# WPC pre-submission correction pass, change log (2026-11-18)

Format: file, location, old -> new, reason. M = main.tex, S = supplementary.tex (Online Resource 1), B = refs.bib.

## Phase 0 (read-only, results reported to the author)
V1 text 4.2/3.9/4.99 is the paired hex lead; Table S8 caption said 1,620 runs but its cells are the pooled 2,130. V2 13 of 165, 56.4-66.8%. V3 accept-all 67.08% (19) and 61.94% (37). V4 12 seeds, 7 ties. V5 gap at 19 gNBs is at most 3.12 pooled / 3.76 per layout, so "5.3" is unsupported. V6 QMIX -0.288 reward, Holm p 1.0. V8 nine failed checks listed in the reply. V10 58 of 58 DOIs resolve (302).

## Phase 1 (main)
- M abstract: replaced by the supplied 249-word text. Reason: 1.1. The "3.9 to 5.0" stays (Phase 0 V1 confirms 4.99).
- M Sec 3: "exposes to xApps, the external control applications of O-RAN" -> "exposes to external controllers through its E2 agent", with \cite{cheng2024oranslice} after OAI. 1.2.
- M Sec 3: control-step sentence now names the 10 ms to 1 s near-real-time RIC loop. 1.3.
- M Sec 3: "which saturates in Env B at nineteen gNBs" -> "which falls to a floor ... where it no longer separates the policies". 1.4.
- M Sec 5: "same 60 seeds" -> "same 60 seeds plus 15 more, 75 in all"; "Every campaign" -> "Unless stated otherwise, every campaign". 1.5. (The phrase "same 60 seeds" is kept inside the new wording, as the instruction's own text contains it.)
- M Sec 5: "Block precision $\pi = b/b$" -> "Block precision, $b_{mMTC}/b$,". No other use of pi for precision exists. 1.6.
- M Sec 5 safeguards: validation-screen sentence moved to the end of the paragraph. 1.7.
- M Sec 5: "above 99.98%" -> "at 99.97% or more". 1.8.
- M Sec 5 end: AI-assistant sentence added, pointing to Sec 6.6. 1.9.
- M Sec 6: mMTC admission 60.9% vs 5.5% -> 60.7% vs 7.6% (pooled, same as Sec 6.1). 1.10.
- M Sec 6.1: p = 0.007 -> 0.0066 (verifier to confirm in Phase 3). 1.11.
- M Table 3 header W/T/L (n = 60) -> (n = 75). The Env B table keeps n = 60, which is correct. 1.12.
- M Sec 6.2: "each layout-independent baseline was run once per seed" merged into the 37-gNB paragraph. 1.13.
- M Sec 6.2: "no other learner" -> "none of DQN-SA, DQN-I, and MAPPO"; QMIX sentence added. 1.14.
- M Sec 6.4: static-rule-over-tuned-rule sentence added (source: S7, 8.05 to 10.63; 1.8 to 2.0). 1.15.
- M Sec 6.7 heading -> "Live Testbed Check". 1.16.
- M Sec 6.6 and S1: "except the one reused rerun disclosed in Section 5" / "except the reused rerun that Section S4 discloses". 1.17.
- M Sec 7: rules paragraph rewritten as supplied, but "as Fig. 10b shows" replaced by "(Section S7 of Online Resource 1)". Reason: Fig. 10 is the capability figure and Fig. 11b compares AXIOM with the tuned rule only, so neither shows static over tuned; the source is OR1 S7. 1.18.
- M Sec 7: MLP-encoder exception added after "No learned baseline earns significantly more reward". V6 shows QMIX is not significantly ahead, so QMIX is not added. 1.19.
- M Sec 7: "Among the learned controllers of Fig. 10". 1.20.
- M Sec 8: "every learned baseline stays below 84%" -> "DQN-SA, DQN-I, and MAPPO stay below 84%". 1.21.
- Fig. 8 tick label "Tuned neighbour rule": left for Phase 4. 1.22.
- M Table 5: no change. The AXIOM row already has "--" in both W/T/L cells. 1.23.
- M Declarations, AI item: now "Claude Code (Anthropic), running Claude Opus models in Visual Studio Code". AUTHOR TO CONFIRM IDE and whether the AI drafted manuscript prose; if so, state it explicitly. This replaces the wording the author gave on 2026-11-18. 1.24.
- B ORANSlice: NOT changed. Crossref for 10.1145/3636534.3701544 gives the title "ORANSlice: An Open Source 5G Network Slicing Platform for O-RAN", the container "Proceedings of the 30th Annual International Conference on Mobile Computing and Networking" and the author order already in refs.bib. The supplied workshop title, booktitle and author order do not match the DOI record. AUTHOR TO DECIDE.
- B page ranges in number fields {3-4} -> {3--4} (2 entries). 1.25.
- B Patterson et al.: url https://jmlr.org/papers/v25/23-0183.html added; the page title is "Empirical Design in Reinforcement Learning". 1.25.
- B OACR2: title is "{OACR$^{2}$}: Online ..." which renders with no space before the colon. No change. 1.25.

## Phase 1E (Online Resource 1)
- S S6: garbled ".7% and 92.0%" removed. E1.
- S S4: live-testbed sentence now reports the PRB grants below the five-PRB floor found before the root fix. E2.
- S Table S2 caption: sentence on the 15 newest seeds (Table S4) and 75 seeds added. E3.
- S S5: "pooled over these 40 seeds, the 30 primary and 10 replication seeds and not the 75-seed sample of the main paper". E4.
- S S7: "In Env B," added before "past the tuning load at nineteen gNBs". E5.
- S Table S12 p values: 8.8e-05 and 1e-05 -> <0.0001; 0.00016 -> 0.0002. E6.
- S S8: duplicate definition of normalised backlog removed. E7.
- S S4 Eqs (1) and (2): attention logits renamed e (epsilon kept for DP); N_i includes i; the second equation reads h_j^(1) and is stated to be the final layer. Self-loops are on by default (framework topology.py). E8.
- S Table S17: Fig1 to Fig11; "m97" -> m104_run.py, plus m109_run.py; seed list extended. m97 is an analysis script, not a runner. E9.
