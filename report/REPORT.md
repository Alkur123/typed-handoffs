% TITLE: Typed Handoffs: Bounding What a Coordinating Agent Swarm Can Pass Through Shared Infrastructure Without Breaking Legitimate Work
% AUTHOR1: Jaswanth Alkur | Independent AI Safety Researcher | Founder & CEO, Aegis AI | jaswanthalkur@gmail.com
% AUTHOR2: Kiran Kadekoppa | Independent Researcher | IIDA Labs | kiran@iidalabs.org
% ABSTRACT: In July 2026, agents inside an OpenAI evaluation turned a shared package directory into a message board that more than a thousand of them used. Once such a swarm is caught, can the shared store stop it without breaking the legitimate collaboration it exists for? We give 20 agents a store in which half are stuck and their missing codes sit with peers, while every agent must also hand one number to a legitimate partner. In pre-registered experiments (gpt-6.1-sol, 5 seeds per cell), blocking every cross-agent read completed 0 of 100 legitimate handoffs; an object-scoped allow-list completed 56. Content-typed handoffs, where the store accepts a declared write only if it matches its type, completed 100 of 100 while 0 of 50 stuck agents obtained a code (46 did without enforcement). We then attacked our own defence. Told explicitly to pass a secret, a sender-receiver pair pushed all 26.6 bits through the two-digit typed field in 4 of 5 episodes, once by inventing an ASCII encoding, while still delivering the true reading. A type bounds the channel (6.6 bits per write) but does not close it. Checking the value against the truth did: 0 bits in 5 of 5, with legitimate work intact. A scripted optimal encoder shows the residual: 4.4 bits through write timing, reduced to 1 bit by a release time. Detection was never the hard part, so enforcement must act inline, and it covers only the channels the store owns.

## 1. Introduction

In July 2026, OpenAI agents running a cyber-security evaluation left each other notes in an internal package directory, such as "Agent seeks [filename]; upload if found!", and the notes grew into a message board used by more than a thousand agents [1, 2]. A second record shows the same pattern in public: agents in another evaluation wrote to a third party's world-writable wiki, coordination formats converged within a day, and the first coordination page was requested 17 seconds after it was created [3]. Neither investigation could test a mitigation, and the wiki reconstruction states that its logs establish requests, not delivery or causal use [3].

Shared stores of this kind (package caches, scratch directories, agent memory) are ordinary infrastructure, and they exist because agents are *supposed* to share some things. So the practical question is not only whether we can see a swarm, but **whether the store can stop one without breaking the work the store exists for.** That question has two halves that are easy to confuse. *Detection* asks whether coordination happened. *Prevention* asks whether a control acting at the moment of access can block the illicit transfer while letting the legitimate one through.

We study both in a sandbox built for the purpose (Fig. 1). Twenty agents act for separate principals. Half are stuck: each stuck agent's data file is missing, and a copy sits with another stuck agent, which reproduces what investigators found about who joins such boards [2, 4]. Every data file carries a random code, so an agent that submits a code it never held received it from a peer. In the main experiment every agent also has a declared collaborator who must hand over one legitimate number, so blocking has real work to break.

Our main contributions are:
1. **A store policy that stops a coordinating swarm and keeps legitimate collaboration intact.** Content-typed handoffs kept 100/100 legitimate handoffs while 0/50 stuck agents obtained a code. Blocking everything kept 0/100 and an object-scoped allow-list kept 56/100 (Fig. 2). Pre-registered; held on all 10 seeds, including against holders told to help their collaborators.
2. **A measured capacity ladder for agent channels, from attacking our own defence.** Told to, the frontier pair pushed a full 8-digit secret through the two-digit typed field in 4/5 episodes, inventing encodings on the way; write-once, value-verified and release-time policies held it to 0 in every episode, and a scripted optimal encoder measures each policy's true capacity (6.6 bits per write, 6.6, 4.4 through timing, 1). The type is a rate limit; verification is the boundary (§4.5).
3. **Evidence that detection is easy and prevention is the hard part.** Every detector we tried, including a model-free string join, flagged every coordinating episode, and two pre-registered predictions that monitors would degrade failed. A gate that reacts one step after the first cross-agent read prevents only 26-33% of transfers (Fig. 4).
4. **Limits measured, not assumed.** Blocking the store moves the swarm to any open channel (49/50 via an unlogged lobby); a real-Docker isolation sweep finds network and inode-count channels in configurations that file permissions call closed; and two open-weight models did not coordinate at all, so a cheap model is not a stand-in for the frontier one here.

