"""M109 arms (docs/PAPER5_M109_preregistration.md). New code only: the framework and the earlier runners are not edited.

  ParityIndependentDqn   DQN-I with AXIOM's loss and normalisation: Huber loss and a LayerNorm after each hidden layer.
                         The base DQN already clips its gradient norm at 1.0, as AXIOM does.
  make_parity_single     the same change for DQN-SA (the single-agent DQNAdmissionPolicy).
  ParamSharedQ           one MLP Q-network shared by every gNB: input is the gNB's own feature row and the slice one-hot,
                         two hidden layers of 128 (the DQN baselines' width), one output head. No encoder, no neighbours,
                         no per-slice heads. Trained exactly as AXIOM is (per-request samples, Huber, clip 1.0, LR 1e-3).
  QmixShared             ParamSharedQ's shared agent network trained with a QMIX target: each gNB's utility is the sum of
                         its chosen Q-values, mixed by the framework's monotonic QMixer over the global state.
"""
import json

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from qoe_oran_framework.marl.ctde_policy import GatCtdeMarlPolicy
from qoe_oran_framework.marl.independent_dqn_ablation import IndependentPerGnbDqnPolicy
from qoe_oran_framework.policies.dqn_admission import DQNAdmissionPolicy

LR = 1e-3


class ParityQNetwork(nn.Module):
    """The baselines' Q-network (two hidden layers of 128) with a LayerNorm after each hidden layer."""

    def __init__(self, state_dim, action_dim, hidden_dim=128, n_branches=1):
        super().__init__()
        self.state_dim, self.action_dim, self.n_branches = state_dim, action_dim, max(1, int(n_branches))
        self.net = nn.Sequential(nn.Linear(state_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.ReLU(),
                                 nn.Linear(hidden_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.ReLU(),
                                 nn.Linear(hidden_dim, self.n_branches * action_dim))

    def forward(self, state):
        return self.net(state).view(-1, self.n_branches, self.action_dim)


def to_parity(dqn):
    """Give one DQNPolicy the parity network, a fresh optimiser at its own learning rate, and the Huber loss."""
    dqn.q_network = ParityQNetwork(dqn.state_dim, dqn.action_dim, 128, dqn.n_branches).to(dqn.device)
    dqn.target_network = ParityQNetwork(dqn.state_dim, dqn.action_dim, 128, dqn.n_branches).to(dqn.device)
    dqn.target_network.load_state_dict(dqn.q_network.state_dict())
    dqn.target_network.eval()
    dqn.optimizer = torch.optim.Adam(dqn.q_network.parameters(), lr=dqn.learning_rate)
    dqn.loss_fn = nn.SmoothL1Loss()
    return dqn


class ParityIndependentDqn(IndependentPerGnbDqnPolicy):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        for agent in self.agents:
            to_parity(agent)


def make_parity_single(state_dim, **overrides):
    return to_parity(DQNAdmissionPolicy(state_dim=state_dim, **overrides))


class OwnRow(nn.Module):
    """'Encoder' that returns each gNB's own feature row unchanged; the adjacency is unused."""

    def forward(self, node_features, adjacency):
        return node_features


class SharedMlpQ(nn.Module):
    def __init__(self, in_dim, context_dim, action_dim, hidden_dim=128):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(in_dim + context_dim, hidden_dim), nn.ReLU(),
                                 nn.Linear(hidden_dim, hidden_dim), nn.ReLU(), nn.Linear(hidden_dim, action_dim))

    def forward(self, embed, context):
        return self.net(torch.cat([embed, context], dim=-1))


class ParamSharedQ(GatCtdeMarlPolicy):
    def __init__(self, n_agents, node_feat_dim, context_dim, action_dim, adjacency, learning_rate=LR, **kw):
        super().__init__(n_agents, node_feat_dim, context_dim, action_dim, adjacency, learning_rate=learning_rate, **kw)
        for net in (self.online, self.target):
            net.encoder = OwnRow()
            net.q_head = SharedMlpQ(node_feat_dim, context_dim, action_dim).to(self.device)
        self.target.load_state_dict(self.online.state_dict())
        self.optimizer = torch.optim.Adam(self.online.parameters(), lr=learning_rate)

    def execution_parameters(self):
        return sum(p.numel() for p in self.online.q_head.parameters())


class QmixShared(ParamSharedQ):
    """Shared agent network with a QMIX target. The per-episode mean training loss is kept for the stability report."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._ep_losses, self.loss_curve = [], []

    def on_episode_end(self):
        super().on_episode_end()
        self.loss_curve.append(float(np.mean(self._ep_losses)) if self._ep_losses else None)
        self._ep_losses = []

    def save_checkpoint(self, path):
        super().save_checkpoint(path)
        json.dump({"episode_mean_loss": self.loss_curve}, open(path + ".loss.json", "w"))

    def _utilities(self, net, embeds_b, agent_idxs, ctx_t, acts_t=None):
        q = net.agent_q_values(embeds_b[agent_idxs], ctx_t)
        v = q.gather(1, acts_t.unsqueeze(1)).squeeze(1) if acts_t is not None else q.max(dim=-1)[0]
        idx = torch.as_tensor(agent_idxs, dtype=torch.long, device=self.device)
        return torch.zeros(self.n_agents, device=self.device).index_add(0, idx, v)

    def train_step(self, batch):
        B = len(batch["rewards"])
        nf = torch.tensor(np.stack(batch["node_features"]), dtype=torch.float32, device=self.device)
        next_nf = torch.tensor(np.stack(batch["next_node_features"]), dtype=torch.float32, device=self.device)
        rewards = torch.tensor(batch["rewards"], dtype=torch.float32, device=self.device)
        dones = torch.tensor(batch["dones"], dtype=torch.float32, device=self.device)
        embeds = self.online.embed(nf, self.adjacency)
        with torch.no_grad():
            next_embeds = self.target.embed(next_nf, self.adjacency)
        keep, u, un = [], [], []
        for b in range(B):
            agent_idxs = list(batch["agent_request_agent_idx"][b])
            if not agent_idxs:
                continue
            ctx_t = torch.tensor(np.asarray(batch["agent_request_context"][b]), dtype=torch.float32, device=self.device)
            acts_t = torch.tensor(batch["agent_request_action"][b], dtype=torch.long, device=self.device)
            u.append(self._utilities(self.online, embeds[b], agent_idxs, ctx_t, acts_t))
            with torch.no_grad():
                un.append(self._utilities(self.target, next_embeds[b], agent_idxs, ctx_t))
            keep.append(b)
        if not keep:
            return {"loss": 0.0, "grad_norm": 0.0, "epsilon": self.epsilon}
        k = torch.as_tensor(keep, dtype=torch.long, device=self.device)
        q_tot = self.online.mixer(torch.stack(u), nf[k].reshape(len(keep), -1))
        with torch.no_grad():
            target = rewards[k] + self.gamma * self.target.mixer(torch.stack(un), next_nf[k].reshape(len(keep), -1)) * (1 - dones[k])
        loss = F.smooth_l1_loss(q_tot, target)
        self.optimizer.zero_grad()
        loss.backward()
        grad_norm = nn.utils.clip_grad_norm_(self.online.parameters(), max_norm=1.0)
        self.optimizer.step()
        self.train_step_count += 1
        self._ep_losses.append(float(loss.item()))
        return {"loss": float(loss.item()), "grad_norm": float(grad_norm.item()), "epsilon": self.epsilon}
