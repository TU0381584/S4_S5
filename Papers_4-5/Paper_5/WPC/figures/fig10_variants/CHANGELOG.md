# Changelog, Fig. 10 variants

All files are new in this folder; the manuscript .tex and the existing Fig. 10 source (experiments/plots/paper5_fig_capability.py) are not touched by this work.

## 2026-11-08

- style.py: created. Okabe-Ito colours (AXIOM #0072B2, learned #7F7F7F filled, rules #D55E00 hollow), Liberation Sans 8 pt, lines at least 0.5 pt, pdf.fonttype 42, no background fills, width 130.7 mm from the measured \textwidth (372.0 pt). Tick, half and cross status marks drawn as paths, since Liberation Sans lacks those glyphs. save() writes pdf, 300 dpi png, greyscale (CIE L*) and deuteranopia (colorspacious) previews and reports the smallest rendered font. palette_check() measures the palette's separation.
- data.py: created. Computes every plotted value from stored per-seed logs through m66_verify's reader, with 95% percentile bootstrap CIs (scipy.stats.bootstrap, 10,000 resamples). Writes data.json.
- data.json: created by data.py, then rebuilt once M97 (the tuned local rule in Env A at 37 gNBs) finished.
- fig10_A.py, fig10_A.pdf/.png/_grey.png/_cvd.png: created. Dot-plot strips and capability table. Revised once for layout (axis labels collided at 8 pt, table qualifiers overlapped) and once for consistency (the past-load qualifier now uses the mean over 110 to 120% load for every controller, where the first draft mixed AXIOM's single best load with the static rule's mean).
- fig10_B.py and outputs: created. Trade-off scatter with transfer arrows and per-seed ellipses. Revised once for layout (annotation clipped at the left edge, legend overlapping panel b).
- fig10_C.py and outputs: created. Normalised heatmap on cividis. Ordinal rows are signed numbers (reward per step against the tuned rule, Env B, 19 gNBs). Private training keeps words, uncoloured, because only AXIOM has a measured value; flagged here as asked.
- fig10_D.py, fig10_D and fig10_D_alt outputs: created. Radar, default and permuted axis order.
- caption_A.txt to caption_D.txt: created, no colour words.
- make_manifest.py, DATA_MANIFEST.md: created; the manifest is generated from data.json.
- make_contact_sheet.py, contact_sheet.tex, contact_sheet.pdf: created.
- REPORT.md: created.

## 2026-11-08, later

- Option A chosen by the author and implemented in the paper's pipeline as experiments/plots/paper5_fig_capability.py (output figures/fig_capability.*), redrawn at the submission's 119 mm width. Changes from the prototype for that width: row labels and qualifiers shortened ("no params", "pooled", "local", "best in A, B"), the compliance bracket raised, delay seeds read in sorted order so the bootstrap CI does not depend on directory order, the static rule's past-load mark from the same Holm test as the learners (3 tests at 19 gNBs), and a layout check that fails on any label overlap or clipping. The files in this folder are left as the prototypes they were.