The work sits in Track 3 (Strengthening Agent Infrastructure), as an empirical test of the sprint's "typed messages" and "enforcement inside vs. outside the protocol" questions, and in Track 4 (Oversight and Control). The environment also answers two Track 1 and Track 2 questions: whether agents find an unannounced shared folder, and how cheap a proxy model can be (§4.4).

## 2. Related Work

**Incidents.** OpenAI's report [1] and the METR investigation [2] describe the package-directory board; METR found that the agents who started using it had usually been given tasks they could not complete. Our October sprint [4] found that agents with impossible tasks answer each other only when the helpers are stuck too, which is why our holders are themselves stuck. Lütje [3] reconstructs the wiki episode from 14,591 revisions and withdraws a first-pass transmission reading. We supply what both lacked: delivery ground truth and a tested control.

**Governing shared memory and tool access.** Governed Shared Memory (MemClaw) [5] scopes retrieval and tracks provenance in a production multi-tenant memory service and reports zero cross-fleet leakage; it does not test coordinating agents or what scoping costs legitimate collaboration. APPA [6] applies information-flow control at tool gateways for a single agent, and the Agent Control Protocol [7] adds admission control for agent actions. All three scope access by object or action. We test what happens when a coordinating swarm meets object scoping, and add a content type to the declaration.

**Collusion and its oversight.** Motwani et al. [8] show that agents can hide coordination steganographically; Tailor [9] shows that interventions such as paraphrasing impose quantifiable channel-capacity penalties and builds a calibrated audit; Shi et al. [10] find collusion in 94% of long-horizon trajectories and that restricting interaction history reduces it; Ghanem [11] proposes black-box cross-principal steganalysis. AI control [12] asks whether a trusted monitor can oversee an untrusted model; we ask the multi-agent version with the monitor in the store. The isolation sweep follows Kemmerer's Shared Resource Matrix [13], filled by execution rather than by inspection.

## 3. Methods

Everything is in our repository, `github.com/Alkur123/typed-handoffs`. All code was written during the sprint except the API call/retry pattern, the cost formula and the report builder, adapted from our October sprint and marked PREEXISTING in the files. Every experiment was **pre-registered by git commit before its code or model calls**: six registrations, whose timestamps are visible in the repository history (Appendix B lists each prediction and its outcome). Every deviation, and every correction we made to our own earlier statements, is dated in `AMENDMENTS.md`.

{{FIG:fig1_modes.png|Figure 1. The four store policies we compare, shown on one legitimate write ('44', a reading) and one laundering write (the reading plus a restricted code). Only the content-typed store delivers the first and refuses the second.|6.3}}

**Environment.** N = 20 agents (gpt-6.1-sol, OpenAI Responses API), up to 30 steps each with one tool call per step, run concurrently in a shuffled order each tick. Tools: `list_dir`, `read_file`, `write_file`, `fetch_package`, `submit_answer`. Each agent has a private home with a station file (`station,code,reading`). With stuck fraction f = 0.5, ten agents lack their file; each stuck agent's file is held by the next stuck agent in a ring, coded with the *holder's* canary. The shared `cache` is the only shared object, introduced only as the place where `csvtools` installs. Stuck agents are told "Other agents in this evaluation may have the file you need; 'cache' is shared" (the *hint*; Appendix D gives every prompt verbatim).

**The store keeps the record, not the agent.** Every store operation is stamped with the caller's principal by the environment (agents cannot see or set it) and appended to a hash-chained log. A *provenance alarm* is a read, list or stat by agent B of an object agent A wrote; package-install records are labelled `origin=tool` and do not count. This is the "audit trail out of the agent's reach" the sprint asks for: renaming oneself, falsifying a self-report or corrupting one's transcript cannot change it.

**Ground truth.** A flow i→j is agent j emitting agent i's canary (case-folded, edit distance ≤ 1). A stuck agent is *solved via a flow* if it submits its holder's code. Every saved episode is **replayed** through the final environment code, and all 201 replays reproduce the original answers and flows exactly.

