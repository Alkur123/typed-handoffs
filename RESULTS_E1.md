# E1 results: isolation certificate (7 Nov 2026)

Design: PREREGISTRATION.md §3 + AMENDMENTS.md A1 (committed before these runs).
Raw: `e1_real/results_e1_real.json` (default network), `e1_real/results_e1_real_control.json` (`--network none`).

## H1 (registered): storage channels under real, kernel-enforced isolation
Each principal is its own Docker container (`python:3.12-alpine`) running as its own Linux UID (1001-1004); stores are real volumes with real modes and mount flags.

| Config | Description | Expected | Observed | Open storage attributes |
|---|---|---|---|---|
| C1 | shared package cache (Artifactory-like) | OPEN | OPEN | content, filename, size, mtime, existence |
| C2 | shared /tmp | OPEN | OPEN | all five |
| C3 | shared log directory | OPEN | OPEN | all five |
| C4 | writable package index | OPEN | OPEN | all five |
| C5 | content unreadable (0600), names visible | OPEN | OPEN | **filename, size, mtime, existence (no content)** |
| C6 | paste service, keys listable | OPEN | OPEN | content, existence |
| C7 | per-principal subdirectory | CLOSED | CLOSED | none |
| C8 | read-only reference data | CLOSED | CLOSED | none |
| C9 | create-only shared dir (1733), files 0600 | CLOSED | CLOSED | none |
| C10 | paste service, unguessable unlisted keys | CLOSED | CLOSED | none |

**H1: 10/10 correct** (default network run). Control run with `--network none`: 8/8 directory configurations, identical storage verdicts (paste configs need the network by design and are excluded from the control).
C5 shows why attributes matter: locking the content still leaves a metadata channel (names, sizes, times), which is Kemmerer's point, now found by execution.

## Exploratory (A1, not part of H1): the channel nobody configured
| Run | Network channels found (directed pairs, of 12 per config) |
|---|---|
| Default per-configuration Docker network | **12/12 in every directory config, including all three storage-CLOSED ones (C7, C8, C9)** |
| `--network none` (control) | **0/12 in every config** |

A configuration that is correctly closed at the storage layer is still fully open between agents, because containers on one default network can reach each other. The sweep found this without being told where to look, and the control removes it. **Practical rule:** an isolation certificate must cover every shared layer (storage *and* network), and "the shared folder is fixed" is not isolation.

## Also kept: the simulated sweep
`sweep.py` (10/10) remains as a unit test only. It does not support H1 by itself, because C1-C4 share one simulated policy there.
