#!/usr/bin/env python3
"""M70 runner: m64_run.py plus the referee-response variants of docs/PAPER5_M70_preregistration.md.

The framework and m64_run.py are not modified. Variants are selected with
environment variables and run under the ordinary m64_run arm names:

  M70_VARIANT=sharedhead  with --arm axiom2
      AXIOM v2 with its three per-slice Q-heads replaced by one shared Q-head
      that takes the slice one-hot as an input. The shared head's hidden width
      (85) is chosen so that its parameter count matches the three per-slice
      heads it replaces (2,127 against 2,118).
  M70_VARIANT=vdn         with --arm axiom2
      AXIOM v2 trained on one joint target per step instead of one TD sample
      per pending request: the step's chosen Q-values are summed and regressed
      on r + gamma * sum of the next-step maxima, a value-decomposition (VDN)
      target. Everything else, including the Huber loss, is unchanged.
  M70_MAPPO=lr,epochs,minibatch  with --arm mappo
      MAPPO with the given actor learning rate, epochs and minibatch size.
      Use --train-episodes to change its training budget.
"""
import os
import sys

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m64_run  # noqa: E402
import m64_mappo  # noqa: E402
from m64_axiom2 import LR_V2, AxiomV2Policy  # noqa: E402

SHARED_HIDDEN = 85


class SharedQHead(nn.Module):
    """One MLP for every slice; the slice one-hot is concatenated to the input."""

    def __init__(self, embed_dim, context_dim, action_dim, hidden_dim=SHARED_HIDDEN):
        super().__init__()
        self.context_dim, self.action_dim = context_dim, action_dim
        self.net = nn.Sequential(nn.Linear(embed_dim + context_dim, hidden_dim), nn.ReLU(),
                                 nn.Linear(hidden_dim, action_dim))

    def forward(self, embed, context):
        return self.net(torch.cat([embed, context], dim=-1))


class SharedHeadAxiom(AxiomV2Policy):
    def __init__(self, n_agents, node_feat_dim, context_dim, action_dim, adjacency, learning_rate=LR_V2, **kw):
        super().__init__(n_agents, node_feat_dim, context_dim, action_dim, adjacency, learning_rate=learning_rate, **kw)
        emb = self.online.q_head.heads[0][0].in_features
        for net in (self.online, self.target):
            net.q_head = SharedQHead(emb, context_dim, action_dim).to(self.device)
        self.target.load_state_dict(self.online.state_dict())
        self.optimizer = torch.optim.Adam(self.online.parameters(), lr=learning_rate)


class VdnAxiom(AxiomV2Policy):
    def train_step(self, batch):
        B = len(batch["rewards"])
        nf = torch.tensor(np.stack(batch["node_features"]), dtype=torch.float32, device=self.device)
        next_nf = torch.tensor(np.stack(batch["next_node_features"]), dtype=torch.float32, device=self.device)
        rewards = torch.tensor(batch["rewards"], dtype=torch.float32, device=self.device)
        dones = torch.tensor(batch["dones"], dtype=torch.float32, device=self.device)
        embeds = self.online.embed(nf, self.adjacency)
        with torch.no_grad():
            next_embeds = self.target.embed(next_nf, self.adjacency)
        chosen_list, target_list = [], []
        for b in range(B):
            agent_idxs = batch["agent_request_agent_idx"][b]
            if len(agent_idxs) == 0:
                continue
            ctx_t = torch.tensor(np.asarray(batch["agent_request_context"][b]), dtype=torch.float32, device=self.device)
            acts_t = torch.tensor(batch["agent_request_action"][b], dtype=torch.long, device=self.device)
            q_vals = self.online.agent_q_values(embeds[b, agent_idxs], ctx_t)
            chosen_list.append(q_vals.gather(1, acts_t.unsqueeze(1)).squeeze(1).sum())
            with torch.no_grad():
                next_max = self.target.agent_q_values(next_embeds[b, agent_idxs], ctx_t).max(dim=-1)[0].sum()
                target_list.append(rewards[b] + self.gamma * next_max * (1 - dones[b]))
        if not chosen_list:
            return {"loss": 0.0, "grad_norm": 0.0, "epsilon": self.epsilon}
        loss = F.smooth_l1_loss(torch.stack(chosen_list), torch.stack(target_list))
        self.optimizer.zero_grad()
        loss.backward()
        grad_norm = nn.utils.clip_grad_norm_(self.online.parameters(), max_norm=1.0)
        self.optimizer.step()
        self.train_step_count += 1
        if self.train_step_count % 100 == 0:
            self.target.load_state_dict(self.online.state_dict())
        return {"loss": float(loss.item()), "grad_norm": float(grad_norm.item()), "epsilon": self.epsilon}


if __name__ == "__main__":
    v = os.environ.get("M70_VARIANT")
    if v == "sharedhead":
        m64_run.AxiomV2Policy = SharedHeadAxiom
    elif v == "vdn":
        m64_run.AxiomV2Policy = VdnAxiom
    elif v:
        raise SystemExit(f"unknown M70_VARIANT {v!r}")
    mp_cfg = os.environ.get("M70_MAPPO")
    if mp_cfg:
        lr, ep, mb = mp_cfg.split(",")
        m64_mappo.LR_ACTOR, m64_mappo.EPOCHS, m64_mappo.MINIBATCH = float(lr), int(ep), int(mb)
        print(f"[m70] MAPPO actor LR {lr}, epochs {ep}, minibatch {mb}", flush=True)
    if v:
        print(f"[m70] AXIOM variant {v}", flush=True)
    m64_run.main()