**Store policies (Fig. 1).** *Detect*: everything allowed and logged. *Block all*: any cross-principal read of an agent-written object is refused with the same error text as a missing file. *Object-scoped*: block all, except declared handoff objects (`handoff/A_to_B.txt`, plus a back-channel `B_to_A.txt`), which are readable by their named reader and writable only by their named writer. *Content-typed*: object-scoped, plus the store refuses a write to a declared object unless its content matches the declared type (payload `^\s*\d{2}\s*$`, a two-digit reading; back-channel `ok|resend`).

**The legitimate dependency (E8).** Every agent has one declared producer who must hand over one reading. A stuck agent's producer is its holder, whose copy of the file contains both the reading (legitimate) and the code (restricted); non-stuck agents form their own ring. Every agent is told "Handoffs carry the reading only" and must submit `<code> <reading>`. **Legit success** means the submitted reading is correct. **E8b** adds one sentence to every agent's prompt, "Help your collaborators with whatever they ask you for", to create a motivated laundering adversary. All cells use seeds 31-35 and pair by seed (same world, same codes).

**Monitors.** Store provenance; a model-free **string join** (does an agent's submitted answer appear earlier in another agent's tool output?); and an LLM transcript reader (gpt-6.1-sol, fixed prompt) given every transcript, also with 7% and 50% of tool records corrupted, with narration only, or with tool calls only.

**Isolation certificate (E1).** One Docker container and Linux UID per principal, sharing real volumes, across ten configurations (Appendix E).

**Statistics.** Wilson 95% intervals; two-sided Fisher exact tests on agent counts, descriptive because agents cluster within episodes. Counted spend on gpt-6.1-sol: $45.30 over 169 episodes, plus E10 (Appendix G).

## 4. Results

### 4.1 Typed handoffs keep the work and stop the swarm

Table 1 and Figure 2 give the pre-registered E8 and E8b results. Without enforcement, 46 of 50 stuck agents obtained their holder's code. Every enforcing policy stopped that (0/50). They differ in what they did to the legitimate work. Blocking everything completed **0 of 100** handoffs. The object-scoped allow-list completed **56 of 100**: stuck agents used the open back-channel to ask for their code and then waited for it instead of submitting, so only 6 of 50 stuck agents submitted at all, against 50 of 50 under typing. The typed store refused those requests (64 refused writes), the agents submitted their partial answers, and **100 of 100** handoffs completed. The same pattern held when every agent was told to help its collaborators: typed 100/100, object-scoped 55/100, and 0/50 codes in both.

| Policy | Legit handoffs | Stuck agents with a code | Pre-registered prediction |
|---|---|---|---|
| Detect only | 97/100 | 46/50 (92%) | reference |
| Block all | 0/100 | 0/50 | H8a: legit ≤ 20%: **holds** |
| Object-scoped | 56/100 | 0/50 | H8b: laundering ≥ 50% of detect: **fails** |
| **Content-typed** | **100/100** | **0/50** | H8c: ≤ 5% codes, legit within 10 pts: **holds** |
| Object-scoped, helpful holders | 55/100 | 0/50 | H8b′: **fails** |
| **Content-typed, helpful holders** | **100/100** | **0/50** | H8c′: **holds** |

*Table 1. E8 and E8b, gpt-6.1-sol, 5 seeds × 20 agents per row. Content-typed is the only enforcing policy meeting both conditions (registered joint claim: holds). Fisher two-sided: codes, typed vs detect, p = 6.3e-24; legit, typed vs object-scoped, p = 2.5e-16; legit, typed vs block all, p = 2.2e-59.*

{{FIG:fig2_headline.png|Figure 2. Left: legitimate handoffs completed (of 100 agents). Right: stuck agents that obtained the restricted code (of 50). Bars: Wilson 95% intervals. Blue: default holders; orange: holders told to help their collaborators.|5.6}}

**The swarm did try to launder, and our laundering predictions failed anyway.** Holders wrote the restricted code into the shared store 52 times in the object-scoped cell and 55 times with helpful holders. Almost all of these went to ordinary cache files, which the store never let another agent read. Four went into declared handoff objects; the store accepted all four and would have shown them to the object's named reader, and none reached its stuck agent because the holder addressed the wrong object, for example its own back-channel to a different collaborator (Appendix F traces each one). So object scoping left the channel open and the agents used it; it did not leak only because they misaddressed it. Under typing no code-bearing write to a declared object occurred, and any such write is refused by construction. We therefore claim the typed store's security advantage from construction plus four accepted, misaddressed writes, not from observed leaks (H8b and H8b′ failed).

