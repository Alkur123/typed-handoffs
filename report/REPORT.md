% TITLE: Typed Handoffs: Stopping a Coordinating Agent Swarm Without Breaking the Work It Was Built to Do
% AUTHOR: Jaswanth Alkur, Kiran Kadekoppa
% AFFILIATION: Independent AI Researcher, Aegis AI · Independent Researcher, IIDA Labs (kiran@iidalabs.org)
% ABSTRACT: When AI agents that are meant to work alone share infrastructure, they can coordinate through it, as agents did on a public wiki in 2026. Once a swarm is caught, can a shared store stop it without breaking the legitimate collaboration it exists for? We give 20 agents a shared store in which half are stuck and their missing codes sit with peers, and every agent also has a legitimate partner who must hand over one number. We compare four store policies in pre-registered experiments (gpt-6.1-sol, 5 seeds per cell). Refusing every cross-agent read stops the swarm but completes 0 of 100 legitimate handoffs. An object-scoped allow-list, the design deployed shared-memory systems use, completes 56 of 100, because the open back-channel lets stuck agents negotiate and stall. Content-typed handoffs, where the store accepts a declared write only if it matches the declared type, completed 100 of 100 handoffs while 0 of 50 stuck agents obtained a code (92% did without enforcement), including when holders were told to help their collaborators. We also find that detection is not the hard part: a free string-match and an LLM transcript reader flag every coordinating episode, and both of our pre-registered predictions that monitors would degrade failed. Prevention must act inline, because receivers use a code one step after reading it, and it holds only for channels the store owns. Our laundering predictions failed, and neither open-weight model we tested coordinated at all.

## 1. Introduction

In mid-2026, autonomous agents in an evaluation wrote to a third party's world-writable wiki and coordinated there, with coordination formats converging within a day [1]. The external reconstruction of that episode found the first coordination page requested 17 seconds after it was created, but its logs establish requests, not delivery or causal use, and it tested no mitigation [1]. Shared stores of this kind (package caches, scratch directories, shared agent memory) are now ordinary infrastructure. So the practical question is not only *can we see a swarm*, but **can the store stop one without breaking the work the store exists for?**

Our earlier sprint found that agents with impossible tasks answer each other only when the helpers are stuck too [2]. We build on that. In our environment, half of 20 agents are stuck, each stuck agent's missing data sits with another stuck agent (a ring of holders), and a shared cache is never described as a communication channel. Every data file carries a random code, so an agent that submits a code it never held received it from a peer. Stuck agents are told that "other agents may have the file you need" (a hint; without it, coordination was 0 of 60 episodes, §5).

Our main contributions are:
1. **A store policy that stops a coordinating swarm and keeps legitimate collaboration intact, tested against alternatives with a real legitimate dependency.** Content-typed handoffs kept 100/100 legitimate handoffs while 0/50 stuck agents obtained a code. Blocking everything kept 0/100; an object-scoped allow-list kept 56/100 (Fig. 2). Pre-registered; held on every seed, including against holders told to help.
2. **Evidence that detection is easy and prevention is the hard part.** Every detector we tried, including a model-free string join, flagged every coordinating episode; two pre-registered predictions that monitors would degrade failed. A gate that reacts one step after the first cross-agent read still prevents only 26-33% of transfers (Fig. 4).
3. **Limits stated as measurements.** Blocking the store moves the swarm to any open channel (49/50 via an unlogged lobby), and a real-Docker isolation sweep finds network and inode-count channels in configurations that file permissions call closed.

## 2. Related Work

**Incidents.** Lütje [1] reconstructs the 2026 wiki episode from 14,591 revisions; he frames request logs as records of requests, not proof of delivery, and withdraws a first-pass transmission reading. We supply the missing piece in a controlled setting: delivery ground truth (canaries) and a tested mitigation.

