# M61 — layered testbed block diagram (TikZ), Fig. 6

## Status: complete. Compiles clean (pdflatex+bibtex+pdflatex x2, exit 0 every
stage, zero undefined refs/citations, zero overfull hboxes). **21pp, no page-
count delta** (the milestone flagged a possible +1pp; the figure fit in
existing slack on p.17).

## Step 1 — fact verification (docs/PAPER5_M61_rig_facts.csv)

Every label was checked against a live command, a source file, or the
manuscript's own already-published text, not copied from the milestone's
draft unverified. Two corrections to the milestone's own draft came out of
this:

1. **Policy tier**: the draft said "DQN/GAT-CTDE checkpoint." The manuscript's
   own Sec. 5.5 (line 634) states the live deployment used *only* a
   single-agent-DQN checkpoint (seed 900) — GAT-CTDE is never claimed live
   anywhere in this paper, only offline. Counted the real checkpoint's
   parameters directly (`torch.load` + `numel()` per tensor,
   `experiments/results/m8_live_anchor/.../seed900/.../checkpoint.pt`):
   **18,562**. The figure's Policy block reflects this, not the draft's
   generic DQN/GAT-CTDE pairing.
2. **UE count**: untracked `live_ue7_console*.log` files exist in the working
   tree, which could suggest a 7th concurrent UE. Their content shows the
   `oaitun_ue1` TUN interface (i.e. they're UE1 retry logs, not a genuine 7th
   UE), and no committed script or the manuscript itself ever states more
   than 6 (2/slice x 3 slices, matching Sec. 5.5's own "1 UE/slice" / "2
   UEs/slice" language). Excluded "7" from the figure as unverified.

Everything else (host specs, rfsim, band/PRB/numerology, E2 ports 6600/6655,
`slicing_control_m`, 17 Open5GS containers, slice SDs, traffic profiles)
checked out exactly against source: live `lscpu`/`free -h`, the ORANSlice E2
agent header (`e2_agent_app.h`), the E2 message handler
(`e2_message_handlers.c`), the actual gNB conf file's own numerology/PRB/band
fields, `docker_open5gs/5g-sa-deploy-slicing.yaml`'s 17-service list, and
`experiments/configs/traffic_profiles.yaml`.

One honesty note folded into the figure: the gNB config file is literally
named `...usrpx310.conf` (an RU-section template originally shaped for that
SDR), but `restart_ran_stack.sh` launches it with an explicit `--rfsim` flag
that overrides the RF layer entirely — no physical X310 is present or used.
The figure labels this block "rfsim -- software radio" / "no SDR/RF
hardware", not by its confusing filename.

## Step 2 — the figure

Added `\usepackage{tikz}` + `\usetikzlibrary{arrows.meta,fit}` to the
preamble (TikZ only, no external image asset, per the milestone's
constraint). Drew a layered block diagram inside `\resizebox{\textwidth}{!}`
placed right after Sec. 5.5's intro paragraph:

- A dashed outer box: "Single commodity host: Intel i5-1135G7 (4C/8T), 7.4
  GiB RAM -- CPU-only, no GPU, no SDR/RF hardware", enclosing every block
  below it (the whole stack runs as one machine's processes/containers).
- Top row (data plane): Core network (Open5GS, 17 containers, MongoDB) --
  N2/N3 --> RAN (OAI gNB/ORANSlice fork, rfsim, n78/106PRB/mu=1/TDD-SA) --
  Uu/rfsim --> UEs + traffic (up to 6 native nr-uesoftmodem, netns-isolated,
  eMBB/URLLC/mMTC iperf3 UDP).
- Bottom row (control plane), below RAN: Control loop (RIC-free UDP E2 agent
  ports 6600/6655, `slicing_control_m` per-slice PRB-ratio ceiling,
  `omega_log`) -- E2 (UDP) arrow up to RAN, state/action arrow across to
  Policy (single-agent DQN checkpoint, seed 900, 18,562 params, CPU
  inference).

Caption states plainly: "a single-host, software-radio (rfsim), RIC-free
O-RAN deployment, distinguished here from SDR/hardware-in-the-loop O-RAN
testbeds," and that every block/label is directly measured/configured, none
borrowed from any reference figure. `\label{fig:testbed}` (Fig. 6, lands on
p.17 in the current build).

Two rendering bugs were caught and fixed before finalizing (verified visually
via `pdftoppm` page-17 renders each iteration):
- Nodes given only `minimum width` auto-expand past that minimum to fit their
  content, so hand-computed anchor positions didn't hold; switched every
  block to an explicit `text width` so box geometry (and therefore anchor
  positions) became predictable, then recomputed all coordinates with real
  non-overlapping gaps.
- The `fit` library silently pads its bounding box by the node's own `inner
  sep` (10pt), so the outer host box actually rendered ~0.35cm larger than
  the corners passed to `fit={...}`, colliding with the title label placed
  just above those corners. Fixed by setting `inner sep=0pt` on the fit node.

## Verification

- Numeric-token diff on `main.tex` vs. the prior commit: `ONLY IN REMOVED`
  is empty (nothing existing was touched); every `ONLY IN ADDED` token
  traces to either a sourced fact in `docs/PAPER5_M61_rig_facts.csv` (17,
  106, 6600, 6655, 900, 18562, 7.4, 1135, 4, 8, 78, 3) or a TikZ layout
  coordinate (node positions/widths), not a new claim.
- `grep -n "fig:testbed" main.tex main.aux` confirms the label resolves to
  Fig. 6 on page 17, correctly cross-referenced.
- No component in the figure is absent from the Step 1 facts CSV.

## STOP

Reported per the milestone's own gate.
