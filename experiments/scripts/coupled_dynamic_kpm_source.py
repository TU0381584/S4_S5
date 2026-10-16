"""Env B (M64): shared-budget simulator with time-varying load and inter-cell coupling.

Extends SharedBudgetKpmSource (Env A, M62/M63) with two mechanisms, and
nothing else.

1. Time-varying load. Each gNB's offered demand follows
       mean_k(t) = nominal_k * LOAD_BASE * m_i * (1 + LOAD_AMPLITUDE * sin(2 pi (s + phi_i) / LOAD_PERIOD))
   where s is the step within the episode, m_i the fixed per-gNB multiplier
   in [0.9, 1.0], and phi_i a phase drawn afresh for every gNB at every
   episode start. Demand therefore swings above and below the budget, so
   shedding mMTC is needed at some times and wasteful at others, and no
   static rule is optimal.

2. Inter-cell coupling. A gNB's usable budget shrinks with its neighbours'
   load on the previous step, a first-order inter-cell interference model,
       B_i(t) = B * (1 - COUPLING_ALPHA * mean_{j in N(i)} u_j(t-1)),
   where u_j is neighbour j's served PRBs over B, and N(i) comes from the
   same adjacency graph (fully-connected, ring, or hex) that the encoder
   reads. Admitting traffic at one gNB therefore costs its neighbours
   capacity, which they observe only indirectly, through their own queues.

Backlog is cleared, and phases are redrawn, at every episode start via
on_episode_reset(). install_backlog_reset() in m62_reviewer_experiments.py
calls it. The congestion feature stays served/B, as in the framework.
"""
from typing import Dict, List

import numpy as np

from qoe_oran_framework.types import UeSample
from shared_budget_kpm_source import (SharedBudgetKpmSource, offered_ratio_from_nominal,
                                      shared_budget_load_multiplier, OFFERED_VOLATILITY)

LOAD_BASE = 0.95        # mean demand = LOAD_BASE x nominal shares (M64 calibration, pre-registered)
LOAD_AMPLITUDE = 0.30   # demand swings between 0.7x and 1.3x of the mean
LOAD_PERIOD = 60.0      # steps per cycle (one evaluation episode)
COUPLING_ALPHA = 0.15   # capacity lost per unit of mean neighbour utilisation
TOPOLOGY = "fully_connected"   # set by the caller before the factory is built


def neighbour_lists(n: int, topology: str) -> List[List[int]]:
    from qoe_oran_framework.marl.topology import build_adjacency, hex_grid_edges, ring_edges
    if topology == "fully_connected":
        adj = build_adjacency(n)
    elif topology == "ring":
        adj = build_adjacency(n, ring_edges(n))
    elif topology == "hex":
        adj = build_adjacency(n, hex_grid_edges(n))
    else:
        raise ValueError(topology)
    adj = np.asarray(adj)
    return [[j for j in range(n) if j != i and adj[i, j] > 0] for i in range(n)]


class CoupledDynamicKpmSource(SharedBudgetKpmSource):
    def __init__(self, *args, neighbours=None, **kw):
        super().__init__(*args, **kw)
        self._neighbours = neighbours
        self._phase_rng = np.random.RandomState(int(self._rng.randint(0, 2**31 - 1)))
        self._util = {g: 0.0 for g in self._gnb_ids}
        self.on_episode_reset()

    def on_episode_reset(self):
        for key in self._backlog:
            self._backlog[key] = 0.0
        self._step = 0
        self._phase = {g: float(self._phase_rng.uniform(0.0, LOAD_PERIOD)) for g in self._gnb_ids}
        self._util = {g: 0.0 for g in self._gnb_ids}

    def poll(self) -> List[UeSample]:
        self._t += 1.0
        self._step += 1
        samples: List[UeSample] = []
        prev_util = dict(self._util)
        for gi, gnb_id in enumerate(self._gnb_ids):
            nb = self._neighbours[gi] if self._neighbours else []
            nb_util = float(np.mean([prev_util[self._gnb_ids[j]] for j in nb])) if nb else 0.0
            budget = self._B * (1.0 - COUPLING_ALPHA * nb_util)
            wave = 1.0 + LOAD_AMPLITUDE * np.sin(2.0 * np.pi * (self._step + self._phase[gnb_id]) / LOAD_PERIOD)
            demand, desired = {}, {}
            for slice_id in self._slice_ids:
                key = (gnb_id, slice_id)
                mean = self._mean_offered_ratio[slice_id] * self._B * self._gnb_load_multiplier[gnb_id] * wave
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
            share = 1.0 if total <= budget or total <= 0 else budget / total
            served_total = 0.0
            for slice_id in self._slice_ids:
                key = (gnb_id, slice_id)
                sd = self._sd_for_slice[slice_id]
                served = desired[slice_id] * share
                served_total += served
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
            self._util[gnb_id] = served_total / self._B
        return samples


def make_coupled_factory(cfg, sd_for_slice, backlog_capacity: float = 2000.0, topology: str = None):
    ratios = offered_ratio_from_nominal(cfg, LOAD_BASE)
    nbrs = neighbour_lists(len(cfg.gnb_ids), topology or TOPOLOGY)

    def factory(seed):
        return CoupledDynamicKpmSource(
            seed=seed, gnb_ids=cfg.gnb_ids, slice_ids=list(cfg.slice_by_id), B=cfg.B,
            mean_offered_ratio=ratios, backlog_capacity=backlog_capacity, sd_for_slice=sd_for_slice,
            offered_volatility=OFFERED_VOLATILITY,
            gnb_load_multiplier=shared_budget_load_multiplier(cfg.gnb_ids, seed),
            neighbours=nbrs,
        )
    return factory
