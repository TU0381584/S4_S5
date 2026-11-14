# WPC pre-submission changelog

Branch `wpc-presubmission`. One entry per change: gate, file and place, old text, new text, reason.

## Gate 0

No edits. Baseline: main 29 pp, OR1 10 pp, m66_verify 674/674, m82 57/57, CI 21 same.

## Gate 1

| # | File, place | Old | New | Reason |
|---|---|---|---|---|
| 1.1 | refs.bib gong2026femaddpg author | `author  = {Gong, Yu and Gong, P. and Jiang, He and Xie, W. and Wang, C. and Xu, P.},` | `author  = {Gong, Yu and Gong, Pengwei and Jiang, He and Xie, Wen and Wang, Chenxi and Xu, Peijun},` | Crossref gives full given names (its given and family fields are swapped; family names unchanged) |
| 1.2 | refs.bib cheng2024oranslice author | `Bonati, Leonardo and Polese, Michele and Melodia, Tommaso},   title     = {{ORANSlice}` | `Bonati, Leonardo and Polese, Michele and Melodia, Tommaso and Arrobo, Gabriel and Maciocco, Christian},   title     = {{ORANSlice}` | Crossref and the ACM record list ten authors; two were missing |
| 1.3 | refs.bib barlacchi2015milan number | `  volume  = {2},   pages   = {150055},` | `  volume  = {2},   number  = {1},   pages   = {150055},` | Crossref gives issue 1 |
| 1.4 | refs.bib velickovic2018gat | `(none)` | `new entry` | primary source added, record fetched from Crossref or the publisher page (docs/reference_audit.md) |
| 1.5 | refs.bib mcmahan2017fedavg | `(none)` | `new entry` | primary source added, record fetched from Crossref or the publisher page (docs/reference_audit.md) |
| 1.6 | refs.bib mnih2015dqn | `(none)` | `new entry` | primary source added, record fetched from Crossref or the publisher page (docs/reference_audit.md) |
| 1.7 | refs.bib schulman2017ppo | `(none)` | `new entry` | primary source added, record fetched from Crossref or the publisher page (docs/reference_audit.md) |
| 1.8 | refs.bib oliehoek2016decpomdp | `(none)` | `new entry` | primary source added, record fetched from Crossref or the publisher page (docs/reference_audit.md) |
| 1.9 | refs.bib wilcoxon1945 | `(none)` | `new entry` | primary source added, record fetched from Crossref or the publisher page (docs/reference_audit.md) |
| 1.10 | refs.bib efron1979bootstrap | `(none)` | `new entry` | primary source added, record fetched from Crossref or the publisher page (docs/reference_audit.md) |
| 1.11 | refs.bib gupta2017cooperative | `(none)` | `new entry` | primary source added, record fetched from Crossref or the publisher page (docs/reference_audit.md) |
| 1.12 | refs.bib vanhasselt2016popart | `(none)` | `new entry` | primary source added, record fetched from Crossref or the publisher page (docs/reference_audit.md) |
| 1.13 | main.tex Sec. 1 | `including a deep Q-network (DQN), can protect` | `including a deep Q-network (DQN)~\cite{mnih2015dqn}, can protect` | primary source for DQN |
| 1.14 | main.tex Sec. 1 | `The encoder is a graph attention network (GAT)~\cite{wu2021gnnsurvey}, and` | `The encoder is a graph attention network (GAT)~\cite{velickovic2018gat}, one kind of graph neural network~\cite{wu2021gnnsurvey}, and` | GAT cited to its source; Wu et al. kept as the survey it is |
| 1.15 | main.tex Sec. 3 | `forms a decentralised partially observable Markov decision process.` | `forms a decentralised partially observable Markov decision process~\cite{oliehoek2016decpomdp}.` | Dec-POMDP reference |
| 1.16 | main.tex Sec. 4 | `AXIOM trains one encoder over the whole cluster from every agent's experience and reads out one Q-head per slice.` | `AXIOM trains one encoder over the whole cluster from every agent's experience, a form of parameter sharing~\cite{gupta2017cooperative}, and reads out one Q-head per slice.` | parameter-sharing reference |
| 1.17 | main.tex Sec. 4.1 | `cannot swamp mMTC's smaller learning signal in a shared head, which Section` | `cannot swamp mMTC's smaller learning signal in a shared head, a known difficulty when reward scales differ~\cite{vanhasselt2016popart}, which Section` | reward-scale reference (PopArt) |
| 1.18 | main.tex Sec. 4.2 | `sends its weights for FedAvg~\cite{lim2020flmec}.` | `sends its weights for FedAvg~\cite{mcmahan2017fedavg}, as surveyed for mobile edge networks in~\cite{lim2020flmec}.` | FedAvg cited to its source; Lim et al. kept as the survey it is |
| 1.19 | main.tex Sec. 5 | `MAPPO~\cite{yu2022mappo} is a published multi-agent baseline with a shared actor and a centralised critic,` | `MAPPO~\cite{yu2022mappo} is a published multi-agent baseline that extends proximal policy optimisation~\cite{schulman2017ppo} with a shared actor and a centralised critic,` | PPO reference |
| 1.20 | main.tex Sec. 5 | `are 95\% bootstrap percentile intervals over 10{,}000 resamples.` | `are 95\% bootstrap percentile intervals over 10{,}000 resamples~\cite{efron1979bootstrap}.` | bootstrap reference |
| 1.21 | main.tex Sec. 5 | `Paired comparisons use the Wilcoxon signed-rank test,` | `Paired comparisons use the Wilcoxon signed-rank test~\cite{wilcoxon1945},` | Wilcoxon reference |
| 1.22 | refs.bib wilcoxon1945 pages | `80--83` (typed in 1.x, never committed) | `80` | Crossref records the first page only; the range had come from memory |
| 1.23 | docs/reference_audit.md | (none) | new file | one row per reference with verdict and evidence URL |
