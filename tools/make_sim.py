"""Local test data for PathFinder: a simulated drone flight with known ground truth.

Writes <out>/clean.csv (ts, accel, gyro: the organiser script's column order), <out>/gt.tum,
then runs the organiser degrade_imu.py and converts the result to EuRoC imu0/data.csv (ts, gyro, accel).
usage: python make_sim.py <repo_dir> <out_dir> [max_level]
"""
import os, subprocess, sys
import numpy as np

repo, out = sys.argv[1], sys.argv[2]
level = sys.argv[3] if len(sys.argv) > 3 else "1.0"
os.makedirs(os.path.join(out, "deg", "imu0"), exist_ok=True)
rng = np.random.default_rng(7)
G = 9.81
fs, T = 200.0, 150.0
t = np.arange(0, T, 1 / fs)

# flight envelope: rest 0-5 s, fly, hover-stop 70-73 s, fly, rest 140-150 s (organiser kills the last 5 s)
def smooth_gate(t, a, b, r=2.0):
    up = np.clip((t - a) / r, 0, 1); dn = np.clip((b - t) / r, 0, 1)
    s = np.minimum(up, dn)
    return s * s * (3 - 2 * s)

env = smooth_gate(t, 5, 70) + smooth_gate(t, 73, 140)
px = 3.0 * np.sin(2 * np.pi * t / 23.0) + 1.2 * np.sin(2 * np.pi * t / 7.1)
py = 2.5 * np.sin(2 * np.pi * t / 17.0 + 0.7) + 0.8 * np.cos(2 * np.pi * t / 5.3)
pz = 0.8 * np.sin(2 * np.pi * t / 11.0) + 0.3 * np.sin(2 * np.pi * t / 3.7)
# integrate a gated velocity so the vehicle really stops when env = 0
vel = np.stack([np.gradient(px, t), np.gradient(py, t), np.gradient(pz, t)], 1) * env[:, None]
pos = np.cumsum(vel, 0) / fs
acc = np.gradient(vel, t, axis=0)

# attitude: a multirotor tilts with horizontal acceleration, yaw slowly follows heading
roll = np.arctan2(-acc[:, 1], G) * 0.9
pitch = np.arctan2(acc[:, 0], G) * 0.9
yaw = np.cumsum(0.25 * np.sin(2 * np.pi * t / 31.0) * env) / fs

def rot(r, p, y):
    cr, sr, cp, sp, cy, sy = np.cos(r), np.sin(r), np.cos(p), np.sin(p), np.cos(y), np.sin(y)
    R = np.empty((len(r), 3, 3))
    R[:, 0, 0] = cy * cp; R[:, 0, 1] = cy * sp * sr - sy * cr; R[:, 0, 2] = cy * sp * cr + sy * sr
    R[:, 1, 0] = sy * cp; R[:, 1, 1] = sy * sp * sr + cy * cr; R[:, 1, 2] = sy * sp * cr - cy * sr
    R[:, 2, 0] = -sp;     R[:, 2, 1] = cp * sr;                R[:, 2, 2] = cp * cr
    return R

R = rot(roll, pitch, yaw)
dR = np.gradient(R, t, axis=0)
W = np.einsum("nji,njk->nik", R, dR)                 # R^T dR = [w]x in body frame
gyro = np.stack([W[:, 2, 1], W[:, 0, 2], W[:, 1, 0]], 1)
f_world = acc + np.array([0, 0, G])
accel = np.einsum("nji,nj->ni", R, f_world)          # R^T f

# realistic clean-sensor imperfections (EuRoC-like): white noise + constant gyro bias
gyro += np.array([-0.002, 0.024, 0.081]) + rng.normal(0, 0.0017, gyro.shape)
accel += rng.normal(0, 0.02, accel.shape)

ts = (1403636579758555392 + np.round(t * 1e9)).astype(np.int64)
clean = os.path.join(out, "clean.csv")
with open(clean, "w") as f:
    f.write("timestamp,ax,ay,az,gx,gy,gz\n")
    for i in range(len(t)):
        f.write("%d,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n" % (ts[i], *accel[i], *gyro[i]))

def quat(R):
    w = np.sqrt(np.maximum(0, 1 + R[:, 0, 0] + R[:, 1, 1] + R[:, 2, 2])) / 2
    x = (R[:, 2, 1] - R[:, 1, 2]) / (4 * w); y = (R[:, 0, 2] - R[:, 2, 0]) / (4 * w); z = (R[:, 1, 0] - R[:, 0, 1]) / (4 * w)
    return np.stack([x, y, z, w], 1)

q = quat(R)
with open(os.path.join(out, "gt.tum"), "w") as f:
    for i in range(len(t)):
        f.write("%.9f %.6f %.6f %.6f %.7f %.7f %.7f %.7f\n" % (ts[i] * 1e-9, *pos[i], *q[i]))

degc = os.path.join(out, "deg_acc_first.csv")
subprocess.run([sys.executable, os.path.join(repo, "tools", "degrade_imu.py"), clean, degc, "--max-level", level], check=True)
# to EuRoC order: ts, gyro, accel
lines = open(degc).read().splitlines()
with open(os.path.join(out, "deg", "imu0", "data.csv"), "w") as f:
    f.write("#timestamp [ns],w_RS_S_x [rad s^-1],w_RS_S_y [rad s^-1],w_RS_S_z [rad s^-1],a_RS_S_x [m s^-2],a_RS_S_y [m s^-2],a_RS_S_z [m s^-2]\n")
    for ln in lines[1:]:
        c = ln.split(",")
        f.write(",".join([c[0], c[4], c[5], c[6], c[1], c[2], c[3]]) + "\n")
print("rows clean", len(t), "rows degraded", len(lines) - 1, "path length %.1f m" % np.sum(np.linalg.norm(np.diff(pos, axis=0), axis=1)))