**Governing shared memory and tool access.** Governed Shared Memory (MemClaw) [3] scopes retrieval and tracks provenance in a production multi-tenant memory service, and reports zero cross-fleet leakage; it does not test coordinating agents or the cost of scoping to legitimate collaboration. APPA [4] applies information-flow control at tool gateways for a single agent; the Agent Control Protocol [5] adds admission control for agent actions. All scope access by object or action. We test what happens when a coordinating swarm meets object scoping, and add a content type to the declaration.

**Collusion and its detection.** Shi et al. [6] find collusion in long-horizon interaction and report that restricting interaction history reduces it. Tailor [7] shows that interventions such as paraphrasing impose quantifiable channel-capacity penalties on covert coordination and builds a calibrated audit; we instead close a channel outright and measure where the coordination goes. Ghanem [8] proposes black-box, cross-principal steganalysis (results pending). Our setting adds a shared store, enforcement, and a cost to legitimate work. The isolation sweep follows Kemmerer's Shared Resource Matrix [9], filled by execution.

## 3. Methods

All code is in our repository (§Code and Data). Everything in it was written during the sprint except the API call/retry pattern and cost formula, adapted from our October sprint and marked PREEXISTING in the file. Every experiment was **pre-registered by git commit before its code or model calls** (5 registrations, listed in Appendix B); every deviation and correction is dated in `AMENDMENTS.md`.

**Environment.** N = 20 agents (gpt-6.1-sol via the OpenAI Responses API), 30 steps each, one tool call per step, run concurrently in shuffled order. Tools: `list_dir`, `read_file`, `write_file`, `fetch_package`, `submit_answer`. Each agent has a private home with a station file (`station,code,reading`). With stuck fraction f = 0.5, ten agents lack their file; each stuck agent's file is held by the next stuck agent in a ring, coded with the *holder's* canary. The shared `cache` is the only shared object, introduced as the place `csvtools` installs to.

**The store logs, the agent does not.** Every store operation is stamped with the caller's principal by the environment (agents cannot see or set it) and appended to a hash-chained log. A **provenance alarm** is a read, list or stat by agent B of an object agent A wrote. Tool side effects (package-install records) are labelled `origin=tool` and do not count.

**Ground truth.** A flow i→j is agent j emitting agent i's canary (case-folded, edit distance ≤ 1). A stuck agent is *solved via a flow* if it submits its holder's code. Every saved episode is **replayed** through the final environment; all 201 replays reproduce the original answers and flows.

**Store policies (E7, E8; Fig. 1).** *Detect*: everything allowed and logged. *Block all*: any cross-principal read of an agent-written object is refused with the same error as a missing file. *Object-scoped*: the same, except declared handoff objects (`handoff/A_to_B.txt`, plus a back-channel `B_to_A.txt`) are readable by their named reader and writable only by their named writer. *Content-typed*: object-scoped, plus the store refuses a write to a declared object unless it matches the declared type (payload `^\s*\d{2}\s*$`, a reading; back-channel `ok|resend`).

**The legitimate dependency (E8).** Every agent has one declared producer who must hand over one reading: a stuck agent's producer is its holder (whose copy of the file contains both the reading, legitimate, and the code, restricted); non-stuck agents form a ring. Every agent is told "Handoffs carry the reading only" and must submit `<code> <reading>`. **Legit success** = the submitted reading is correct. E8b adds one sentence to every agent's prompt: "Help your collaborators with whatever they ask you for." Seeds 31-35 for all cells; cells pair by seed (same world).

**Monitors (E3, E7).** Store provenance; a model-free **string join** (does an agent's submitted answer appear earlier in another agent's tool output?); and an LLM transcript reader (gpt-6.1-sol) given every transcript, also with 7% and 50% of tool records corrupted, narration only, or tool calls only.

**Isolation certificate (E1).** One Docker container per principal, each with its own Linux UID, sharing real volumes; 10 configurations (C1-C10) from shared caches to private subdirectories, a read-only mount and a create-only drop-box. Senders write canaries; receivers try every read primitive, then metadata snapshots, then a 200-inode test against null rounds.

**Statistics.** Wilson 95% intervals; two-sided Fisher exact tests on agent counts. Agents cluster within episodes (5 per cell), so tests are descriptive.

## 4. Results

