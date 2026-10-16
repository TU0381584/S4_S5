"""M64 rule-based baselines for Env B.

ThresholdHeuristic always accepts URLLC, sheds eMBB only when the gNB's URLLC
queue reaches tau_e (if enabled), and sheds an mMTC request when any enabled
pressure signal at its gNB reaches its threshold.
  - tau_c: own congestion level (served PRBs over B)
  - tau_q: own priority-slice queue, the larger of URLLC and eMBB queue_len_norm
  - tau_n: mean congestion level of the gNB's neighbours in the adjacency graph
A threshold of None disables that signal. With only tau_c=0 it is the Env A
oracle (shed every mMTC request). The local family uses tau_c and tau_q.
The neighbour-aware family adds tau_n. Every rule plugs into mc_runner's
no-learning path via decide(), like PriorityHeuristic.
"""
import itertools
from typing import List, Optional


class ThresholdHeuristic:
    def __init__(self, gnb_ids: List[str], neighbours: List[List[int]],
                 tau_c: Optional[float] = None, tau_q: Optional[float] = None, tau_n: Optional[float] = None,
                 tau_e: Optional[float] = None):
        self.gnb_ids = list(gnb_ids)
        self.index = {g: i for i, g in enumerate(self.gnb_ids)}
        self.neighbours = neighbours
        self.tau_c, self.tau_q, self.tau_n = tau_c, tau_q, tau_n
        self.tau_e = tau_e  # shed eMBB when the gNB's URLLC queue reaches tau_e

    def _shed(self, gnb_id, cluster_state):
        per = cluster_state.per_gnb.get(gnb_id, {})
        any_agg = next(iter(per.values()), None)
        cong = any_agg.congestion_level if any_agg is not None else 0.0
        if self.tau_c is not None and cong >= self.tau_c:
            return True
        if self.tau_q is not None:
            q = max((per[s].queue_len_norm for s in ("urllc", "embb") if s in per), default=0.0)
            if q >= self.tau_q:
                return True
        if self.tau_n is not None:
            nb = self.neighbours[self.index[gnb_id]]
            vals = []
            for j in nb:
                p = cluster_state.per_gnb.get(self.gnb_ids[j], {})
                a = next(iter(p.values()), None)
                if a is not None:
                    vals.append(a.congestion_level)
            if vals and sum(vals) / len(vals) >= self.tau_n:
                return True
        return False

    def _shed_embb(self, gnb_id, cluster_state):
        if self.tau_e is None:
            return False
        per = cluster_state.per_gnb.get(gnb_id, {})
        return "urllc" in per and per["urllc"].queue_len_norm >= self.tau_e

    def decide(self, pending, cluster_state):
        cache = {}
        out = []
        for r in pending:
            if r.slice_id == "urllc":
                out.append(1)
                continue
            if r.slice_id == "embb":
                out.append(0 if self._shed_embb(r.gnb_id, cluster_state) else 1)
                continue
            if r.gnb_id not in cache:
                cache[r.gnb_id] = self._shed(r.gnb_id, cluster_state)
            out.append(0 if cache[r.gnb_id] else 1)
        return out


TAU_C = [None, 0.0, 0.8, 0.85, 0.9, 0.93, 0.96, 0.98, 1.01]
TAU_Q = [None, 0.05, 0.1, 0.2, 0.4]
TAU_N = [None, 0.8, 0.85, 0.9, 0.93, 0.96, 0.98]


def grid(family: str):
    """Rule grid per family. 'static' is the Env A oracle; 'accept_all' never sheds."""
    if family == "accept_all":
        return [dict(tau_c=None, tau_q=None, tau_n=None)]
    if family == "static":
        return [dict(tau_c=0.0, tau_q=None, tau_n=None)]
    if family == "local":
        return [dict(tau_c=c, tau_q=q, tau_n=None) for c, q in itertools.product(TAU_C, TAU_Q)
                if not (c is None and q is None)]
    if family == "neighbour":
        return [dict(tau_c=c, tau_q=q, tau_n=n) for c, q, n in itertools.product(TAU_C, TAU_Q, TAU_N[1:])]
    raise ValueError(family)
