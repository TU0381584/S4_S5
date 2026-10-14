"""Shared-budget closed-loop KPM source (M62 simulator fix).

ClosedLoopKpmSource serves every (gNB, slice) pair independently,
served = min(offered + backlog, ceiling), so slices never compete for the
gNB's PRB budget B. Combined with the live-anchored demand used by the M2
campaign (MEAN_OFFERED_RATIO: eMBB 15%, URLLC 5%, mMTC 5% of B), each gNB
carried only about a quarter of its budget, so accepting every request was
harmless and shedding mMTC could never protect URLLC or eMBB.

This subclass restores the stress design the config documents (slice caps
summing to 110% of B, demand at those caps, permanent scarcity) with two
changes and nothing else:

  1. Shared budget. Per gNB, each slice first asks for
     desired_k = min(offered_k + backlog_k, ceiling_k). When the sum of
     desired_k exceeds B, the slices share B in proportion to desired_k;
     otherwise each is served in full. Admitting more of one slice now
     takes PRBs away from the others.
  2. Real load. Mean offered demand per slice is LOAD_FACTOR times its
     nominal PRB share (urllc 30, embb 60, mmtc 10 for B = 100), so the
     reference gNB's aggregate demand exceeds B while URLLC and eMBB stay
     below their own caps (33, 66). Per-step demand noise is
     OFFERED_VOLATILITY x B. Per-gNB load multipliers are drawn from
     [0.9, 1.0] (first gNB pinned to 1.0), which keeps cross-gNB
     heterogeneity for the load-balance term.

Backlog carry-over, the loss/BLER model, UE churn, rejection relief, and
sample construction are identical to ClosedLoopKpmSource.poll().
"""
from typing import Dict, List

import numpy as np

from qoe_oran_framework.replay_kpm_source import ClosedLoopKpmSource
from qoe_oran_framework.types import UeSample

LOAD_MULTIPLIER_RANGE = (0.9, 1.0)


LOAD_FACTOR = 1.05        # mean offered demand = LOAD_FACTOR x each slice's nominal PRB share
OFFERED_VOLATILITY = 0.005  # per-step demand noise, as a fraction of B


def offered_ratio_from_nominal(cfg, load_factor: float = LOAD_FACTOR) -> Dict[str, float]:
    return {sid: load_factor * spec.nominal_ratio / 100.0 for sid, spec in cfg.slice_by_id.items()}


def shared_budget_load_multiplier(gnb_ids: List[str], seed: int) -> Dict[str, float]:
    rng = np.random.RandomState(seed + 7919)
    return {g: 1.0 if i == 0 else float(rng.uniform(*LOAD_MULTIPLIER_RANGE)) for i, g in enumerate(gnb_ids)}


class SharedBudgetKpmSource(ClosedLoopKpmSource):
    def poll(self) -> List[UeSample]:
        self._t += 1.0
        samples: List[UeSample] = []
        for gnb_id in self._gnb_ids:
            demand, desired = {}, {}
            for slice_id in self._slice_ids:
                key = (gnb_id, slice_id)
                mean = self._mean_offered_ratio[slice_id] * self._B * self._gnb_load_multiplier[gnb_id]
                drift = 0.1 * (mean - self._offered[key])
                noise = self._rng.normal(0.0, self._offered_volatility * self._B)
                self._offered[key] = max(0.0, self._offered[key] + drift + noise)
                relief = self._pending_relief.get(key, 0.0)
                if relief > 0.0:
                    self._backlog[key] = max(0.0, self._backlog[key] - relief)
                    self._pending_relief[key] = 0.0
                ceiling_prb = self._ceiling_ratio[key] / 100.0 * self._B
                demand[slice_id] = self._offered[key] + self._backlog[key]
                desired[slice_id] = min(demand[slice_id], ceiling_prb)

            total = sum(desired.values())
            share = 1.0 if total <= self._B or total <= 0 else self._B / total

            for slice_id in self._slice_ids:
                key = (gnb_id, slice_id)
                sd = self._sd_for_slice[slice_id]
                served = desired[slice_id] * share
                unmet = max(0.0, demand[slice_id] - served)
                self._backlog[key] = min(self._backlog_capacity, unmet)

                if self._rng.rand() < self._churn_prob and self._ues[key]:
                    idx = self._rng.randint(0, len(self._ues[key]))
                    self._ues[key][idx] = self._next_rnti()

                n_ues = max(1, len(self._ues[key]))
                per_ue_served = served / n_ues
                backlog_frac = self._backlog[key] / max(self._backlog_capacity, 1e-6)
                bler = max(0.0, min(1.0, 0.02 + 0.3 * backlog_frac))
                for rnti in self._ues[key]:
                    samples.append(UeSample(
                        rnti=rnti, timestamp_s=self._t, nssai_sst=1, nssai_sd=sd,
                        avg_prbs_dl=per_ue_served, gnb_id=gnb_id,
                        dl_total_bytes=per_ue_served * 1000.0, dl_errors=bler * 2.0, dl_bler=bler,
                        dl_mac_buffer_occupation=self._backlog[key] / n_ues,
                    ))
        return samples


def make_shared_budget_factory(cfg, sd_for_slice, backlog_capacity: float = 2000.0,
                               load_factor: float = None, volatility: float = None):
    ratios = offered_ratio_from_nominal(cfg, LOAD_FACTOR if load_factor is None else load_factor)
    vol = OFFERED_VOLATILITY if volatility is None else volatility

    def factory(seed):
        return SharedBudgetKpmSource(
            seed=seed, gnb_ids=cfg.gnb_ids, slice_ids=list(cfg.slice_by_id), B=cfg.B,
            mean_offered_ratio=ratios, backlog_capacity=backlog_capacity, sd_for_slice=sd_for_slice,
            offered_volatility=vol,
            gnb_load_multiplier=shared_budget_load_multiplier(cfg.gnb_ids, seed),
        )
    return factory