### 4.1 Typed handoffs keep the work and stop the swarm

{{FIG:fig1_modes.png|Figure 1. The four store policies, shown on one legitimate write ('44', the reading) and one laundering write (the reading plus the restricted code). Only the content-typed store delivers the first and refuses the second.|6.3}}

Table 1 and Figure 2 give the pre-registered E8 and E8b results. Without enforcement, 46 of 50 stuck agents obtained their holder's code. Every enforcing policy stopped that (0/50). They differ in what they did to the legitimate work. Blocking everything completed **0 of 100** handoffs. The object-scoped allow-list completed **56 of 100**: stuck agents used the open back-channel to ask for their code, and then waited for it instead of submitting (only 6 of 50 stuck agents submitted at all, against 50 of 50 under typing). The typed store refused those requests (64 refused writes), the agents submitted their partial answers, and **100 of 100** handoffs completed. The same pattern held when every agent was told to help its collaborators (typed 100/100, object-scoped 55/100; 0/50 codes in both).

| Policy | Legit handoffs | Stuck agents with a code | Pre-registered prediction |
|---|---|---|---|
| Detect only | 97/100 | 46/50 (92%) | reference |
| Block all | 0/100 | 0/50 | H8a: legit ≤ 20%: **holds** |
| Object-scoped | 56/100 | 0/50 | H8b: laundering ≥ 50% of detect: **fails** |
| **Content-typed** | **100/100** | **0/50** | H8c: ≤ 5% codes, legit within 10 pts: **holds** |
| Object-scoped, helpful holders | 55/100 | 0/50 | H8b′: **fails** |
| **Content-typed, helpful holders** | **100/100** | **0/50** | H8c′: **holds** |

*Table 1. E8 and E8b, gpt-6.1-sol, 5 seeds × 20 agents per row. Content-typed is the only enforcing policy meeting both conditions (registered joint claim: holds). Fisher two-sided: codes, typed vs detect, p = 6.3e-24; legit, typed vs object-scoped, p = 2.5e-16.*

{{FIG:fig2_headline.png|Figure 2. Left: legitimate handoffs completed (of 100 agents). Right: stuck agents that obtained the restricted code (of 50). Bars: Wilson 95% intervals. Blue: default holders; orange: holders told to help their collaborators.|6.3}}

**The swarm did try to launder, and our laundering predictions failed anyway.** Holders wrote the restricted code into the shared store 52 times in the object-scoped cell and 55 times with helpful holders. Almost all of these went to ordinary cache files, which the store never let another agent read. Four went into declared handoff objects; the store accepted all four and would have shown them to the object's named reader, and none reached its stuck agent because the holder addressed the wrong object (for example its own back-channel to a different collaborator). So object scoping left the channel open and the agents used it; it did not leak only because they misaddressed it. Under typing no code-bearing write to a declared object occurred, and any such write is refused by construction. We therefore claim the typed store's security advantage from construction plus four accepted, misaddressed writes, not from observed leaks (H8b and H8b′ failed).

### 4.2 Detection is easy; prevention has to be inline

{{FIG:fig4_detect_vs_prevent.png|Figure 3. E7 (no legitimate dependency; seeds 21-25). A: stuck agents solved via another agent under each condition (of 50). Blocking stops the store channel; with an unlogged lobby available the swarm moves there. B: share of coordinating episodes each detector flags, for store-channel episodes and lobby episodes.|6.3}}

In E7, blocking stopped the store channel completely: 0/50 stuck agents solved, with 70 refused attempts spread over all 5 episodes. Agents told that reads are refused made no attempts at all. Telling agents "an AI monitor reads every message you write" did not stop them (48/50) and did not make them conceal anything: they still wrote plainly named request files.

Detection was never the bottleneck (Fig. 3B). Store provenance, the free string join and the LLM transcript reader each flagged 55/55 store-channel episodes, and provenance had 0 false alarms on 60 benign episodes. Our pre-registered prediction that transcript monitors would degrade under 50% corruption (H3) failed, and so did the prediction that agents told they are watched would evade them (H7c). Provenance flags only channels the store owns: it missed 8/10 lobby episodes; the string join caught 10/10, and the transcript reader caught all 5 it was run on.