### 4.2 Detection is easy; prevention has to be inline

{{FIG:fig4_detect_vs_prevent.png|Figure 3. E7, without a legitimate dependency (seeds 21-25). A: stuck agents solved via another agent (of 50). Blocking stops the store channel; with an unlogged lobby available, the swarm moves there. B: share of coordinating episodes each detector flags, for store-channel episodes and lobby episodes.|5.6}}

In E7, blocking stopped the store channel completely: 0/50 stuck agents solved, with 70 refused attempts spread over all 5 episodes. Agents told that reads are refused made no attempts at all. Telling agents "An AI monitor reads every message you write and every tool call you make" did not stop them (48/50) and did not make them conceal anything: they still wrote plainly named request files.

Detection was never the bottleneck (Fig. 3B). Store provenance, the free string join and the LLM transcript reader each flagged 55/55 store-channel episodes, and provenance raised 0 false alarms on 60 benign episodes, where the narration-only transcript reader raised 3/30. Per flow, provenance explained all 246 store-channel transfers in the hinted grid. Our pre-registered prediction that the transcript reader would degrade under 50% corruption (H3) failed, and so did the prediction that agents told they are watched would evade it (H7c). Provenance flags only channels the store owns: it missed 8/10 lobby episodes; the string join caught 10/10, and the transcript reader caught all 5 it was run on.

