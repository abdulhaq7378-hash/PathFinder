"""Extract real MH01 data for the video and slides: trajectories, naive drift, degraded signals, stats."""
import json, sys, os
import numpy as np
sys.path.insert(0, sys.argv[1] + "/tools")
from evaluate import load, associate, umeyama

D = sys.argv[2]; OUT = sys.argv[3]
te, pe, qe = load(D + "/est.txt"); tg, pg, qg = load(D + "/gt.tum")
ie, ig = associate(te, tg)
TE, PE, QE, PG = te[ie], pe[ie], qe[ie], pg[ig]
keep = np.r_[True, np.diff(TE) > 0]; TE, PE, QE, PG = TE[keep], PE[keep], QE[keep], PG[keep]
R, t = umeyama(PE, PG); PA = PE @ R.T + t
T0 = TE[0]; TT = TE - T0
err = np.linalg.norm(PA - PG, axis=1)
fail_t = TT[-1] - 5.0

def qrot(q):
    x, y, z, w = q.T
    return np.stack([np.stack([1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)], -1),
                     np.stack([2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)], -1),
                     np.stack([2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)], -1)], -2)

# naive strap-down on the degraded IMU, using PathFinder's own attitude, no corrections
imu = np.loadtxt(D + "/deg/imu0/data.csv", delimiter=",", comments="#")
ti = imu[:, 0] * 1e-9 - T0; acc = imu[:, 4:7]
tall, pall, qall = load(D + "/est.txt")
nf = np.searchsorted(ti, fail_t)
Rall = qrot(qall[:nf])
aw = np.einsum("nij,nj->ni", Rall, acc[:nf]) - [0, 0, np.median(np.linalg.norm(acc[:2000], axis=1))]
dt = np.r_[0, np.diff(ti[:nf])]
v = np.cumsum(aw * dt[:, None], 0); p = np.cumsum(v * dt[:, None], 0)
# align naive the same way as the estimate (same R,t) so the comparison is fair
pn = p @ R.T + t
gi = np.searchsorted(TT, ti[:nf]).clip(0, len(TT) - 1)
naive_err = np.linalg.norm(pn - PG[gi], axis=1)
naive_ate = float(np.sqrt(np.mean(naive_err ** 2)))

def ds(a, n):
    idx = np.linspace(0, len(a) - 1, n).astype(int); return a[idx]

N = 900
data = {
    "duration": float(TT[-1]), "fail_t": float(fail_t),
    "t": ds(TT, N).round(3).tolist(),
    "gt": ds(PG[:, :2], N).round(3).tolist(),
    "est": ds(PA[:, :2], N).round(3).tolist(),
    "err": ds(err, N).round(3).tolist(),
    "naive_t": ds(ti[:nf], 600).round(3).tolist(),
    "naive": ds(pn[:, :2], 600).round(2).tolist(),
    "naive_err": ds(naive_err, 600).round(2).tolist(),
    "stats": {"ate": float(np.sqrt(np.mean(err**2))), "naive_ate": naive_ate, "naive_final": float(naive_err[-1]),
              "naive_max": float(naive_err.max()), "baseline": float(np.sqrt(np.mean(np.sum((PG - PG.mean(0))**2, 1))))},
}
# degraded vs clean accel-z for the degradation scene (first 184 s)
clean = np.loadtxt(D + "/clean/imu0/data.csv", delimiter=",", comments="#")
tc = clean[:, 0] * 1e-9 - T0
data["sig_clean_t"] = ds(tc, 1500).round(3).tolist(); data["sig_clean"] = ds(np.linalg.norm(clean[:, 4:7], axis=1), 1500).round(3).tolist()
data["sig_deg_t"] = ds(ti, 1500).round(3).tolist(); data["sig_deg"] = ds(np.linalg.norm(imu[:, 4:7], axis=1), 1500).round(3).tolist()
gaps = np.flatnonzero(np.diff(ti) > 0.05)
data["gaps"] = [[float(ti[g]), float(ti[g + 1])] for g in gaps]
meta = json.load(open(D + "/meta.json"))
data["meta"] = {k: meta[k] for k in ["rows", "dropout_gaps", "dropout_time_s", "duplicate_stamps", "spikes_fixed", "static_intervals", "static_seconds", "ms_per_imu_second"]}
# gyro magnitude + rest windows (same idea as main.py's detector: low gyro and |a| variance over 0.5 s)
gyr = imu[:, 1:4]; gm = np.linalg.norm(gyr, axis=1); am = np.linalg.norm(acc, axis=1)
w = 100
def rstd(x):
    c = np.cumsum(np.r_[0, x]); c2 = np.cumsum(np.r_[0, x * x])
    n = len(x); s = np.zeros(n)
    lo = np.clip(np.arange(n) - w // 2, 0, n); hi = np.clip(np.arange(n) + w // 2, 0, n)
    m = (c[hi] - c[lo]) / (hi - lo); s = np.sqrt(np.maximum(0, (c2[hi] - c2[lo]) / (hi - lo) - m * m)); return s
still = (rstd(gyr[:, 0]) + rstd(gyr[:, 1]) + rstd(gyr[:, 2]) < 0.03 * 3) & (rstd(am) < 0.25) & (ti < fail_t)
segs = []; s0 = None
for i, f in enumerate(still):
    if f and s0 is None: s0 = i
    if (not f or i == len(still) - 1) and s0 is not None:
        if ti[i] - ti[s0] > 0.6: segs.append([float(ti[s0]), float(ti[i])])
        s0 = None
data["rest"] = segs
data["gyro_t"] = ds(ti, 1500).round(3).tolist(); data["gyro_mag"] = ds(gm, 1500).round(4).tolist()
# tilt: angle between estimated and true gravity direction in the body frame
Re = qrot(QE); Rg = qrot(qg[ig][keep])
ze = Re[:, 2, :]; zg = Rg[:, 2, :]
tilt = np.degrees(np.arccos(np.clip(np.sum(ze * zg, 1), -1, 1)))
data["tilt_t"] = ds(TT, 600).round(2).tolist(); data["tilt"] = ds(tilt, 600).round(3).tolist()
data["stats"]["tilt_median"] = float(np.median(tilt[TT < fail_t]))
# speed: naive vs PathFinder vs truth
def spd(P, T):
    v = np.gradient(P, T, axis=0); k = 41; ker = np.ones(k) / k
    return np.convolve(np.linalg.norm(v, axis=1), ker, mode="same")
data["spd_t"] = ds(TT, 600).round(2).tolist()
data["spd_gt"] = ds(spd(PG, TT), 600).round(3).tolist(); data["spd_est"] = ds(spd(PA, TT), 600).round(3).tolist()
data["spd_naive_t"] = ds(ti[:nf], 600).round(2).tolist(); data["spd_naive"] = ds(np.linalg.norm(v, axis=1), 600).round(2).tolist()
# blind window detail (last 12 s): gt and est xy
bw = TT > TT[-1] - 12
data["blind_t"] = ds(TT[bw], 240).round(3).tolist(); data["blind_gt"] = ds(PG[bw, :2], 240).round(3).tolist(); data["blind_est"] = ds(PA[bw, :2], 240).round(3).tolist()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(data, open(OUT, "w"))
print(json.dumps(data["stats"], indent=1), "gaps>50ms:", len(gaps))