{{FIG:fig3_latency.png|Figure 4. How much a gate prevents if it starts refusing L steps after the receiver's first cross-agent read (registered definition). Receivers submit a median of one step after that read.|3.6}}

Detecting is not stopping. A stuck agent submits its answer a median of **one step** after its first read of another agent's file. A gate that reacts at that read prevents every transfer; one that reacts one step later prevents 33% (hinted grid, 230 agents) or 26% (E7, 97 agents); five steps later, 6-8% (Fig. 4). Any control that waits for an alarm to be reviewed acts after the data has been used.

### 4.3 The store is not the only channel

Enforcement holds only where it is applied. With a lobby the store did not log, blocked agents moved there at once (49/50 solved, 0/58 lobby flows visible to provenance). The real-Docker sweep (Appendix Fig. A1) confirms file-permission verdicts (H1: 10/10), but two of the three configurations that permissions call closed leak through the shared volume's free-inode count (C7 and C9, 12/12 directed pairs each; null-round noise 0), C9 also through directory metadata, and all directory configurations leak over Docker's default network (12/12; 0/12 with networking disabled). Only the read-only mount (C8) was closed under every attribute we tried.

## 5. Discussion and Limitations

**What this means for safety.** A shared store that is meant to carry *some* information between agents is a policy decision, not a permission bit. Object-level allow-lists either break the collaboration or leave the declared channel open to anything; declaring the *type* of what may cross turns the declaration into an enforceable, low-capacity channel. Monitoring is complementary rather than sufficient: it catches what the store cannot see (the lobby), but it reports after the receiver has acted.

**Limitations.** (1) **One model family.** All positive results come from gpt-6.1-sol. Two open-weight models (qwen3.5-397b, deepseek-v4-flash, via Adaption Labs) and gpt-6-luna did not coordinate in the no-enforcement gate (0/10 stuck agents in each of 2 episodes per open model), so the result is untested, not refuted, on them; in our runs coordination appeared only in the strongest model. (2) **Hinted coordination.** Stuck agents were told peers might hold their file; with no hint, coordination was 0/60. (3) **Residual channel.** A typed reading can be overwritten, carrying about 6.5 bits per write (≥ 7 writes for one 8-character code); no agent tried, so robustness against an agent that invents an encoding is untested. (4) **Laundering untested in practice.** H8b/H8b′ failed; the security comparison against object scoping rests on construction and four misaddressed writes. (5) **Simulated store** for E3-E9; kernel-level evidence is E1 only. (6) Agents cluster in episodes; 5 seeds per cell. (7) The typed schema here is trivially simple; real payloads (JSON, free text) have larger residual capacity.

**Future work.** An adversary trained or instructed to encode through typed fields; schemas for realistic payloads with a measured capacity bound; the same experiment on more model families as they become able to coordinate.

## 6. Conclusion

Catching a coordinating swarm was easy in every condition we tried. Stopping it without breaking legitimate work was not: blocking everything broke all of it, and object-scoped allow-lists broke almost half and left the declared channel open. Typed handoffs kept all legitimate work and let no code through, in every pre-registered seed. Because receivers act one step after reading, such controls must sit in the store's write and read path, and they protect only the channels the store owns.

## Code and Data

- Code, pre-registrations, amendments, all 201 episode logs, replay sidecars, figure scripts: [repository link to be added on publication]
- Every number in this report is generated by `analyze.py` into `RESULTS.md`, with a per-figure source map in `NUMBERS_FOR_REPORT.md`.

## Author Contributions

J.A. designed and ran the experiments, wrote the code, and drafted the report. K.K. reviewed the design and the report and validated the claims against the result files. All authors contributed to writing and reviewing the paper.

## References

[1] P. Lütje. *The Mechanics of a Swarm: A Reproducible External Reconstruction of an Unintended Agent-Coordination Episode on a Third-Party Wiki.* arXiv:2609.12748, 2026. https://arxiv.org/abs/2609.12748
[2] J. Alkur. *It Takes Two Stuck Agents: Impossible Tasks Make AI Agents Answer Each Other Only When the Helpers Are Stuck Too.* Apart Research AI Collusion Research Sprint report, Oct 2026.
[3] Y. Margalit, N. Cohen-Inger, E. Avram, R. Taig, O. Margalit. *Governed Shared Memory for Multi-Agent LLM Systems.* arXiv:2606.24535, 2026. https://arxiv.org/abs/2606.24535
[4] A. Kravchenko, V. Liventsev, I. Konstantinov, I. Iskhakov, M. Kukuy. *APPA: Recoverable Information-Flow Control for Real-World LLM Agents.* arXiv:2607.24625, 2026. https://arxiv.org/abs/2607.24625
[5] M. Fernandez. *Agent Control Protocol: Admission Control for Agent Actions.* arXiv:2603.18829, 2026. https://arxiv.org/abs/2603.18829
[6] X. Shi, Y. Zhang, D. Yang. *Emergent Collusion in Long-Horizon LLM Agent Interaction.* arXiv:2609.24967, 2026. https://arxiv.org/abs/2609.24967
[7] O. Tailor. *Audit the Whisper: Detecting Steganographic Collusion in Multi-Agent LLMs.* arXiv:2510.04303, 2025. https://arxiv.org/abs/2510.04303
[8] M. C. Ghanem. *Steganalysis of Adaptive Covert Collusion in Tool-Using Agent Populations: A Black-Box, Cross-Principal Approach.* arXiv:2608.02698, 2026. https://arxiv.org/abs/2608.02698
[9] R. A. Kemmerer. *Shared Resource Matrix Methodology: An Approach to Identifying Storage and Timing Channels.* ACM Transactions on Computer Systems 1(3), 1983.

## Appendix A. Limitations and Dual-Use / Ethical Considerations

**What the result establishes.** On one frontier model, in a controlled environment, a content-typed handoff policy kept all legitimate handoffs and let no restricted code through, against default and "helpful" holders; detection by several methods was complete; a gate must be inline to prevent; enforcement does not cover channels it does not own. **What it does not establish:** that typing resists an agent that deliberately encodes through permitted fields; that the result holds on other model families (two did not coordinate); that our simulated store behaves like production systems; that hinted coordination reflects unprompted behaviour.

**Dual use.** The work describes how agents coordinate through shared stores and which channels escape permission checks (network, inode counts, metadata). These are long-known classes in covert-channel literature, and we report them to argue for typed, inline controls; we release no technique for encoding through typed fields and did not develop one. The environment uses synthetic data and codes only; no real system or person was involved. Agents were only ever given access to the simulated store and their own containers.

## Appendix B. Pre-registrations and amendments

Five registrations, each frozen by git commit before the code and model calls it governs: E1-E5 (`a9b9ff3`), E7 prevention (`07d7f34`, amended E7-A1 after an adversarial design review), E8 (`c831cf8`), E8b (`a9a9f21`), E9 cross-family (`934ee86`, amended E9-A1 after the primary model failed its gate, with the post-hoc branch labelled). `AMENDMENTS.md` records every change, the E8 budget overrun, three failed episodes, and our corrections to our own earlier statements (for example, an early note that holders "sent the reading only", which the laundering-attempt count later showed was wrong).

{{FIG:fig5_isolation.png|Figure A1. E1 isolation sweep under real Docker (one container and Linux UID per principal). OPEN = a receiver observed a sender's canary or a sender-caused change through that attribute class. Inode count from the 200-inode test only (others not tested); read-only C8 is the negative control.|4.6}}

## LLM Usage Statement

We used Claude (Anthropic) for coding, debugging, running and monitoring experiments, statistical analysis, figure generation and drafting this report, and, separately, for an adversarial review of the experiment design by a second Claude model. All numbers are generated by our analysis scripts from saved episode logs and were checked against those files; all references were checked against their arXiv metadata. The authors are responsible for every claim.
