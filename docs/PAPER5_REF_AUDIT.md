# Paper 5 (WPC) reference audit

Checked 2026-11-05 against the Crossref REST API (api.crossref.org/works/<doi>). Reference numbers are those of the compiled main.pdf. The bib was not edited.

| No. | Key | Title in bib | Title at DOI | Authors match | Venue, volume, pages | Status |
|---|---|---|---|---|---|---|
| [2] | ahmadi2024generalizable | Generalizable 5G RAN/MEC Slicing and Admission Control for Reliable Network Operation | Generalizable 5G RAN/MEC Slicing and Admission Control for Reliable Network Operation | yes | yes | OK |
| [6] | bouroudi2025gnnmarl | GNN-Based Multi-Agent DRL for Energy-Efficient Multi-Domain 6G Resource Orchestration | GNN-Based Multi-Agent DRL for Energy-Efficient Multi-Domain 6G Resource Orchestration | yes | matches, see note | OK (naming only) |
| [9] | fatehi2026attentionmarl | Interpretable Attention-Based Multi-Agent PPO for Latency Spike Resolution in 6G RAN Slicing | Interpretable Attention-Based Multi-Agent PPO for Latency Spike Resolution in 6G RAN Slicing | yes | matches, see note | OK (naming only) |
| [10] | gong2026femaddpg | Intelligent Resource Allocation for Multiaccess Edge Computing in 5G Ultra-Dense Slicing Network Using Federated Multiagent DDPG Algorithm | Intelligent resource allocation for multiaccess edge computing in 5G ultra-dense slicing network using federated multiagent DDPG algorithm | yes, see note | yes | OK (naming only) |
| [12] | kamal2026ddqn | Reinforcement Learning Double Deep Q-Network Techniques for NextG Network | Reinforcement learning Double Deep Q-Network Techniques for NextG Network | yes | yes | OK |
| [14] | krishnamoorthy2026federated | Federated Learning for Dynamic Resource Allocation in 6G Network Slicing | Federated Learning for Dynamic Resource Allocation in 6G Network Slicing | yes | yes | OK |
| [20] | li2026scalablemarl | A Flexible and Scalable Multi-Agent Learning Framework for Dynamic RAN Slicing in 6G Native-AI Networks | A Flexible and Scalable Multi-Agent Learning Framework for Dynamic RAN Slicing in 6G Native-AI Networks | yes | yes | OK |
| [23] | mohajer2026pronto | Joint SLA-Aware Task Offloading and Adaptive Service Orchestration With Graph-Attentive Multi-Agent Reinforcement Learning | Joint SLA-Aware Task Offloading and Adaptive Service Orchestration With Graph-Attentive Multi-Agent Reinforcement Learning | yes | yes | OK |
| [35] | tashman2026adversarial | Adversarial Attacks in AI-Driven RAN Slicing: SLA Violations and Recovery | Adversarial Attacks in AI-Driven RAN Slicing: SLA Violations and Recovery | yes | matches, see note | OK (naming only) |

Notes

- bouroudi2025gnnmarl: Same conference; the bib gives the proceedings name, Crossref the event name. Pages 4457-4462 match.
- fatehi2026attentionmarl: Same conference; proceedings name versus event name. Pages 1-6 match.
- tashman2026adversarial: Same conference; proceedings name versus event name. Pages 1391-1396 match.
- gong2026femaddpg: Crossref's record swaps given and family names (given 'Gong', family 'Yu', and so on). The bib's order, Gong Y, Gong P, Jiang H, Xie W, Wang C, Xu P, is the publisher's. China Communications 23(1):273-289 matches.

Summary: 9 references checked, 9 resolve, 9 titles and years match. 5 match exactly; 4 differ only in how Crossref names the venue or orders Chinese names. No bib change is needed.

## Gate C additions, 2026-11-06

Resolved through the Crossref REST API, with the Semantic Scholar API for the CNSM abstract and the NeurIPS proceedings page for the one work without a DOI. No arXiv version is cited. Six entries were added to refs.bib and no existing entry was changed.

| Key | Title | Authors | Venue | Year | Vol(no) | Pages | DOI | Source |
|---|---|---|---|---|---|---|---|---|
| cheng2024oranslice | ORANSlice: An Open Source 5G Network Slicing Platform for O-RAN | Cheng, D'Oro, Gangula, Velumani, Villa, Bonati, Polese, Melodia | Proc. 30th Annual Int. Conf. on Mobile Computing and Networking (ACM MobiCom '24), ACM | 2024 | n/a | 2297-2302 | 10.1145/3636534.3701544 | Crossref |
| doherty2025hype | Reinforcement learning for dynamic resource allocation in optical networks: hype or hope? | Doherty, Matzner, Sadeghi, Bayvel, Beghelli | Journal of Optical Communications and Networking | 2025 | 17(9) | D1 | 10.1364/JOCN.559990 | Crossref |
| henderson2018matters | Deep Reinforcement Learning That Matters | Henderson, Islam, Bachman, Pineau, Precup, Meger | Proc. AAAI Conference on Artificial Intelligence | 2018 | 32(1) | not given by Crossref | 10.1609/aaai.v32i1.11694 | Crossref |
| agarwal2021precipice | Deep Reinforcement Learning at the Edge of the Statistical Precipice | Agarwal, Schwarzer, Castro, Courville, Bellemare | Advances in Neural Information Processing Systems | 2021 | 34 | 29304-29320 | none issued | proceedings.neurips.cc citation metadata |
| asdikian2025verifying | Verifying Behavior of Reinforcement Learning Agents for Network Slice Admission Control | Asdikian, Amro, Mehyeddine, Natalino, Sbeity, Maier, Monti, Troia, Ayoub | 2025 21st Int. Conf. on Network and Service Management (CNSM) | 2025 | n/a | 1-6 | 10.23919/CNSM67658.2025.11297450 | Crossref, Semantic Scholar |
| barlacchi2015milan | A multi-source dataset of urban life in the city of Milan and the Province of Trentino | Barlacchi, De Nadai, Larcher, Casella, Chitic, Torrisi, Antonelli, Vespignani, Pentland, Lepri | Scientific Data | 2015 | 2 | article 150055 | 10.1038/sdata.2015.55 | Crossref |

Notes

- cheng2024oranslice: Crossref files it in the MobiCom '24 proceedings volume, which also holds the workshop papers. The workshop name is not in the Crossref record, so the bib gives the proceedings title.
- doherty2025hype: the JOCN version is cited. Three Optica Open preprint records (10.1364/opticaopen.28431092, v1, v2) exist and were not used. The abstract supports "simple heuristics outperform the published RL solutions" after the problem settings of five landmark papers were recreated exactly.
- asdikian2025verifying: the abstract describes a DRL admission agent, an integer linear program for slice embedding, and a Shapley-value explanation module (SVERL) used to verify the agent's behaviour before deployment. It does not describe benchmarking the agent against an optimisation result, so the citing sentence was written to match the abstract.
- agarwal2021precipice: NeurIPS issues no DOI, so none is given.
