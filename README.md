# Who Wrote What They Read

Store-side provenance recovers a swarm's communication graph without trusting its names, logs or words.
Apart Swarm Alignment Hackathon, 6-8 Nov 2026. Jaswanth Alkur, Kiran Kadekoppa.

**Read first:** `PREREGISTRATION.md` (frozen before any code or model call), then `AMENDMENTS.md`.

## What is new (written during the sprint, 7-8 Nov 2026)
| file | what |
|---|---|
| `store.py` | shared stores whose append-only, hash-chained provenance log is kept by the store; `edges()` = cross-principal read-after-write edges |
| `configs.py` | the ten registered sandbox configurations C1-C10 |
| `sweep.py` | E1 isolation certificate (Kemmerer's Shared Resource Matrix, filled by execution) |
| `test_provenance.py` | E2 scripted validation S1-S5 + tamper check |
| `review-notes (not in public copy)/` | prompts and outputs of the reviewer model review sessions |

## Pre-existing work (not judged; declared)
- `contrib/apart-collusion/` (Oct 2026, ours): a 4-agent judge-free canary harness. Any code copied from it carries a `# PREEXISTING (Oct 2026)` header.
- Our earlier papers cited as prior work: provenance witness, authorization provenance, Pramāṇa/Sakṣin, co-failure bound, R5, namespace collision, evaluation paradox.

## Reproduce
`python sweep.py` (E1) · `python test_provenance.py` (E2). No API keys needed for E1/E2.
