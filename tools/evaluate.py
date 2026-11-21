#!/usr/bin/env python3
"""Score an estimated TUM trajectory against ground truth the way the organisers describe:
SE(3) Umeyama alignment (no scale) then ATE RMSE, plus proxies for the three tiers:
  waypoints : position error at 10 evenly spaced 'checkpoint' times before the IMU failure
  blind5    : position RMSE inside the final 5 s (IMU dead), using the global alignment
  rpe1s     : relative translation error over 1 s windows
usage: python evaluate.py <est.txt> <gt.tum> [--blind 5]
"""
import argparse
import json
import sys

import numpy as np


def load(p):
    a = np.loadtxt(p, comments="#")
    return a[:, 0], a[:, 1:4], a[:, 4:8]


def associate(te, tg, max_dt=0.006):
    j = np.searchsorted(tg, te)
    j = np.clip(j, 1, len(tg) - 1)
    left = tg[j - 1]
    right = tg[j]
    jj = np.where(np.abs(te - left) < np.abs(te - right), j - 1, j)
    ok = np.abs(tg[jj] - te) < max_dt
    return np.flatnonzero(ok), jj[ok]


def umeyama(src, dst):
    mu_s, mu_d = src.mean(0), dst.mean(0)
    S = (dst - mu_d).T @ (src - mu_s) / len(src)
    U, D, Vt = np.linalg.svd(S)
    W = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        W[2, 2] = -1
    R = U @ W @ Vt
    t = mu_d - R @ mu_s
    return R, t


def score(est_path, gt_path, blind=5.0):
    te, pe, qe = load(est_path)
    tg, pg, qg = load(gt_path)
    ie, ig = associate(te, tg)
    te, pe = te[ie], pe[ie]
    pg = pg[ig]
    # drop duplicate stamps for scoring
    keep = np.r_[True, np.diff(te) > 0]
    te, pe, pg = te[keep], pe[keep], pg[keep]
    R, t = umeyama(pe, pg)
    pa = pe @ R.T + t
    err = np.linalg.norm(pa - pg, axis=1)
    tb = te[-1] - blind
    pre = te < tb
    blind_err = err[~pre]
    cp_idx = np.linspace(0, np.flatnonzero(pre)[-1], 12).astype(int)[1:-1]
    # RPE over 1 s
    step = max(1, int(round(1.0 / np.median(np.diff(te)))))
    de = pa[step:] - pa[:-step]
    dg = pg[step:] - pg[:-step]
    rpe = np.linalg.norm(de - dg, axis=1)
    # zero-motion baseline (predict the mean position everywhere)
    base = np.sqrt(np.mean(np.sum((pg - pg.mean(0)) ** 2, 1)))
    return {
        "n": int(len(te)),
        "ate_rmse": float(np.sqrt(np.mean(err ** 2))),
        "ate_pre_fail": float(np.sqrt(np.mean(err[pre] ** 2))),
        "waypoint_mean": float(err[cp_idx].mean()),
        "blind5_rmse": float(np.sqrt(np.mean(blind_err ** 2))) if len(blind_err) else None,
        "blind5_final": float(blind_err[-1]) if len(blind_err) else None,
        "rpe1s_rmse": float(np.sqrt(np.mean(rpe ** 2))),
        "baseline_static_rmse": float(base),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("est")
    ap.add_argument("gt")
    ap.add_argument("--blind", type=float, default=5.0)
    a = ap.parse_args()
    print(json.dumps(score(a.est, a.gt, a.blind), indent=2))
