# Experiment protocol

Each run must have: Research Question, Hypothesis, Independent Variable, Controlled Variables, Metrics, Evidence Gate, Cost Bound, Failure Branch.

Experiment directories are created with exist_ok=False. Never overwrite a completed run. Append registry events instead of erasing invalid attempts. Record code commit, dirty status and script SHA256, upstream commit, dataset revision/hashes, seed, config, raw JSONL, result and validity.

CPU scripted tool replay is an environment experiment, not an Agent model experiment. GPU fields are null/not-measured until measured. GPU-hours=0 for CPU-only runs; this does not imply future GPU cost is zero.

Keep official reward and project diagnostics separate. Verifier exceptions caused by code/data mismatch are invalid for model attribution. Normal policy mistakes, generation limits and loops are valid model failures. Capability metrics exclude infra-invalid runs; total cost includes them.

Task success is macro pass@1 over valid task rollouts; do not substitute pass@k. Partial success is diagnostic only. Record tool-call attempts independently of model turns; HTTP 200 is not tool semantic success. Grounding annotations require visible evidence. Success cost is undefined when successes=0.

No training stage starts on CPU qualification alone. Model qualification, real masking/loss/update/reload checks, and measured SFT/DPO step time need separately approved probes.

