"""Hash each single-agent DQN training batch and the post-update weights (wrapper only; framework untouched)."""
import hashlib, sys, os, runpy
sys.path.insert(0, "/home/kmanojp/oranslice_rig/experiments/scripts")
os.chdir("/home/kmanojp/oranslice_rig/framework"); sys.path.insert(0, os.getcwd())
from qoe_oran_framework.policies import dqn_admission as D
import numpy as np, torch
out = open(sys.argv[1], "w"); orig = D.DQNAdmissionPolicy.train_step; k = [0]
def h(a): return hashlib.md5(np.ascontiguousarray(a).tobytes()).hexdigest()[:10]
def wrapped(self, batch):
    pre = h(np.concatenate([p.detach().numpy().ravel() for p in self.q_network.parameters()]))
    r = orig(self, batch)
    post = h(np.concatenate([p.detach().numpy().ravel() for p in self.q_network.parameters()]))
    out.write(f"{k[0]} batch={h(batch['states'])}{h(batch['actions'])}{h(batch['rewards'])} pre={pre} post={post}\n"); k[0] += 1
    if k[0] > 3000: out.flush(); os._exit(0)
    return r
D.DQNAdmissionPolicy.train_step = wrapped
sys.argv = ["m64_run.py", "--arm", "single_agent_dqn", "--n", "3", "--out-dir", sys.argv[2], "--seeds", "900", "--train-episodes", "30"]
runpy.run_path("/home/kmanojp/oranslice_rig/experiments/scripts/m64_run.py", run_name="__main__")
