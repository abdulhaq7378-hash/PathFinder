#!/usr/bin/env python3
"""Figures for README / slides. usage: plot.py <seq> <variant>"""
import os, sys, json, subprocess
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from evaluate import load, associate, umeyama
seq, var = (sys.argv[1:3] if len(sys.argv) > 2 else ('MH01', 'deg'))
D = os.path.join(ROOT, 'data', seq); R = os.path.join(ROOT, 'results'); os.makedirs(R, exist_ok=True)
est = '/tmp/claude-0/plot_est.txt'
subprocess.run([sys.executable, os.path.join(ROOT, 'src/main.py'), os.path.join(D, var), '-o', est], check=True, capture_output=True)
te, pe, qe = load(est); tg, pg, qg = load(os.path.join(D, 'gt.tum'))
ie, ig = associate(te, tg); te, pe, pg = te[ie], pe[ie], pg[ig]
Rm, t = umeyama(pe, pg); pa = pe @ Rm.T + t
err = np.linalg.norm(pa - pg, axis=1); tt = te - te[0]
plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
# 1 top view
fig, ax = plt.subplots(figsize=(6.4, 5.2))
ax.plot(pg[:, 0], pg[:, 1], color='#888', lw=1.2, label='ground truth')
ax.plot(pa[:, 0], pa[:, 1], color='#1f6fd1', lw=1.0, label='PathFinder (IMU only)')
nb = tt > tt[-1] - 5
ax.plot(pa[nb, 0], pa[nb, 1], color='#e8590c', lw=2.2, label='blind 5 s (IMU dead)')
ax.scatter(pg[0, 0], pg[0, 1], c='k', s=20, zorder=5); ax.set_aspect('equal'); ax.set_xlabel('x [m]'); ax.set_ylabel('y [m]')
ax.set_title(f'EuRoC {seq} degraded - top view (SE3 aligned)'); ax.legend(loc='best', frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(R, 'trajectory_topview.png'), dpi=160); plt.close(fig)
# 2 error over time
fig, ax = plt.subplots(figsize=(7.5, 3.0))
ax.plot(tt, err, color='#1f6fd1', lw=1); ax.axvspan(tt[-1] - 5, tt[-1], color='#e8590c', alpha=0.15, label='IMU failure')
ax.set_xlabel('time [s]'); ax.set_ylabel('position error [m]'); ax.set_title('Absolute position error after alignment'); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(R, 'error_over_time.png'), dpi=160); plt.close(fig)
# 3 degradation view
def imu(p):
    a = np.loadtxt(p, delimiter=',', comments='#'); return a[:, 0] * 1e-9, a[:, 1:4], a[:, 4:7]
tc, wc, ac = imu(os.path.join(D, 'clean/imu0/data.csv')); td, wd, ad = imu(os.path.join(D, var, 'imu0/data.csv'))
fig, axs = plt.subplots(2, 1, figsize=(7.5, 4.6), sharex=True)
axs[0].plot(tc - tc[0], wc[:, 2], color='#888', lw=0.6, label='clean'); axs[0].plot(td - tc[0], wd[:, 2], color='#c92a2a', lw=0.5, alpha=0.8, label='degraded')
axs[0].set_ylabel('gyro z [rad/s]'); axs[0].legend(frameon=False, loc='upper left', fontsize=9)
axs[1].plot(tc - tc[0], ac[:, 1], color='#888', lw=0.6); axs[1].plot(td - tc[0], ad[:, 1], color='#c92a2a', lw=0.5, alpha=0.8)
axs[1].set_ylabel('accel y [m/s$^2$]'); axs[1].set_xlabel('time [s]')
dtd = np.diff(td); gaps = td[1:][dtd > 0.009] - tc[0]
for g in gaps: axs[1].axvline(g, color='#f08c00', lw=0.3, alpha=0.4)
axs[0].set_title('Degradation grows with time; dropouts in orange; IMU dead in the last 5 s', fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(R, 'degradation.png'), dpi=160); plt.close(fig)
print('ATE', np.sqrt((err ** 2).mean()))
