# Amendments

Every change to PREREGISTRATION.md after the freeze, dated, with its reason. None yet.

## Pending (7 Nov, before any model call): E1 must run against real stores
E1 passed 10/10 on simulated store policies (`results_e1.json`). That is weak evidence: C1-C4 share one simulated policy, so the sweep partly tests our own encoding of the configs. Proposed amendment (decided after reviewer model session 1): run the same sweep against **real** isolation mechanisms, namely (a) real OS directories with per-principal permissions on this machine, and (b) at least one public multi-agent harness's shared-volume configuration. The simulated result stays reported as a unit test only.
