"""Exact full-corpus tokenizer and longest-pair gradients; no optimizer updates."""
import argparse
import importlib.metadata
import math
import os
import threading
import time
import traceback
from datetime import datetime, timezone
from run_day3 import ROOT, write, append, Monitor
from run_sft_probe import frozen_sample
from run_current_s1_preference import actual_tokenizer_check
from veriagent.dpo import load_pairs, branch_score, pair_backward, turn_logp
from veriagent.sft_stage import require, sha, validate_deployment, verify_weights


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--execute', action='store_true')
    args = ap.parse_args()
    cfg, pairs = load_pairs('configs/preference29_preflight.json')
    longest = {side: max((len(e['input_ids']), p['task_id']) for p in pairs
                         for e in p[side]['encoded_turns']) for side in ['chosen', 'rejected']}
    require(all(v[1] == cfg['selected_task_id'] for v in longest.values()), 'Longest pair selection changed')
    if not args.execute:
        print({'pairs': len(pairs), 'longest': longest, 'updates': 0})
        return
    require(os.name == 'posix' and cfg['optimizer_updates'] == 0 and not cfg['GPU_training_authorized'], 'Preflight only')
    build = validate_deployment(cfg['deployment_files'])
    out = ROOT / 'experiments' / cfg['run_id']
    out.mkdir(exist_ok=False)
    start = time.perf_counter()
    write(out/'config.json', cfg)
    write(out/'identity.json', {'code_commit': build['code_commit'], 'deployment': build,
          'started_at': datetime.now(timezone.utc).isoformat(), 'hostname': os.uname().nodename})
    append(ROOT/'experiments/registry.jsonl', {'experiment_id': cfg['run_id'], 'event': 'started'})
    def deadline():
        write(out/'invalid_run.json', {'kind': 'process_wall_limit', 'optimizer_updates': 0})
        os._exit(124)
    timer = threading.Timer(cfg['max_wall_seconds'], deadline)
    timer.daemon = True
    timer.start()
    monitor = Monitor(out/'gpu_samples.jsonl')
    monitor.start()
    try:
        packages = {n: importlib.metadata.version(n) for n in cfg['required_packages']}
        require(packages == cfg['required_packages'], 'Package mismatch')
        write(out/'weights.json', verify_weights(cfg))
        adapter = ROOT/cfg['initial_adapter_path']
        for n, h in cfg['initial_adapter_sha256'].items():
            require(sha(adapter/n) == h, 'S1 file mismatch')
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, set_seed
        from peft import PeftModel
        from check_preference_torch import run_controls
        write(out/'torch_controls.json', run_controls())
        require(torch.cuda.device_count() == 1 and torch.cuda.is_bf16_supported(), 'Single BF16 GPU required')
        require(torch.cuda.get_device_properties(0).total_memory >= cfg['min_gpu_memory_gib']*2**30, '96GB required')
        set_seed(cfg['seed'])
        tokenizer = AutoTokenizer.from_pretrained(ROOT/cfg['weights_path'], local_files_only=True)
        count = actual_tokenizer_check(tokenizer, pairs)
        require(count == cfg['expected_HF_turns'], 'Turn count mismatch')
        write(out/'host_preflight.json', {'HF_turns_checked': count, 'packages': packages,
              'gpu': torch.cuda.get_device_name(0), 'longest': longest, 'cuda': torch.version.cuda})
        model = AutoModelForCausalLM.from_pretrained(ROOT/cfg['weights_path'], local_files_only=True,
            trust_remote_code=False, dtype=torch.bfloat16, device_map={'': 0}, attn_implementation='sdpa')
        model = PeftModel.from_pretrained(model, adapter, is_trainable=True)
        model.config.use_cache = False
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
        model.train()
        require(getattr(model.config, 'attention_dropout', 0.) == 0., 'Attention dropout')
        require(all(m.p == 0 for m in model.modules() if isinstance(m, torch.nn.Dropout)), 'Dropout')
        trainable = {n: p for n, p in model.named_parameters() if p.requires_grad}
        require(sum(p.numel() for p in trainable.values()) == cfg['expected_trainable_parameters']
                and all('lora_' in n for n in trainable), 'Trainable policy mismatch')
        before = {n: p.detach().cpu().clone() for n, p in trainable.items()}
        frozen = frozen_sample(model)
        pair = next(p for p in pairs if p['task_id'] == cfg['selected_task_id'])
        def gradients():
            gs = [p.grad for p in trainable.values() if p.grad is not None]
            require(gs and all(torch.isfinite(g).all().item() for g in gs)
                    and any(g.count_nonzero().item() for g in gs), 'Invalid gradients')
            return {'gradient_tensors': len(gs), 'grad_norm': float(torch.nn.utils.clip_grad_norm_(
                list(trainable.values()), cfg['max_grad_norm'], error_if_nonfinite=True))}
        def measure(label, fn):
            model.zero_grad(set_to_none=True)
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()
            tick = time.perf_counter()
            result = fn()
            torch.cuda.synchronize()
            entry = {'phase': label, 'seconds': time.perf_counter()-tick,
                     'peak_allocated_GiB': torch.cuda.max_memory_allocated()/2**30,
                     'peak_reserved_GiB': torch.cuda.max_memory_reserved()/2**30, **result}
            append(out/'phases.jsonl', entry)
            print(entry, flush=True)
            return entry
        def chosen():
            loss = 0.
            for ex in pair['chosen']['encoded_turns']:
                part = -turn_logp(model, ex)/pair['chosen']['target_tokens']
                loss += float(part.detach())
                part.backward()
                del part
            return {'loss': loss, **gradients()}
        sft = measure('chosen_full_branch_backward_no_update', chosen)
        ref = {}
        def reference():
            ref.update({s: branch_score(model, pair[s]['encoded_turns']) for s in ['chosen', 'rejected']})
            return ref
        reference_phase = measure('original_S1_reference_scores', reference)
        write(out/'reference_scores.json', ref)
        def dpo():
            evidence = pair_backward(model, pair, ref, cfg['beta'], cfg['recompute_atol'])
            require(abs(evidence['relative_margin']) <= cfg['initial_margin_atol']
                    and abs(evidence['loss']-math.log(2)) < .01, 'Reference differs')
            return {**evidence, **gradients()}
        dpo_phase = measure('DPO_full_pair_backward_no_update', dpo)
        model.zero_grad(set_to_none=True)
        require(all(torch.equal(p.detach().cpu(), before[n]) for n, p in trainable.items()), 'LoRA changed')
        require(frozen_sample(model) == frozen, 'Frozen sample changed')
        for n, h in cfg['initial_adapter_sha256'].items():
            require(sha(adapter/n) == h, 'S1 file changed')
        wall = time.perf_counter()-start
        write(out/'result.json', {'status': 'FULL_HF_LONGEST_PAIR_GRADIENT_PREFLIGHT_PASSED',
            'pairs': len(pairs), 'HF_turns': count, 'selected_task': pair['task_id'],
            'optimizer_updates': 0, 'LoRA_tensors_unchanged': len(trainable), 'frozen_samples_unchanged': True,
            'wall_seconds': wall, 'GPU_hours': wall/3600, 'estimated_rmb': None,
            'sft': sft, 'reference': reference_phase, 'dpo': dpo_phase,
            'limits': 'Longest sequence gradient paths only; optimizer states/update/reload/full29 training not tested. Not capability evidence or proof of80GB fit.'})
        append(ROOT/'experiments/registry.jsonl', {'experiment_id': cfg['run_id'], 'event': 'completed'})
    except Exception:
        write(out/'invalid_run.json', {'traceback': traceback.format_exc(), 'optimizer_updates': 0,
                                     'wall_seconds': time.perf_counter()-start})
        append(ROOT/'experiments/registry.jsonl', {'experiment_id': cfg['run_id'], 'event': 'failed_preserved'})
        raise
    finally:
        timer.cancel()
        monitor.stop()


if __name__ == '__main__':
    main()
