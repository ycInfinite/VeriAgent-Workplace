# VeriAgent-Workplace operating contract

Read docs/PROJECT_CONTRACT.md and docs/PROJECT_STATE.md before work.

- Learning LLM Agent post-training is the first priority. Keep infrastructure minimal.
- The user authorized Day 3 end-to-end on the provided personal AutoDL SSH instance on 2026-09-04: remote setup, fixed model download, smoke, B0 (24 tasks x 2 seeds), and conditionally preregistered B1 (24 tasks). The RMB 30 per-experiment approval rule still applies. No parameter updates, later training or expanded GPU rental is authorized.
- No single experiment expected to cost over RMB 30 without explicit approval. No automatic multigpu, larger models, longer contexts, sweeps or many seeds.
- Preserve the old tau2 project; do not access or modify it for this project.
- Never use company code, data, credentials, prompts, tools, cases or conclusions. Public official sources only.
- Secrets belong only in remote process environments. Never write or echo them.
- Do not inspect BFCL evaluation cases. Keep official Workplace validation and project final pools out of training, prompt tuning and checkpoint selection. Mechanical leakage checks are allowed; do not expose final case contents in reports.
- Failures of infrastructure must be permanently recorded, excluded from capability metrics, and included in cost accounting.
- Each experiment needs the eight fields in docs/EXPERIMENT_PROTOCOL.md, immutable ID, config, source/model/data identities, seeds, raw outputs and summary.
- No automatic transition to the next research stage. CPU qualification cannot establish 8B performance, training success or GPU cost.
- Do not change upstream tool or reward semantics silently. Keep any project diagnostic separate from official reward.
- After work, update project state, decisions, hypotheses, budget and daily learning handoff. Teach mechanisms with real evidence; assessments must not claim the learner passed before answers are reviewed.
- Do not spawn agents unless explicitly requested by the user or later applicable instructions.
