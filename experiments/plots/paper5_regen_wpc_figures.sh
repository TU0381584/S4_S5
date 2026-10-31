#!/usr/bin/env bash
# Regenerate every plotted figure of the WPC paper and its Online Resource 1 from the stored results.
# Main-paper figures are drawn at the journal's 119 mm maximum width; Online Resource 1 figures keep theirs.
set -euo pipefail
ROOT=/home/kmanojp/oranslice_rig
R=$ROOT/experiments/results
P=$ROOT/experiments/plots
F=$ROOT/Papers_4-5/Paper_5/WPC/figures
PY=$ROOT/venv/bin/python
export MATPLOTLIBRC=$P

# main paper
$PY $P/paper5_fig_scaling_trend.py --with-37 --out $F/fig6_scaling_trend
(cd $ROOT/framework && $PY $P/paper5_fig_gnb_map.py --n 37 --cell m73/A_n37_hex --out $F/fig13_gnb_map)
$PY $P/paper5_fig_envB.py --root $R/m64 --out $F/fig11_envB
(cd $P && $PY paper5_fig_pergnb_envb.py)
(cd $P && $PY paper5_fig_superiority.py)

# Online Resource 1
(cd $P && $PY paper5_fig_forest.py)
(cd $P && $PY paper5_fig_decision.py)
$PY $P/paper5_fig4_m3_privacy.py --m3-results $R/m65_m3/campaign_results.json --m3-campaign-dir $R/m65_m3 \
    --m2-results $R/m65_m2_view/campaign_results.json --m2-campaign-dir $R/m65_m2_view --out $F/fig4_m3_privacy
$PY $P/paper5_fig5_m4_disruption.py --level --no-titles --m4-results $R/m65_m4/campaign_results.json \
    --m4-campaign-dir $R/m65_m4 --m2-campaign-dir $R/m65_m2_view --m3-campaign-dir $R/m65_m3 --out $F/fig5_m4_disruption
(cd $ROOT/framework && $PY $P/paper5_fig_layouts.py --out $F/fig14_layouts)
