#!/usr/bin/env python3
"""Build test sets from a EuRoC sequence folder (needs imu0/data.csv + state_groundtruth_estimate0/data.csv).

Creates <out>/<name>/
    gt.tum                          ground truth, TUM format
    clean/imu0/data.csv             original IMU
    deg/imu0/data.csv               organiser degradation applied with correct column mapping
    deg_raw/imu0/data.csv           organiser script applied to the EuRoC file as-is (gyro/accel swapped by the script)
    deg_hard/imu0/data.csv          correct mapping, max-level 1.5
usage: python make_data.py <euroc_seq_dir> <name> <out_root>
"""
import os
import subprocess
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DEG = os.path.join(HERE, "degrade_imu.py")


def main():
    src, name, out = sys.argv[1], sys.argv[2], sys.argv[3]
    t0 = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0     # optional crop [t0, t1] seconds from start
    t1 = float(sys.argv[5]) if len(sys.argv) > 5 else 1e9
    root = os.path.join(out, name)
    os.makedirs(root, exist_ok=True)
    imu = pd.read_csv(os.path.join(src, "imu0", "data.csv"))
    cols = list(imu.columns)                      # ts, w xyz, a xyz
    gt = pd.read_csv(os.path.join(src, "state_groundtruth_estimate0", "data.csv"))
    ts0 = imu[cols[0]].iloc[0]
    rel = (imu[cols[0]] - ts0) * 1e-9
    imu = imu[(rel >= t0) & (rel <= t1)].reset_index(drop=True)
    relg = (gt[gt.columns[0]] - ts0) * 1e-9
    gt = gt[(relg >= t0) & (relg <= t1)].reset_index(drop=True)
    g = gt.to_numpy()
    with open(os.path.join(root, "gt.tum"), "w") as f:
        f.write("# timestamp tx ty tz qx qy qz qw\n")
        for r in g:
            f.write("%.9f %.6f %.6f %.6f %.7f %.7f %.7f %.7f\n" % (
                int(r[0]) * 1e-9, r[1], r[2], r[3], r[5], r[6], r[7], r[4]))

    def put(df, sub):
        d = os.path.join(root, sub, "imu0")
        os.makedirs(d, exist_ok=True)
        df.to_csv(os.path.join(d, "data.csv"), index=False)

    put(imu, "clean")
    tmp_in = os.path.join(root, "_acc_first.csv")
    tmp_out = os.path.join(root, "_acc_first_deg.csv")
    imu[[cols[0]] + cols[4:7] + cols[1:4]].to_csv(tmp_in, index=False)
    for sub, extra in (("deg", []), ("deg_hard", ["--max-level", "1.5"])):
        subprocess.run([sys.executable, DEG, tmp_in, tmp_out, "--meta",
                        os.path.join(root, sub + "_stats.json")] + extra, check=True)
        d = pd.read_csv(tmp_out)
        dc = list(d.columns)
        put(d[[dc[0]] + dc[4:7] + dc[1:4]], sub)
    raw_in = os.path.join(root, "clean", "imu0", "data.csv")
    raw_out = os.path.join(root, "_raw_deg.csv")
    subprocess.run([sys.executable, DEG, raw_in, raw_out, "--meta",
                    os.path.join(root, "deg_raw_stats.json")], check=True)
    put(pd.read_csv(raw_out), "deg_raw")
    for p in (tmp_in, tmp_out, raw_out):
        os.remove(p)
    print("built", root)


if __name__ == "__main__":
    main()
