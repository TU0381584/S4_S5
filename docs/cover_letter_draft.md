# Cover letter (draft)

Dear Editor,

We submit "AXIOM: A Shared Controller for Scalable Multi-Agent 5G Slice Admission" for consideration in Wireless Personal Communications. The paper presents AXIOM, a slice-admission controller with one encoder shared by every gNB and one Q-head per slice, so its size does not grow with the cluster. In a simulator with static load it keeps priority-slice compliance above 93 % at 7, 19 and 37 gNBs while every learned baseline stays below 84 %, including a policy trained only at 7 gNBs. The paper also contributes an evaluation protocol, with trivial-policy checks, per-slice metrics, tuned rule baselines, independent seed samples and pre-registered analyses, and its numbers are recomputed from stored logs by a separate verification script.

The findings have limits that the paper states. Both simulators are synthetic, with no radio channel or measured traffic, and the live single-gNB testbed never reached contention, so AXIOM was not deployed live. Graph attention gave no consistent benefit, and a tuned threshold rule earns more than every learned policy at its tuning conditions, so AXIOM's contribution is a design that scales and not a new learning principle. Our learned baselines are standard multi-agent methods and ablations, since we did not reimplement a published slice-admission controller.

Declarations on funding, competing interests, the use of an AI tool and data availability are in the manuscript. The authors need to add any statement on originality, concurrent submission and suggested reviewers themselves.

Sincerely,
The authors
