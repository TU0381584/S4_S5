# Archive manifest (prepared, not uploaded)

This lists what the public deposit holds and how it is built. Nothing has been uploaded. The DOI that the authors mint replaces the macro archivedoi in Papers_4-5/Paper_5/WPC/main.tex.

## Build

`bash experiments/scripts/make_archive.sh <staging_dir>` writes the archive to a staging directory and finishes with SHA256SUMS over every file. It records the source commit in SOURCE_COMMIT.txt. It needs about 34 GB of free space for tier 2, the size of experiments/results now that its logs are gzipped, since gzipped logs do not shrink further. The M108 and M109 logs were gzipped on 2026-11-16, which brought the results directory from 92 GB to about 33 GB and free space to 71 GB, so tier 2 can now be staged on this laptop. Only tier 1 and the console logs are staged in ~/archive_staging so far.

## Contents

| Part | What it holds | Built here |
|---|---|---|
| tier1_code_and_documents.tar.zst | every git-tracked file outside experiments/results, experiments/logs and Papers_4-5/Paper_4: framework/ (simulators and learners), experiments/configs, experiments/scripts (campaign runners, analysis, the three verification scripts m66_verify.py, m82_audit.py, m66_ci_recompute.py), experiments/plots (figure scripts), docs/ (pre-registrations, result notes, audits), CHANGELOG_WPC.md, and the manuscript sources, figures and Online Resource 2 | yes, 22 MB |
| tier2_results/_console_logs.tar.zst | experiments/logs, the console logs and job lists of every campaign | yes, 0.7 MB |
| tier2_results/<campaign>.tar.zst | one tarball per directory of experiments/results: stored evaluation logs (omega_log.jsonl), trained checkpoints (checkpoint.pt), and result JSON files | no, disk space |
| SHA256SUMS, SOURCE_COMMIT.txt | checksums of every tarball and the commit the archive was built from | at the final build |

Tier 1 is rebuilt at the final build, so its checksum will differ from any earlier staging. The stored evaluation logs are kept uncompressed on disk, as the verifier reads them in place. The tarballs do not change that.

## How to reproduce

Section S9 of Online Resource 1 lists the software versions and the order of the steps. Unpack tier 1 and tier 2 into one tree, then run the verification scripts from framework/ against the unpacked logs.

## Pre-registrations

Each file was committed before the runs it governs. The hash and timestamp are those of the commit that added the file, read from the repository history.

| File | Commit | Committed |
|---|---|---|
| docs/PAPER5_M100_preregistration.md | 58fb2f55 | 2026-11-10T09:45:09+08:00 |
| docs/PAPER5_M101_preregistration.md | 9baec7d8 | 2026-11-10T11:26:41+08:00 |
| docs/PAPER5_M102_preregistration.md | d98ac66c | 2026-11-11T02:41:34+08:00 |
| docs/PAPER5_M104_preregistration.md | 934e5d69 | 2026-11-11T05:01:13+08:00 |
| docs/PAPER5_M105_preregistration.md | 9530fabe | 2026-11-12T04:15:57+08:00 |
| docs/PAPER5_M106_preregistration.md | 1aeb6fd0 | 2026-11-12T10:20:23+08:00 |
| docs/PAPER5_M107_preregistration.md | 426a3281 | 2026-11-12T20:39:47+08:00 |
| docs/PAPER5_M108_preregistration.md | bb57af09 | 2026-11-14T06:14:36+08:00 |
| docs/PAPER5_M109_preregistration.md | 497c86d6 | 2026-11-16T00:05:29+08:00 |
| docs/PAPER5_M110_preregistration.md | d59ee624 | 2026-11-16T20:43:14+08:00 |
| docs/PAPER5_M111_preregistration.md | 8f45623e | 2026-11-17T01:08:41+08:00 |
| docs/PAPER5_M45_PF21_preregistration.md | 3239be0b | 2026-09-14T20:19:40+08:00 |
| docs/PAPER5_M63_preregistration.md | 85f2aa92 | 2026-10-15T14:29:06+08:00 |
| docs/PAPER5_M64_preregistration.md | cfc6c151 | 2026-10-16T13:55:08+08:00 |
| docs/PAPER5_M70_preregistration.md | 08b6f6d1 | 2026-10-20T19:34:42+08:00 |
| docs/PAPER5_M72_preregistration.md | a4b9856e | 2026-10-21T12:35:49+08:00 |
| docs/PAPER5_M73_preregistration.md | 85e67818 | 2026-10-22T04:15:44+08:00 |
| docs/PAPER5_M74_preregistration.md | ab763116 | 2026-10-22T14:22:38+08:00 |
| docs/PAPER5_M75_preregistration.md | d251490d | 2026-10-22T19:30:54+08:00 |
| docs/PAPER5_M76_preregistration.md | c1f8cd2f | 2026-10-23T14:17:11+08:00 |
| docs/PAPER5_M79_preregistration.md | 105e1a56 | 2026-10-27T01:50:40+08:00 |
| docs/PAPER5_M80_preregistration.md | 9c1886bb | 2026-10-27T03:13:19+08:00 |
| docs/PAPER5_M92_preregistration.md | 2b1dae55 | 2026-11-06T15:36:45+08:00 |
| docs/PAPER5_M94_preregistration.md | 43e6204e | 2026-11-06T18:41:50+08:00 |
| docs/PAPER5_M95_preregistration.md | cffadecf | 2026-11-06T21:47:32+08:00 |
| docs/PAPER5_M96_preregistration.md | 32de84d0 | 2026-11-07T06:18:40+08:00 |
| docs/PAPER5_M97_preregistration.md | 33522657 | 2026-11-07T23:07:03+08:00 |
| docs/PAPER5_M98_preregistration.md | d800a0a6 | 2026-11-09T04:24:54+08:00 |
| docs/PAPER5_M99_preregistration.md | 1584a86e | 2026-11-10T05:07:49+08:00 |

Campaigns with no file in this table have no separate pre-registration file. The main paper's Section 5 discloses the one registration whose plan was committed one minute after its launch.
