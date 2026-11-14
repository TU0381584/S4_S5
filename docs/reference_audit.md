# Reference audit (Gate 1, 2026-11-15)

Every DOI was resolved through the doi.org handle API and its Crossref record fetched from api.crossref.org, then compared with refs.bib on title, author family names, year, volume, issue, pages and venue. DBLP refused automated queries, so entries without a DOI were checked against the publisher page. Numbers are the reference numbers in the rebuilt main paper.

## Existing entries

| No. | Key | Verdict | Evidence | Notes |
|---|---|---|---|---|
| 3 | ahmadi2024generalizable | verified | https://api.crossref.org/works/10.1109/TNSM.2024.3437217 ; https://doi.org/10.1109/TNSM.2024.3437217 |  |
| 4 | alqahtani2025dynamic | verified | https://api.crossref.org/works/10.1007/s11277-025-11835-y ; https://doi.org/10.1007/s11277-025-11835-y |  |
| 5 | amiri2024vnf | verified | https://api.crossref.org/works/10.1109/LCOMM.2023.3341302 ; https://doi.org/10.1109/LCOMM.2023.3341302 |  |
| 8 | bega2020market | verified | https://api.crossref.org/works/10.1109/TMC.2019.2896950 ; https://doi.org/10.1109/TMC.2019.2896950 | author mismatch is LaTeX accent markup only (Costa-P\'erez) |
| 9 | bouroudi2025gnnmarl | verified | https://api.crossref.org/works/10.1109/GLOBECOM59602.2025.11432814 ; https://doi.org/10.1109/GLOBECOM59602.2025.11432814 | venue wording differs from Crossref's proceedings title only (same conference and year) |
| 12 | doanis2024madqn | verified | https://api.crossref.org/works/10.1109/TMLCN.2024.3420268 ; https://doi.org/10.1109/TMLCN.2024.3420268 |  |
| 1 | dpsgd | verified | https://api.crossref.org/works/10.1145/2976749.2978318 ; https://doi.org/10.1145/2976749.2978318 |  |
| 15 | fatehi2026attentionmarl | verified | https://api.crossref.org/works/10.1109/ICC59461.2026.11586913 ; https://doi.org/10.1109/ICC59461.2026.11586913 | venue wording differs from Crossref's proceedings title only (same conference and year) |
| 16 | gong2026femaddpg | metadata corrected: four given names expanded to the full names in the Crossref record | https://api.crossref.org/works/10.23919/JCC.fa.2022-0187.202601 ; https://doi.org/10.23919/JCC.fa.2022-0187.202601 |  |
| 18 | hao2024hybridtask | verified | https://api.crossref.org/works/10.1109/TWC.2024.3487533 ; https://doi.org/10.1109/TWC.2024.3487533 | Crossref splits "Phee Lep Yeoh" differently; same person |
| 28 | cacs-paper4 | cannot verify | none | the authors' own CACS 2026 paper, marked "To appear in IEEE Xplore"; no DOI yet and no public record found; entry left untouched |
| 26 | icraie-paper2 | verified | https://api.crossref.org/works/10.1109/ICRAIE65839.2025.11239148 ; https://doi.org/10.1109/ICRAIE65839.2025.11239148 |  |
| 21 | kamal2026ddqn | verified | https://api.crossref.org/works/10.1007/s11277-026-12048-7 ; https://doi.org/10.1007/s11277-026-12048-7 |  |
| 22 | khani2024sacsurvey | verified | https://api.crossref.org/works/10.1002/dac.5857 ; https://doi.org/10.1002/dac.5857 |  |
| 23 | krishnamoorthy2026federated | verified | https://api.crossref.org/works/10.1007/s11277-026-11943-3 ; https://doi.org/10.1007/s11277-026-11943-3 |  |
| 24 | kulkarni2024actor | verified | https://api.crossref.org/works/10.1007/s11277-024-11526-0 ; https://doi.org/10.1007/s11277-024-11526-0 |  |
| 29 | li2025oacr2 | verified | https://api.crossref.org/works/10.1109/TMC.2025.3548767 ; https://doi.org/10.1109/TMC.2025.3548767 | title matches; the comparison script could not parse the nested braces of OACR$^{2}$ |
| 30 | li2026scalablemarl | verified | https://api.crossref.org/works/10.1109/TMC.2025.3642213 ; https://doi.org/10.1109/TMC.2025.3642213 |  |
| 31 | lim2020flmec | verified | https://api.crossref.org/works/10.1109/COMST.2020.2986024 ; https://doi.org/10.1109/COMST.2020.2986024 | venue wording differs from Crossref's proceedings title only (same conference and year) |
| 25 | mecon-paper1 | verified | https://api.crossref.org/works/10.1109/MECON67253.2025.11277096 ; https://doi.org/10.1109/MECON67253.2025.11277096 |  |
| 33 | ming2024fedslice | verified | https://api.crossref.org/works/10.1109/TMC.2024.3404125 ; https://doi.org/10.1109/TMC.2024.3404125 |  |
| 35 | mohajer2026pronto | verified | https://api.crossref.org/works/10.1109/TNSM.2026.3673188 ; https://doi.org/10.1109/TNSM.2026.3673188 |  |
| 36 | ojijo2024sac | verified | https://api.crossref.org/works/10.1016/j.comnet.2024.110878 ; https://doi.org/10.1016/j.comnet.2024.110878 |  |
| 38 | phyu2025icecream | verified | https://api.crossref.org/works/10.1109/TNSM.2024.3524503 ; https://doi.org/10.1109/TNSM.2024.3524503 |  |
| 39 | polese2023coloran | verified | https://api.crossref.org/works/10.1109/TMC.2022.3188013 ; https://doi.org/10.1109/TMC.2022.3188013 |  |
| 40 | polese2023oran | verified | https://api.crossref.org/works/10.1109/COMST.2023.3239220 ; https://doi.org/10.1109/COMST.2023.3239220 | venue wording differs from Crossref's proceedings title only (same conference and year) |
| 41 | rashid2020qmix | verified | https://jmlr.org/papers/v21/20-081.html | no DOI (JMLR issues none); authors, volume 21, issue 178, pages 1-51 match the JMLR page |
| 42 | raza2019slicing | verified | https://api.crossref.org/works/10.1109/JLT.2019.2924345 ; https://doi.org/10.1109/JLT.2019.2924345 |  |
| 27 | ref:access | verified | https://api.crossref.org/works/10.1109/ACCESS.2026.3716911 ; https://doi.org/10.1109/ACCESS.2026.3716911 |  |
| 44 | shao2021gatmarl | verified | https://api.crossref.org/works/10.1109/TVT.2021.3103416 ; https://doi.org/10.1109/TVT.2021.3103416 |  |
| 45 | sirma2025relay | verified | https://api.crossref.org/works/10.1007/s11277-025-11753-z ; https://doi.org/10.1007/s11277-025-11753-z |  |
| 46 | sulaiman2023coordinated | verified | https://api.crossref.org/works/10.1109/TNSM.2022.3222589 ; https://doi.org/10.1109/TNSM.2022.3222589 |  |
| 47 | sunehag2018vdn | verified | https://api.crossref.org/works/10.65109/jsrc7365 ; https://doi.org/10.65109/jsrc7365 | DOI 10.65109/jsrc7365 is registered at Crossref for this paper and resolves to the ACM Digital Library record 10.5555/3237383.3238080; title, 11 authors, pages 2085-2087 and year match. Crossref labels the container with the generic AAMAS series name |
| 48 | tao2025dtac | verified | https://api.crossref.org/works/10.1109/TCOMM.2024.3476430 ; https://doi.org/10.1109/TCOMM.2024.3476430 |  |
| 49 | tashman2026adversarial | verified | https://api.crossref.org/works/10.1109/IWCMC69287.2026.11580033 ; https://doi.org/10.1109/IWCMC69287.2026.11580033 | venue wording differs from Crossref's proceedings title only (same conference and year) |
| 50 | tsampazi2023xapps | verified | https://api.crossref.org/works/10.1109/GLOBECOM54140.2023.10437367 ; https://doi.org/10.1109/GLOBECOM54140.2023.10437367 | venue wording differs from Crossref's proceedings title only (same conference and year) |
| 51 | tsampazi2025pandora | verified | https://api.crossref.org/works/10.1109/TMC.2024.3505781 ; https://doi.org/10.1109/TMC.2024.3505781 |  |
| 54 | wu2021gnnsurvey | verified | https://api.crossref.org/works/10.1109/TNNLS.2020.2978386 ; https://doi.org/10.1109/TNNLS.2020.2978386 |  |
| 55 | yasin2025dpfl | verified | https://api.crossref.org/works/10.1109/APWCS67981.2025.11151868 ; https://doi.org/10.1109/APWCS67981.2025.11151868 | venue wording differs from Crossref's proceedings title only (same conference and year) |
| 56 | yu2022mappo | verified | https://api.crossref.org/works/10.52202/068431-1787 ; https://doi.org/10.52202/068431-1787 | DOI 10.52202/068431-1787 is registered at Crossref for this paper (NeurIPS 35 via Curran/proceedings.com); title, 7 authors, pages 24611-24624 and year match. Crossref carries no separate volume field; 35 is in its container title |
| 57 | zangooei2024flexible | verified | https://api.crossref.org/works/10.1109/JSAC.2023.3336156 ; https://doi.org/10.1109/JSAC.2023.3336156 |  |
| 10 | zcdp | verified | https://api.crossref.org/works/10.1007/978-3-662-53641-4_24 ; https://doi.org/10.1007/978-3-662-53641-4_24 | Crossref container is the LNCS series; the bib names the conference (TCC), consistent |
| 58 | zhang2022federatedoran | verified | https://api.crossref.org/works/10.1109/GLOBECOM48099.2022.10001658 ; https://doi.org/10.1109/GLOBECOM48099.2022.10001658 | venue wording differs from Crossref's proceedings title only (same conference and year) |
| 11 | cheng2024oranslice | metadata corrected: two missing authors added (Arrobo, Maciocco) | https://api.crossref.org/works/10.1145/3636534.3701544 ; https://doi.org/10.1145/3636534.3701544 |  |
| 13 | doherty2025hype | verified | https://api.crossref.org/works/10.1364/JOCN.559990 ; https://doi.org/10.1364/JOCN.559990 |  |
| 20 | henderson2018matters | verified | https://api.crossref.org/works/10.1609/aaai.v32i1.11694 ; https://doi.org/10.1609/aaai.v32i1.11694 |  |
| 2 | agarwal2021precipice | verified | https://proceedings.neurips.cc/paper_files/paper/2021/hash/f514cec81cb148559cf475e7426eed5e-Abstract.html | no DOI in the bib; authors, volume 34, pages 29304-29320 match the NeurIPS proceedings record |
| 6 | asdikian2025verifying | verified | https://api.crossref.org/works/10.23919/CNSM67658.2025.11297450 ; https://doi.org/10.23919/CNSM67658.2025.11297450 | venue wording differs from Crossref's proceedings title only (same conference and year) |
| 7 | barlacchi2015milan | metadata corrected: issue 1 added | https://api.crossref.org/works/10.1038/sdata.2015.55 ; https://doi.org/10.1038/sdata.2015.55 |  |

