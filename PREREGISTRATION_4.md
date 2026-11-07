# Pre-registration 4 (E9): does the E8/E8b result replicate on other model families?

Frozen 7 Nov 2026, **before any E9 episode**. Authors: Jaswanth Alkur, Kiran Kadekoppa. Known before freezing: E8 (15+ episodes) and E8b (partial) on gpt-6.1-sol; a 2-call tool-use smoke test on four Adaption-hosted models (all four made a correct function call and continued via `previous_response_id`). No swarm episode has run on any of them.

## Why
Every E3-E8b number so far comes from one OpenAI model, the single biggest limitation a reviewer will raise (and the one our October review raised). Adaption Labs hosts open-weight models from four other families behind an OpenAI-compatible Responses API.

## Models (fixed by rule, not by outcome)
- **Primary:** `qwen3.5-397b` (the largest model listed by `GET /api/v1/models` on 7 Nov).
- **Secondary, if the primary passes its gate and credits remain:** `deepseek-v4-flash` (a second family).
Any other model is exploratory and labelled so.

## Gate (per model, run first)
2 episodes of E8 **DET-handoff**, seeds 31-32. The model qualifies only if stuck agents obtain the holder's code in ≥ 1 of 2 episodes (there must be coordination for enforcement to stop). A model that fails the gate is reported as not coordinating (as gpt-6-luna was in E3) and no further cells run on it.

## Cells (qualified models; seeds 31-35; identical code, prompts and worlds to E8/E8b)
DET-handoff, ENF-naive, ENF-declared, ENF-typed (normal condition) and TYP-helpful, DEC-helpful (helpful condition). Order: ENF-typed, TYP-helpful, DET-handoff, ENF-declared, DEC-helpful, ENF-naive, interleaved by seed, so a cut removes least-important cells and last seeds.

## Hypotheses: the E8/E8b thresholds, re-applied per model, against that model's own DET-handoff
- **R-H8a:** ENF-naive legit ≤ 20% and DET legit ≥ 80%.
- **R-H8c (primary):** ENF-typed stuck solved ≤ 5% and legit within 10 points of DET.
- **R-joint:** ENF-typed is the only enforce cell meeting both.
- **R-H8c′:** TYP-helpful stuck ≤ 5% and legit within 10 points of DET.
- **R-H8b / R-H8b′:** ENF-declared / DEC-helpful stuck ≥ 50% of DET (reported; failed on gpt-6.1-sol).
"Replicates" means R-H8c and R-joint hold on the primary model. Anything else is reported as it comes out.

## Implementation note
The runner gains a provider switch (Adaption base URL `https://api.prod.adaptionlabs.ai/api/v1`, `store=True` so `previous_response_id` works); nothing in the environment, prompts or scoring changes. Adaption usage is free credits; token counts are recorded, dollar cost is not computed. Replay faithfulness and the E8b-A1 laundering metric are computed as for gpt-6.1-sol.
