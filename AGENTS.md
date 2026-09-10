# VeriAgent-Workplace operating contract

Read docs/PROJECT_CONTRACT.md and docs/PROJECT_STATE.md before work.

- Learning LLM Agent post-training is the first priority. Keep infrastructure minimal.
- Day 3 authorization on 2026-09-04 covered inference only and is historically complete. On 2026-09-10 the user explicitly requested direct experiment progress toward SFT with coarse teaching. Proceed with data/encoding/runner preparation and the next bounded SFT probe. Learning quizzes are not execution gates. GPU execution requires GPU availability on the user-provided single-GPU instance, eligible training data, passed integrity gates and a preregistered bounded run; do not automatically rent or start an instance. Apply the latest budget override below and do not infer authorization for a full S1/S2 sweep, DPO or online RL from this first-probe request.
- No single experiment expected to cost over RMB 30 without explicit approval. No automatic multigpu, larger models, longer contexts, sweeps or many seeds.
- Latest user override (2026-09-10): for the currently requested SFT progression the user explicitly waived budget gating ("不用管预算，尽管用"). Do not ask again solely because of the RMB 30 threshold or missing price. Continue recording measured resource usage and mark unknown prices/costs unavailable; keep single-GPU/model/context/rollout/phase bounds. The newly supplied host is authorized for no-card preparation; GPU compute still requires GPU availability, and preparation is not permission to change instance mode through undocumented controls.
- Preserve the old tau2 project; do not access or modify it for this project.
- Never use company code, data, credentials, prompts, tools, cases or conclusions. Public official sources only.
- Secrets belong only in remote process environments. Never write or echo them.
- User transfer preference (2026-09-10): use the provided GitHub repository to transfer project code/configuration and authorized public project records. Push locally, pull execution files at an exact commit remotely, and verify hashes; keep weights/caches/credentials out of Git. The repo is private: scripts/github_file_sync.py uses the existing local Git login only with GitHub API and sends short-lived raw-file download URLs through non-echoing SSH stdin; account credentials never go to the host and URLs are not persisted. Sync only the approved execution whitelist, retaining dev/final isolation and model/venv assets. Do not change repository visibility or install permanent remote credentials automatically.
- Do not inspect BFCL evaluation cases. Keep official Workplace validation and project final pools out of training, prompt tuning and checkpoint selection. Mechanical leakage checks are allowed; do not expose final case contents in reports.
- Failures of infrastructure must be permanently recorded, excluded from capability metrics, and included in cost accounting.
- Each experiment needs the eight fields in docs/EXPERIMENT_PROTOCOL.md, immutable ID, config, source/model/data identities, seeds, raw outputs and summary.
- No automatic transition to the next research stage. CPU qualification cannot establish 8B performance, training success or GPU cost.
- Do not change upstream tool or reward semantics silently. Keep any project diagnostic separate from official reward.
- After work, update project state, decisions, hypotheses, budget and daily learning handoff. Teach mechanisms with real evidence; assessments must not claim the learner passed before answers are reviewed.
- Do not spawn agents unless explicitly requested by the user or later applicable instructions.
