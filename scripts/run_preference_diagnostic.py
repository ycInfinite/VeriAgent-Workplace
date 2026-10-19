"""Zero-update fixed29 reference calibration, likelihood scoring or train-task rollout."""
import argparse
import copy
import importlib.metadata
import json
import os
import threading
import time
import traceback
from datetime import datetime, timezone
from run_day3 import ROOT, write, append, Monitor, inference_trajectory, summarize, weight_sample
from run_preference29 import actual_tokenizer_check
from veriagent.environment import WorkplaceEnv, digest
from veriagent.dpo import branch_score
from veriagent.preference_diagnostic import load_inputs, score_change
from veriagent.sft_stage import read, sha, require, validate_deployment, verify_weights


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['reference', 'score', 'rollout'], required=True)
    ap.add_argument('--condition', choices=['S1', 'CHOSEN_SFT', 'DPO'], required=True)
    ap.add_argument('--execute', action='store_true')
    args = ap.parse_args()
    cfg, pairs, rows, refs = load_inputs()
    require((args.mode == 'reference') == (args.condition == 'S1'), 'Only calibration uses S1')
    if not args.execute:
        print(json.dumps({'status': 'CPU_DIAGNOSTIC_INPUT_PASSED', 'pairs': 29, 'updates': 0}))
        return
    require(os.name == 'posix' and cfg['GPU_inference_authorized'] and not cfg['GPU_training_authorized'], 'Inference-only scope')
    build = validate_deployment(cfg['deployment_files'])
    if args.mode != 'reference':
        refdir = ROOT/'experiments'/cfg['reference_run_id']
        require(read(refdir/'result.json')['status'] == 'DIAGNOSTIC_COMPLETE' and read(refdir/'identity.json')['code_commit'] == build['code_commit'], 'Calibration gate missing')
    if args.mode == 'rollout':
        for run in cfg['score_run_ids'].values():
            require(read(ROOT/'experiments'/run/'result.json')['status'] == 'DIAGNOSTIC_COMPLETE' and read(ROOT/'experiments'/run/'identity.json')['code_commit'] == build['code_commit'], 'Both frozen score phases required')
    run = cfg['reference_run_id'] if args.mode == 'reference' else cfg[args.mode+'_run_ids'][args.condition]
    out = ROOT/'experiments'/run
    out.mkdir(exist_ok=False)
    started = time.perf_counter()
    records = []
    policy = cfg['policies'][args.condition]
    write(out/'config.json', {**cfg, 'mode': args.mode, 'condition': args.condition})
    identity = {'experiment_id': run, 'code_commit': build['code_commit'], 'deployment': build,
                'source_training_commit': cfg['source_training_commit'], 'policy': policy,
                'started_at': datetime.now(timezone.utc).isoformat(), 'hostname': os.uname().nodename,
                'mode': args.mode, 'condition': args.condition}
    write(out/'identity.json', identity)
    append(ROOT/'experiments/registry.jsonl', {'experiment_id': run, 'event': 'started'})
    def deadline():
        write(out/'invalid_run.json', {'kind': 'process_wall_limit', 'records': len(records), 'updates': 0})
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
        adapter = ROOT/policy['adapter_path']
        require({p.name for p in adapter.iterdir() if p.is_file()} == set(policy['sha256']), 'Wrong adapter file set')
        require(all(sha(adapter/n) == h for n, h in policy['sha256'].items()), 'Wrong adapter SHA')
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, set_seed
        from peft import PeftModel
        require(torch.cuda.device_count() == 1 and torch.cuda.is_bf16_supported(), 'Single BF16 GPU required')
        require(torch.cuda.get_device_properties(0).total_memory >= cfg['min_gpu_memory_gib']*2**30, 'Qualified96GB required')
        set_seed(cfg['seed'])
        tok = AutoTokenizer.from_pretrained(ROOT/cfg['weights_path'], local_files_only=True)
        require(actual_tokenizer_check(tok, pairs) == cfg['expected_HF_turns'], 'HF fullbranch mismatch')
        for row in rows:
            messages = copy.deepcopy(row['responses_create_params']['input'])
            messages[0]['content'] += '\n\n'+cfg['B1_addition']
            ids = tok.apply_chat_template(messages, tools=row['responses_create_params']['tools'], tokenize=True, add_generation_prompt=True, enable_thinking=False)
            require(len(ids)+cfg['max_output_tokens_per_model_call'] <= cfg['max_context_tokens'], 'Initial task cannot fit; no truncation')
        state = WorkplaceEnv().initial_state
        require(all(p['initial_state_sha256'] == digest(state) for p in pairs), 'Initial state changed')
        write(out/'initial_state.json', state)
        model = AutoModelForCausalLM.from_pretrained(ROOT/cfg['weights_path'], local_files_only=True,
            trust_remote_code=False, dtype=torch.bfloat16, device_map={'': 0}, attn_implementation='sdpa')
        model = PeftModel.from_pretrained(model, adapter, is_trainable=False)
        model.eval()
        model.requires_grad_(False)
        require(sum(p.numel() for p in model.parameters() if p.requires_grad) == 0, 'Unexpected trainable model')
        require(all(m.p == 0 for m in model.modules() if isinstance(m, torch.nn.Dropout)), 'Cache requires dropout0')
        before = weight_sample(model)
        identity.update({'gpu': torch.cuda.get_device_name(0), 'packages': packages, 'HF_turns': 179,
                         'initial_contexts': 29, 'trainable_parameters': 0, 'parameter_sample_before': before})
        write(out/'identity.json', identity)
        torch.cuda.reset_peak_memory_stats()
        if args.mode in ['reference', 'score']:
            selected = [p for p in pairs if p['task_id'] in cfg['calibration_task_ids']] if args.mode == 'reference' else pairs
            strata = {r['id']: not bool(r['ground_truth']) for r in rows}
            for p in selected:
                tick = time.perf_counter()
                scores = {s: branch_score(model, p[s]['encoded_turns']) for s in ['chosen', 'rejected']}
                if args.mode == 'reference':
                    require(all(abs(scores[s]-refs[p['pair_id']][s]) <= cfg['cache_tolerance'] for s in scores), 'Cached S1 scores do not reproduce; stop')
                change = score_change(scores['chosen'], scores['rejected'], refs[p['pair_id']],
                                      p['chosen']['target_tokens'], p['rejected']['target_tokens'], cfg['beta'])
                rec = {'task_id': p['task_id'], 'task_uid': p['task_uid'], 'pair_id': p['pair_id'],
                       'category': p['category'], 'empty_reference': strata[p['task_id']],
                       'seconds': time.perf_counter()-tick, **change}
                records.append(rec)
                append(out/'scores.jsonl', rec)
                print(json.dumps({'scored': len(records), 'task_id': p['task_id'], 'margin': rec['relative_margin']}), flush=True)
            require(len(records) == (2 if args.mode == 'reference' else 29), 'Incomplete scores')
            metrics = {'scored_pairs': len(records), 'mean_DPO_loss': sum(x['DPO_loss'] for x in records)/len(records),
                       'positive_relative_margin_pairs': sum(x['relative_margin'] > cfg['cache_tolerance'] for x in records),
                       'calibration_max_abs_diff': max(abs(x[s+'_delta']) for x in records for s in ['chosen', 'rejected']) if args.mode == 'reference' else None,
                       'peak_allocated_GiB': torch.cuda.max_memory_allocated()/2**30,
                       'peak_reserved_GiB': torch.cuda.max_memory_reserved()/2**30}
        else:
            for row in rows:
                require(time.perf_counter()-started+180 < cfg['max_wall_seconds'], 'No time for next trajectory')
                rec = inference_trajectory(model, tok, row, cfg, 42, 'B1', source_pool='training_candidate')
                rec.update({'experiment_id': run, 'diagnostic_condition': args.condition, 'policy_identity': policy,
                            'diagnostic_only_not_training_admitted': True})
                records.append(rec)
                append(out/'trajectories.jsonl', rec)
                write(out/'progress.json', summarize(records))
                require(not rec['infra_invalid'], 'Infrastructure-invalid rollout; no retry')
            require(len(records) == 29, 'Incomplete train-task execution')
            metrics = summarize(records)
        require(weight_sample(model) == before, 'Parameter sample changed')
        require(all(sha(adapter/n) == h for n, h in policy['sha256'].items()), 'Adapter file changed')
        require(sha(ROOT/cfg['reference_path']) == cfg['reference_sha256'], 'Reference cache changed')
        wall = time.perf_counter()-started
        write(out/'result.json', {'status': 'DIAGNOSTIC_COMPLETE', 'mode': args.mode, 'condition': args.condition,
            **metrics, 'parameter_updates': 0, 'parameter_samples_unchanged': True, 'wall_seconds': wall,
            'GPU_hours': wall/3600, 'estimated_rmb': None, 'scope': 'Selected training29 only;notgeneralization;historicalS1failureisselectioncriterion'})
        append(ROOT/'experiments/registry.jsonl', {'experiment_id': run, 'event': 'completed'})
    except Exception:
        write(out/'invalid_run.json', {'traceback': traceback.format_exc(), 'records': len(records),
                                     'wall_seconds': time.perf_counter()-started, 'parameter_updates': 0})
        append(ROOT/'experiments/registry.jsonl', {'experiment_id': run, 'event': 'failed_preserved'})
        raise
    finally:
        timer.cancel()
        monitor.stop()


if __name__ == '__main__':
    main()
