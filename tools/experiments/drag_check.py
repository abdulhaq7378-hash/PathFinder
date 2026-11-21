"""Rotor-drag velocity prototype on EuRoC MH01 degraded.
For a multirotor the accelerometer's non-thrust axes read drag only: f_perp = -k * v_body_perp (no gravity term).
"""
import sys, json
import numpy as np
sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from evaluate import load, associate, umeyama, score

D = sys.argv[1]  # folder with deg/imu0/data.csv, est.txt, gt.tum
imu = np.loadtxt(D + "/deg/imu0/data.csv", delimiter=",", comments="#")
t = imu[:, 0] * 1e-9; w = imu[:, 1:4]; f = imu[:, 4:7]
te, pe, qe = load(D + "/est.txt"); assert len(te) == len(t)
tg, pg, qg = load(D + "/gt.tum")

def qrot(q):
    x, y, z, ww = q.T
    return np.stack([np.stack([1-2*(y*y+z*z), 2*(x*y-ww*z), 2*(x*z+ww*y)], -1),
                     np.stack([2*(x*y+ww*z), 1-2*(x*x+z*z), 2*(y*z-ww*x)], -1),
                     np.stack([2*(x*z-ww*y), 2*(y*z+ww*x), 1-2*(x*x+y*y)], -1)], -2)

# thrust axis = mean specific-force direction
ax = np.argmax(np.abs(np.median(f[:2000], 0))); perp = [i for i in range(3) if i != ax]
print("thrust axis", ax, "perp", perp)

# oracle check: GT body velocity vs f_perp
gi = np.searchsorted(tg, t).clip(1, len(tg) - 1)
vg_w = np.gradient(pg, tg, axis=0)[gi]
Rg = qrot(qg[gi]); vg_b = np.einsum("nji,nj->ni", Rg, vg_w)
alive = t < t[-1] - 5.0
def lp(x, tau, dt=0.005):
    a = dt / (tau + dt); y = np.empty_like(x); y[0] = x[0]
    for i in range(1, len(x)): y[i] = y[i - 1] + a * (x[i] - y[i - 1])
    return y
def zp(x, tau):  # zero-phase low-pass
    return lp(lp(x, tau)[::-1], tau)[::-1]
u = np.median(f[alive], 0); u /= np.linalg.norm(u)
e1 = np.cross(u, [0, 0, 1.0] if abs(u[2]) < 0.9 else [1.0, 0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(u, e1)
B = np.stack([e1, e2])  # 2x3, plane perpendicular to thrust
print("thrust dir", u.round(3))
fp = f @ B.T; vp = vg_b @ B.T
for j in range(2):
    fs = zp(fp[:, j], 0.2)
    m = alive & (np.linalg.norm(fp, axis=1) < 6)
    A = np.c_[vp[m, j], np.ones(m.sum())]
    sol, *_ = np.linalg.lstsq(A, fs[m], rcond=None)
    c = np.corrcoef(fs[m], vp[m, j])[0, 1]
    print(f"perp {j}: f = {sol[0]:.3f} * v + {sol[1]:.3f}   corr {c:.3f}")
# full 2x2 linear map (allows cross-coupling / misalignment)
fs2 = np.c_[zp(fp[:, 0], 0.2), zp(fp[:, 1], 0.2)]
m = alive
A = np.c_[vp[m], np.ones(m.sum())]
K, *_ = np.linalg.lstsq(A, fs2[m], rcond=None)
pred = A @ K
print("2x2 fit R2:", [1 - np.var(fs2[m][:, j] - pred[:, j]) / np.var(fs2[m][:, j]) for j in range(2)])
# oracle velocity from drag (inverse map) -> how good can position be?
Kv = np.linalg.inv(K[:2].T)  # v = Kv (f - b)
vd = (fs2 - K[2]) @ Kv.T
print("velocity from drag vs GT: rmse", np.sqrt(np.mean((vd[m] - vp[m]) ** 2, 0)).round(3), "GT rms", np.sqrt(np.mean(vp[m] ** 2, 0)).round(3))
json.dump({"ax": int(ax), "perp": perp}, open(D + "/drag_axes.json", "w"))
