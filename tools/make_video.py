#!/usr/bin/env python3
"""Demo video: animated trajectory playback + slide walkthrough. usage: make_video.py <deck.pdf> <out.mp4>"""
import os, sys, subprocess, tempfile
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from evaluate import load, associate, umeyama
pdf, out = sys.argv[1], sys.argv[2]
W = tempfile.mkdtemp(dir='/tmp/claude-0')
# ---- trajectory animation
est = os.path.join(W, 'est.txt'); D = os.path.join(ROOT, 'data', 'MH01')
subprocess.run([sys.executable, os.path.join(ROOT, 'src/main.py'), os.path.join(D, 'deg'), '-o', est], check=True, capture_output=True)
te, pe, _ = load(est); tg, pg, _ = load(os.path.join(D, 'gt.tum'))
ie, ig = associate(te, tg); te, pe, pg = te[ie], pe[ie], pg[ig]
R, t = umeyama(pe, pg); pa = pe @ R.T + t; tt = te - te[0]; err = np.linalg.norm(pa - pg, axis=1)
fps, secs = 20, 40
idx = np.linspace(0, len(tt) - 1, fps * secs).astype(int)
fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor='#0a0e1a')
ax = fig.add_axes([0.05, 0.1, 0.5, 0.78], facecolor='#0a0e1a'); ax2 = fig.add_axes([0.62, 0.55, 0.35, 0.33], facecolor='#0a0e1a')
for a in (ax, ax2):
    a.tick_params(colors='#a9b4c8'); [s.set_color('#3a4560') for s in a.spines.values()]
ax.set_xlim(pg[:, 0].min() - 1, pg[:, 0].max() + 1); ax.set_ylim(pg[:, 1].min() - 1, pg[:, 1].max() + 1); ax.set_aspect('equal')
ax.set_xlabel('x [m]', color='#a9b4c8'); ax.set_ylabel('y [m]', color='#a9b4c8')
ax2.set_xlim(0, tt[-1]); ax2.set_ylim(0, err.max() * 1.1); ax2.set_xlabel('time [s]', color='#a9b4c8'); ax2.set_ylabel('error [m]', color='#a9b4c8')
ax2.axvspan(tt[-1] - 5, tt[-1], color='#f08c00', alpha=0.2)
g_line, = ax.plot([], [], color='#8892a6', lw=1.2, label='ground truth (hidden from estimator)')
e_line, = ax.plot([], [], color='#00b4d8', lw=1.2, label='PathFinder (degraded IMU only)')
dot, = ax.plot([], [], 'o', color='#00b4d8'); gdot, = ax.plot([], [], 'o', color='#ffffff', ms=4)
er_line, = ax2.plot([], [], color='#00b4d8')
ax.legend(loc='lower left', facecolor='#0a0e1a', edgecolor='#3a4560', labelcolor='#ffffff', fontsize=9)
title = fig.text(0.05, 0.93, '', color='white', fontsize=20, weight='bold')
info = fig.text(0.62, 0.42, '', color='#ffffff', fontsize=13, va='top', family='monospace')
fig.text(0.62, 0.12, 'EuRoC MH_01 + organiser degrade_imu.py\nnoise/bias ramp, 774 dropout gaps, 49 duplicates,\n340 spikes removed, IMU dead in the last 5 s',
         color='#a9b4c8', fontsize=11, va='bottom')
for f, k in enumerate(idx):
    g_line.set_data(pg[:k + 1, 0], pg[:k + 1, 1]); e_line.set_data(pa[:k + 1, 0], pa[:k + 1, 1])
    dot.set_data([pa[k, 0]], [pa[k, 1]]); gdot.set_data([pg[k, 0]], [pg[k, 1]]); er_line.set_data(tt[:k + 1], err[:k + 1])
    blind = tt[k] > tt[-1] - 5
    title.set_text('PathFinder playback' + ('   |   IMU FAILED: dead reckoning' if blind else ''))
    title.set_color('#f08c00' if blind else 'white')
    info.set_text(f't = {tt[k]:6.1f} s\nerror = {err[k]:5.2f} m\nATE so far = {np.sqrt((err[:k+1]**2).mean()):5.2f} m\n\npeak heap 2.45 MB (limit 8)\ncompute 1.8 ms / IMU-s (limit 20)')
    fig.savefig(os.path.join(W, f'a{f:04d}.png'), facecolor=fig.get_facecolor())
plt.close(fig)
anim = os.path.join(W, 'anim.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(fps), '-i', os.path.join(W, 'a%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-vf', 'scale=1280:720', anim], check=True)
# ---- slides: 13 s each, playback inserted after slide 5 (final output)
subprocess.run(['pdftoppm', '-png', '-r', '128', pdf, os.path.join(W, 's')], check=True)
slides = sorted(f for f in os.listdir(W) if f.startswith('s-'))
clips = []
for i, s in enumerate(slides):
    c = os.path.join(W, f'c{i:02d}.mp4')
    dur = 6 if i in (0, len(slides) - 1) else 13
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-t', str(dur), '-i', os.path.join(W, s), '-r', '20',
                    '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=0x0a0e1a',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', c], check=True)
    clips.append(c)
    if i == 4:
        clips.append(anim)
lst = os.path.join(W, 'list.txt')
open(lst, 'w').write(''.join(f"file '{c}'\n" for c in clips))
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', out], check=True)
print(out)