## New entries (records fetched, not typed from memory)

| No. | Key | Source of the record | Notes |
|---|---|---|---|
| 52 | velickovic2018gat | http://export.arxiv.org/api/query?id_list=1710.10903 | title and six authors from the arXiv record, whose comment reads "To appear at ICLR 2018"; OpenReview and DBLP refused automated access, so no page numbers are given |
| 32 | mcmahan2017fedavg | https://proceedings.mlr.press/v54/mcmahan17a.html | PMLR record: authors, AISTATS 2017, volume 54, pages 1273-1282 |
| 34 | mnih2015dqn | https://api.crossref.org/works/10.1038/nature14236 | Crossref: 19 authors, Nature 518(7540), 529-533, 2015 |
| 43 | schulman2017ppo | http://export.arxiv.org/api/query?id_list=1707.06347 | arXiv record: title, five authors, 2017; a preprint, cited as such |
| 37 | oliehoek2016decpomdp | https://api.crossref.org/works/10.1007/978-3-319-28929-8 | Crossref: book, SpringerBriefs in Intelligent Systems, 2016 |
| 53 | wilcoxon1945 | https://api.crossref.org/works/10.2307/3001968 | Crossref: Biometrics Bulletin 1(6), 1945; Crossref gives the first page only (80), so only that is printed |
| 14 | efron1979bootstrap | https://api.crossref.org/works/10.1214/aos/1176344552 | Crossref: Annals of Statistics 7(1), 1-26, 1979 |
| 17 | gupta2017cooperative | https://api.crossref.org/works/10.1007/978-3-319-71682-4_5 | Crossref: book chapter, LNCS, pages 66-83, 2017 |
| 19 | vanhasselt2016popart | https://proceedings.neurips.cc/paper_files/paper/2016/hash/5227b6aaf294f5f027273aebf16015f2-Abstract.html | NeurIPS record: volume 29, 2016; its BibTeX lists Guez twice and no pages, so five authors and no pages are printed |

## Not added

- Holm (1979), "A simple sequentially rejective multiple test procedure", Scandinavian Journal of Statistics. Crossref holds no record for it (two queries returned other works), and JSTOR and DBLP refused automated access. Under the rule against typing metadata from memory it was not added. The Holm correction is therefore still uncited.

## Cannot verify

- cacs-paper4, the authors' own CACS 2026 paper. It has no DOI and no public record yet. Left untouched.