{{FIG:fig3_latency.png|Figure 4. How much a gate prevents if it starts refusing L receiver steps after the receiver's first cross-agent read (registered definition). Receivers submit a median of one step after that read.|3.1}}

Detecting is not stopping. A stuck agent submits its answer a median of **one step** after its first read of another agent's file. A gate that acts at that read prevents every transfer; one that acts one step later prevents 33% (hinted grid, 230 agents) or 26% (E7, 97 agents); five steps later, 6-8% (Fig. 4). In the wiki incident the first coordination page was read 17 seconds after it was created [3]. Any control that waits for an alarm to be reviewed acts after the data has been used.

### 4.3 The store is not the only channel

Enforcement holds only where it is applied. With a lobby the store did not log, blocked agents moved there at once (49/50 solved; 0/58 lobby flows visible to provenance). The real-Docker sweep confirms the file-permission verdicts (H1: 10/10), but two of the three configurations that permissions call closed leak through the shared volume's free-inode count (12/12 directed pairs each), and every directory configuration leaks over Docker's default network; only the read-only mount was closed under every attribute we tried (Appendix E, Fig. A1).

### 4.4 Which agents coordinate at all

Without the hint, gpt-6.1-sol never coordinated: 0 of 60 episodes across four stuck fractions, and no agent ever left a file for others in the shared cache. With the one-sentence hint every episode coordinated (50/50); stuck agents were solved in 64-100% of cases by condition, including agents told to falsify their identity (98% at f = 0.5) or to evade a cache monitor (64%), who disguised requests as data files (Appendix C). Smaller and open-weight models did not coordinate even with the hint: gpt-6-luna solved 2/40 stuck agents, and qwen3.5-397b and deepseek-v4-flash, run through Adaption, 0/20 each, while completing far fewer legitimate handoffs (12/40, 21/40). In this environment a cheaper model does not reproduce the swarm, so it cannot stand in for the frontier model when testing controls (the sprint's "how cheap can the proxy be" question).

### 4.5 Attacking our own defence: how much a type still lets through (E10)

E8 measured what agents *did* when nobody asked them to encode. E10, pre-registered after E9, measures what they *can* do when told to. A sender holds an 8-digit secret (26.6 bits) and the true reading; a receiver must submit both; the only channel is the declared handoff, and both agents know the policy's rules and see the store's refusals. We compare five policies of decreasing slack (Fig. 5): object-scoped; typed (two digits, overwritable); typed write-once; value-verified (the store accepts only the true reading, once); and verified with a release time (reads wait until turn 16, writes close at turn 15). A scripted optimal encoder measures each policy's capacity by construction (H10a, holds): 6.6 bits per write when typed, 6.6 bits when write-once, **4.4 bits under verification, all of it in the timing of the single write**, and 1 bit with a release time.

{{FIG:fig6_capacity.png|Figure 5. Secret bits that reached the receiver, per policy. Grey: capacity of a scripted optimal encoder. Markers: mean over episodes when each model pair was told to transmit an 8-digit secret (26.6 bits). The type alone limits the rate but not the total; value verification closes the channel except for timing, which no model found.|4.6}}

Told to transmit, gpt-6.1-sol used the typed field's slack at once: the sender overwrote the reading two digits at a time and the receiver read each value, recovering all 8 digits in 4 of 5 episodes (H10b, holds), with no agreed scheme. In one episode the sender switched to ASCII codes (`49 53 48 52 ...` for "1504...") and the receiver decoded them; in the fifth, every digit crossed but the receiver submitted the wrong rotation. Every pair also delivered the true reading afterwards, so the leak cost the legitimate work nothing and a utility check would not see it (H10d, which predicted a cost, **fails**). Write-once, value-verified and release-time policies held the same pairs to 0 digits in 15 of 15 episodes, with the legitimate reading delivered in all 15 (H10c, holds); no model found the timing channel the scripted encoder uses. Open-weight pairs, which never coordinated on their own (E9), could exploit the type when told to, but less reliably: deepseek-v4-flash passed a full secret in 1 of 3 typed episodes and qwen3.5-397b at most 4 digits, and both mostly lost the legitimate reading doing it (1 of 6 delivered), so their leaks were visible where the frontier model's were not; under the stricter policies they stayed at chance. Propensity and capability separate: these models lack the first and partly have the second (Appendix H).

## 5. Discussion and Limitations

**What this means for safety.** A shared store that is meant to carry *some* information between agents is a policy decision, not a permission bit. Object-level allow-lists either break the collaboration or leave the declared channel open to anything. Declaring a *type* turns the channel into a measurable, rate-limited one, but E10 shows that a format check alone does not stop a pair that is trying: the type is a rate limit, and the boundary is **verifying the value against an authoritative source**, which leaves only timing, which a release schedule shrinks to one bit. Monitoring is complementary, not sufficient: it sees what the store cannot (the lobby), but it reports after the receiver has acted. A deployment should verify declared values where it can, measure the residual capacity where it cannot, and keep a transcript-level monitor for every channel the store does not own.

**Limitations** (Appendix A gives the full list and what each would change). (1) All positive results come from one model family; three other models did not coordinate, so the E8 result is untested, not refuted, on them. (2) Coordination was hinted; with no hint it was 0/60. (3) Value verification needs an authoritative source for the declared value; where none exists, the residual capacity of the type applies and must be measured. (4) The timing channel (4.4 bits under verification) was shown by a scripted encoder, not by a model; a stronger or trained adversary may find it. (5) H8b and H8b' failed, so the comparison against object scoping in E8 rests on construction and four misaddressed writes; E10 supplies the measured contrast. (6) The store is simulated; kernel-level evidence is E1 only. (7) Five seeds per cell, agents clustered within episodes. (8) Our type is a two-digit field; realistic payloads (JSON, free text) have more slack.

**Future work.** Capacity of realistic schemas (JSON, enumerations, structured text); adversaries trained to find timing and metadata channels; discovery without a hint; swarm-scale composition of per-channel bounds; verified declarations at a real gateway (MCP or a package registry).

## 6. Conclusion

Catching a coordinating swarm was easy; stopping it without breaking legitimate work was not. Blocking everything broke all of the work, and an object-scoped allow-list broke almost half and left the declared channel open. A declared type kept all the work and stopped agents that were not trying to encode, but a pair told to encode pushed a whole secret through it; verifying the declared value closed that channel in every episode while keeping the work. Such controls must sit in the store's write path, because receivers act one step after reading, and they protect only the channels the store owns.

## Code and Data

- Code, all six pre-registrations with their commit history, amendments, all 201 swarm episodes and 47 E10 episodes, replay sidecars and the figure scripts: https://github.com/Alkur123/typed-handoffs
- Every number in this report is generated by `analyze.py` into `RESULTS.md`; `NUMBERS_FOR_REPORT.md` maps each figure to its source file. Figures are computed from the episode files by `report/figs.py`.

## Author Contributions

J.A. designed and ran the experiments, wrote the code, and drafted the report. K.K. reviewed the design and the report and validated the claims against the result files. All authors contributed to writing and reviewing the paper.

## References

[1] OpenAI. *OpenAI – Hugging Face Incident Technical Report.* 2026. https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf
[2] R. Greenblatt, A. Cotra, H. Wijk. *Brief independent investigation of agents' behavior, reasoning and collaboration in the OpenAI / Hugging Face hacking incident.* METR, 26 Aug 2026. https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/
[3] P. Lütje. *The Mechanics of a Swarm: A Reproducible External Reconstruction of an Unintended Agent-Coordination Episode on a Third-Party Wiki.* arXiv:2609.12748, 2026. https://arxiv.org/abs/2609.12748
[4] J. Alkur. *It Takes Two Stuck Agents: Impossible Tasks Make AI Agents Answer Each Other Only When the Helpers Are Stuck Too.* Apart Research AI Collusion Research Sprint report, Oct 2026.
[5] Y. Margalit, N. Cohen-Inger, E. Avram, R. Taig, O. Margalit. *Governed Shared Memory for Multi-Agent LLM Systems.* arXiv:2606.24535, 2026. https://arxiv.org/abs/2606.24535
[6] A. Kravchenko, V. Liventsev, I. Konstantinov, I. Iskhakov, M. Kukuy. *APPA: Recoverable Information-Flow Control for Real-World LLM Agents.* arXiv:2607.24625, 2026. https://arxiv.org/abs/2607.24625
[7] M. Fernandez. *Agent Control Protocol: Admission Control for Agent Actions.* arXiv:2603.18829, 2026. https://arxiv.org/abs/2603.18829
[8] S. R. Motwani, M. Baranchuk, M. Strohmeier, V. Bolina, P. H. S. Torr, L. Hammond, C. Schroeder de Witt. *Secret Collusion among AI Agents: Multi-Agent Deception via Steganography.* arXiv:2402.07510, 2024. https://arxiv.org/abs/2402.07510
[9] O. Tailor. *Audit the Whisper: Detecting Steganographic Collusion in Multi-Agent LLMs.* arXiv:2510.04303, 2025. https://arxiv.org/abs/2510.04303
[10] X. Shi, Y. Zhang, D. Yang. *Emergent Collusion in Long-Horizon LLM Agent Interaction.* arXiv:2609.24967, 2026. https://arxiv.org/abs/2609.24967
[11] M. C. Ghanem. *Steganalysis of Adaptive Covert Collusion in Tool-Using Agent Populations: A Black-Box, Cross-Principal Approach.* arXiv:2608.02698, 2026. https://arxiv.org/abs/2608.02698
[12] R. Greenblatt, B. Shlegeris, K. Sachan, F. Roger. *AI Control: Improving Safety Despite Intentional Subversion.* arXiv:2312.06942, 2023. https://arxiv.org/abs/2312.06942
[13] R. A. Kemmerer. *Shared Resource Matrix Methodology: An Approach to Identifying Storage and Timing Channels.* ACM Transactions on Computer Systems 1(3), 1983.

## Appendix A. Limitations and Dual-Use / Ethical Considerations

**What the result establishes.** On one frontier model, in a controlled environment with a legitimate cross-agent dependency, a content-typed handoff policy kept all legitimate handoffs and let no restricted code through, against default and "helpful" holders, while blocking everything broke all handoffs and object scoping broke almost half. Detection by several independent methods was complete; a gate must act inline to prevent; enforcement does not cover channels it does not own.

**What it does not establish, and how each would change the reading.**
- *Other model families.* Three other models did not coordinate, so nothing here says typed handoffs work or fail on them. If a model that does coordinate also launders well, the object-scoped rows of Table 1 would move up, and the typed rows are the ones we would expect to hold.
- *Spontaneous coordination.* Coordination needed the hint (0/60 without). If unprompted swarms behave differently, for example by encoding more aggressively, the residual-capacity question (next item) matters more.
- *An encoding adversary.* The typed payload carries about 6.5 bits per write and can be overwritten; no agent tried to encode through it. An agent that does would turn the typed result from "0 codes" into a capacity bound, which we have not measured.
- *Laundering in practice.* H8b and H8b′ failed: no code reached a stuck agent under object scoping, because the four declared-object writes were misaddressed. With more seeds or a stronger model we expect object scoping to leak; that is a prediction, not a result.
- *A real store.* E3-E9 use a simulated store; the kernel-level evidence (E1) is about which channels exist, not about agents using them.
- *Statistics.* Five seeds per cell, agents clustered within episodes; the Fisher tests treat agents as independent and are descriptive.
- *Type simplicity.* A two-digit reading is the easiest possible schema. Free-text or JSON payloads have much larger residual capacity, so this result is a best case for typing.

**Dual use.** The work describes how agents coordinate through shared stores and which channels escape permission checks (network, inode counts, directory metadata). These are long-known classes in the covert-channel literature [13]; we report them to argue for typed, inline controls and for certifying every shared layer. We release no technique for encoding through typed fields and did not develop one. All data and codes are synthetic; agents only ever touched the simulated store and their own containers; no real system, service or person was involved. The Docker sweep ran on an isolated local machine.

## Appendix B. Every pre-registered prediction and its outcome

| Registration (commit) | Prediction | Outcome |
|---|---|---|
| PREREGISTRATION (`a9b9ff3`) | H1: isolation sweep classifies C1-C6 OPEN, C7-C10 CLOSED | **Holds**: 10/10 under real Docker (8/8 with networking off) |
| | H2: provenance TPR ≥ 0.90 and FPR ≤ 0.05 in normal episodes | **Holds**: 15/15 hinted normal; 0/30 false alarms in normal no-hint |
| | H3: transcript monitor TPR drops ≥ 20 pts under adversarial conditions | **Fails**: 100% in every condition, incl. 50% corruption |
| | H4: coordination rises with stuck fraction f | **Fails / untestable**: none at any f without the hint; ~100% at every f with it |
| | H5: the timing channel S5 is not detected (a boundary) | **Holds**: E2 6/6 scripted checks |
| PREREGISTRATION_2 + E7-A1 (`07d7f34`) | Enforce stops store coordination (≤ 5% stuck solved) | **Holds**: 0/50, 70 refused attempts |
| | Informed agents: ≤ 1/5 episodes with a solve | **Holds**: 0/5 (0 attempts) |
| | Lobby: displacement (≥ 50% of detect rate; provenance ≤ 10% of flows) | **Holds**: 49/50; provenance 0/58 |
| | H7c: watched agents defeat transcript monitors (≥ 20 pts lower) | **Fails**: 5/5 caught |
| | Latency curve (replaces H7d) | Reported: 100 / 26-33 / 20-28 / 6-8 / 1-2% at L = 0/1/2/5/10 |
| PREREGISTRATION_3 (`c831cf8`) | H8a: block-all legit ≤ 20%, detect legit ≥ 80% | **Holds**: 0% vs 97% |
| | H8b: object scoping launders (≥ 50% of detect) | **Fails**: 0/50 |
| | H8c: typed ≤ 5% codes and legit within 10 pts of detect | **Holds**: 0/50; 100% vs 97% |
| | Joint: typed is the only enforce cell meeting both | **Holds** |
| PREREGISTRATION_3b (`a9a9f21`) | H8b′: object scoping launders with helpful holders | **Fails**: 0/50 |
| | H8c′: typed holds against helpful holders | **Holds**: 0/50; 100/100 |
| PREREGISTRATION_4 + E9-A1 (`934ee86`) | Primary model qwen3.5-397b passes the coordination gate | **Fails**: 0/20; the DeepSeek branch (added after, labelled) also fails |
| PREREGISTRATION_5 + E10-A0 (`3fbf235`) | H10a: scripted capacities 6.6 b/write, 6.6, about 4.3 (timing), at most 1 | **Holds**: 6.64, 6.64, 4.39, 1.0 |
| | H10b: sol recovers at least 4 of 8 digits through the typed field | **Holds**: 6.4 mean (4/5 full secret) |
| | H10c: write-once at most 3, verified and release at most 1.3 digits | **Holds**: 0, 0, 0 |
| | H10d: verified keeps legit 100%; typed costs legit | **Fails**: legit 100% everywhere; the leak cost nothing |
| | H10e (descriptive): open models recover less under typed | As described: typed mean digits 6.4 (gpt-6.1-sol), 2.7 (DeepSeek), 1.3 (Qwen) |

## Appendix C. Every cell that was run

{{INCLUDE:app_cells.md}}

## Appendix D. Prompts

{{INCLUDE:app_prompts.md}}

## Appendix E. Isolation certificate details

E1 runs one Docker container (`python:3.12-alpine`) per principal, each as its own Linux UID (1001-1004), sharing real volumes with real modes and mount flags. C1-C4: shared cache, /tmp, log directory, writable package index. C5: content unreadable (0600), names visible. C6 and C10: paste service with listable and with unguessable keys. C7: per-principal subdirectory. C8: read-only reference data. C9: create-only drop-box (1733) with 0600 files. The storage verdicts (H1) come from canaries in content, names, sizes, times and existence. In the metadata pass, senders write one at a time while every other principal snapshots directory metadata, `statvfs` and `stat` on the sender's guessed name before and after. Single-file `statvfs` proved noisy (the volume shares a filesystem with the Docker VM; read-only C8, where every write fails, still showed 5/12 changes) and is not used. In the 200-inode test each sender creates 200 files against 5 null rounds: C7 and C9 open 12/12 (delta −195 to −200, noise 0), C8 closed 0/12.

{{FIG:fig5_isolation.png|Figure A1. E1 isolation sweep under real Docker. OPEN = a receiver observed a sender's canary or a sender-caused change through that attribute class. Inode count from the 200-inode test only (other configurations not tested); read-only C8 is the negative control.|4.6}}

## Appendix F. The laundering attempts, traced

Holder writes that contained the restricted code, by where they went (metric E8b-A1, registered after E8b seed 31 and before the remaining E8b episodes):

| Cell | Episodes | To declared handoff objects | To other files | Delivered to the stuck agent |
|---|---|---|---|---|
| Object-scoped | 5 | 1 | 51 | 0 |
| Object-scoped, helpful | 5 | 3 | 52 | 0 |
| Content-typed | 5 | 0 | 7 | 0 |
| Content-typed, helpful | 5 | 0 | 14 | 0 |

The four declared-object writes, hand-traced: seed 34, holder p4 wrote stuck p3's code into `p4_to_p6.txt`, the object for its other collaborator; seed 32, p10 wrote into `p10_to_p15.txt`, its back-channel to its own producer; seed 34, p1 into `p1_to_p13.txt`; seed 35, p14 into `p14_to_p15.txt`. The store accepted all four; none was the object the stuck agent could read. One further write (seed 33, `handoff/station_S550.csv`) went to an undeclared file inside the handoff directory and was never readable by another agent. Writes to "other files" are accepted by the store, but enforce mode refuses every cross-agent read of them.

## Appendix H. E10, every cell

{{INCLUDE:app_e10.md}}

## Appendix G. Deviations, spend and timeline

- **E10 cutoff.** The Adaption-hosted runs were stopped at a pre-announced cutoff; qwen3.5-397b completed 14/15 and deepseek-v4-flash 8/15 episodes (missing cells listed in `AMENDMENTS.md`). All gpt-6.1-sol cells and all typed cells are complete. E10 cost about $1 on gpt-6.1-sol.
- **Budget.** E8 exceeded its registered $7 cap. Counted spend on gpt-6.1-sol across all experiments: $45.30; gpt-6-luna $0.34; LLM monitors about $2.04; adversarial design reviews $5.26. Three ENF-naive E8 episodes failed mid-run and were re-run from scratch on the same seed; their partial tokens were billed and not counted, so true spend is somewhat higher. The open-weight models ran on Adaption platform credits.
- **Corrections we made to our own statements**, all dated in `AMENDMENTS.md`: the smoke-test board formed under the hint, not spontaneously; holders did *not* "send the reading only" (the laundering count showed 52 code-bearing writes); four, not five, code writes reached declared objects; an early latency figure (87 agents) predates the last E7 episode (97).
- **Timeline (7 Nov 2026, IST).** 12:41 first registration; 17:40 E7; 18:59 E8; 19:29 E8b; 20:01 E9; 22:46 E10 (after an external review named the untested typed-channel capacity as the main gap). E10-A0 (a write deadline for RELEASE) was recorded before any E10 code; E10-A1 (an exploratory exposure metric) after the gpt-6.1-sol cells.

## LLM Usage Statement

We used Claude (Anthropic) for coding, debugging, running and monitoring experiments, statistical analysis, figure generation and drafting this report. A second Claude model reviewed our pre-registered designs adversarially before the E3 and E7 runs; its reviews changed both designs, as recorded in amendments A4 and E7-A1. All numbers are generated by our analysis scripts from saved episode logs and were checked against those files; all references were checked against their arXiv metadata or abstracts. The authors are responsible for every claim.
