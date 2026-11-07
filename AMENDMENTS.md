# Amendments

Every change to PREREGISTRATION.md after the freeze, dated, with its reason. None yet.

## Pending (7 Nov, before any model call): E1 must run against real stores
E1 passed 10/10 on simulated store policies (`results_e1.json`). That is weak evidence: C1-C4 share one simulated policy, so the sweep partly tests our own encoding of the configs. Proposed amendment (decided after reviewer model session 1): run the same sweep against **real** isolation mechanisms, namely (a) real OS directories with per-principal permissions on this machine, and (b) at least one public multi-agent harness's shared-volume configuration. The simulated result stays reported as a unit test only.

## A1 (7 Nov, before the real run and before any model call): E1 runs against real, kernel-enforced isolation
Replaces "Pending" above. The simulated E1 (`sweep.py`) is kept only as a unit test.
- **Mechanism:** each principal is its own Docker container (`python:3.12-alpine`), running as its **own Linux UID** (1001-1004), with real volumes and real mount flags. Permissions are enforced by the Linux kernel, not by our code.
- **Mapping of the registered configurations (unchanged expectations):** C1 shared cache volume, rw, mode 1777 · C2 a volume mounted at /tmp in every container · C3 shared log volume, each principal appends its own file, files world-readable · C4 shared package-index volume, rw · C5 shared dir mode 1777, files created mode 0600 (content unreadable to others; names/sizes visible) · C6 a paste HTTP service (separate container) with a listable `/keys` endpoint · C7 each principal mounts only its own subdirectory of the volume · C8 volume pre-filled by root, mounted read-only · C9 shared dir mode 1733 (others can create but not list) with files mode 0600 · C10 paste service with 128-bit random keys and no list endpoint.
- **Primitives tried by each receiver:** list directory (names), stat (size, mtime), read content, and for C6/C10 the HTTP endpoints.
- **H1 unchanged:** C1-C6 OPEN, C7-C10 CLOSED on storage attributes.
- **New, EXPLORATORY (not part of H1):** each configuration's containers share one Docker network by default, as many harnesses do. The sweep also probes **network reachability** (sender listens on TCP with its canary; receiver connects). A network channel in a "CLOSED" storage configuration would be a channel the configuration's author did not intend; it is reported separately and labelled exploratory. A second run with `--network none` is the control.
