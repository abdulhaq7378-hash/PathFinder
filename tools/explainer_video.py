#!/usr/bin/env python3
"""Narrated explainer video for PathFinder (animated scenes + offline TTS + subtitles).
usage: python tools/explainer_video.py <kokoro_dir> <out.mp4>
needs: numpy matplotlib kokoro-onnx soundfile ffmpeg, data/MH01 built by tools/make_data.py
"""
import os, sys, subprocess, tempfile, math, textwrap
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from evaluate import load, associate, umeyama

KDIR, OUT = sys.argv[1], sys.argv[2]
FPS = 24
W, H = 12.8, 7.2
BG = '#0a0e1a'; CARD = '#131b33'; CYAN = '#00b4d8'; TEAL = '#2ec4a0'; ORANGE = '#f08c00'; RED = '#e05a5a'
MUTED = '#a9b4c8'; WHITE = '#ffffff'; GREY = '#7d879b'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'text.color': WHITE, 'axes.edgecolor': '#3a4560',
                     'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.labelcolor': MUTED})
TMP = tempfile.mkdtemp(dir='/tmp/claude-0')

# ------------------------------------------------------------------ data
D = os.path.join(ROOT, 'data', 'MH01')
est = os.path.join(TMP, 'est.txt')
subprocess.run([sys.executable, os.path.join(ROOT, 'src/main.py'), os.path.join(D, 'deg'), '-o', est], check=True, capture_output=True)
te, pe, qe = load(est); tg, pg, qg = load(os.path.join(D, 'gt.tum'))
ie, ig = associate(te, tg)
TE, PE, QE, PG = te[ie], pe[ie], qe[ie], pg[ig]
Rm, tr = umeyama(PE, PG); PA = PE @ Rm.T + tr
TT = TE - TE[0]; ERR = np.linalg.norm(PA - PG, axis=1)


def imu(p):
    a = np.loadtxt(p, delimiter=',', comments='#'); return a[:, 0] * 1e-9, a[:, 1:4], a[:, 4:7]


tc, wc, ac = imu(os.path.join(D, 'clean/imu0/data.csv'))
td, wd, ad = imu(os.path.join(D, 'deg/imu0/data.csv'))
t0 = tc[0]; tc -= t0; td -= t0


def qrot(q):  # x y z w
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


# naive integration (our attitude, no corrections) for the drift scene
_, pe_all, qe_all = load(est)
te_all = load(est)[0]
nf = int(np.searchsorted(te_all - te_all[0], (te_all[-1] - te_all[0]) - 5.0))
Rall = np.array([qrot(q) for q in qe_all[:nf:5]])
ad5 = ad[:nf:5]; td5 = td[:nf:5]
aw = np.einsum('nij,nj->ni', Rall, ad5) - [0, 0, 9.78]
dt5 = np.r_[0, np.diff(td5)]
v_naive = np.cumsum(aw * dt5[:, None], 0)
p_naive = np.cumsum(v_naive * dt5[:, None], 0)
naive_err = np.linalg.norm(p_naive - p_naive[0], axis=1)

# ------------------------------------------------------------------ scenes
# (title, narration-for-captions, narration-for-tts)
SCENES = [
 ("intro", "This is PathFinder, Team Team's entry for Track 3 of the Samsung PRISM XR Hackathon, from Manipal Institute of Technology.",
  "This is PathFinder. Team Team's entry for Track 3 of the Samsung Prism X R Hackathon, from Manipal Institute of Technology."),
 ("mission", "An aircraft flies through checkpoints with no GPS. It is being jammed. All it has is an IMU, a gyroscope and an accelerometer, and that sensor gets worse every second until it dies.",
  "An aircraft flies through checkpoints with no G P S. It is being jammed. All it has is an I M U, a gyroscope and an accelerometer, and that sensor gets worse every second, until it dies."),
 ("degradation", "The organisers degrade the data on purpose: growing noise and bias drift, spikes, missing and duplicated rows, and five dead seconds at the end. We must output a full 6-DoF pose for every row.",
  "The organisers degrade the data on purpose. Growing noise and bias drift, spikes, missing and duplicated rows, and five dead seconds at the end. We must output a full six D O F pose, for every row."),
 ("drift", "Why is it hard? Position means integrating acceleration twice. Naive integration on this data drifts by hundreds of metres within three minutes.",
  "Why is it hard? Position means integrating acceleration twice. Naive integration on this data drifts by hundreds of metres, within three minutes."),
 ("budget", "And it must fit in 8 MB of memory. Surprise: importing numpy alone uses the whole 8 MB. So PathFinder is pure Python standard library, and peaks at 2.45 MB.",
  "And it must fit in eight megabytes of memory. Surprise: importing numpy alone uses the whole eight megabytes. So PathFinder is pure Python standard library, and peaks at two point four five megabytes."),
 ("pipeline", "PathFinder is an eight-stage offline pipeline. Let's walk through it.",
  "PathFinder is an eight stage offline pipeline. Let's walk through it."),
 ("static", "We parse the stream, use the real time step across gaps, and remove spikes. A variance detector finds every moment the vehicle is at rest. At rest the gyro should read zero, so whatever it reads is bias.",
  "We parse the stream, use the real time step across gaps, and remove spikes. A variance detector finds every moment the vehicle is at rest. At rest, the gyro should read zero, so whatever it reads, is bias."),
 ("attitude", "Bias from every rest is interpolated over time to follow drift. A Mahony filter fuses gyro and gravity to track orientation, forward in time, and backward for data before the first rest.",
  "Bias from every rest is interpolated over time, to follow drift. A Mahony filter fuses gyro and gravity to track orientation. Forward in time, and backward for data before the first rest."),
 ("velocity", "We remove gravity and integrate. At rest velocity must be zero, so we reset it and remove linear drift between rests. Offline zero-phase smoothing keeps what remains bounded.",
  "We remove gravity and integrate. At rest, velocity must be zero, so we reset it, and remove linear drift between rests. Offline zero phase smoothing keeps what remains bounded."),
 ("blind", "When the IMU dies, we dead-reckon from the last trusted velocity and turn rate, letting both decay, and still emit a pose for every timestamp.",
  "When the I M U dies, we dead reckon from the last trusted velocity and turn rate, letting both decay, and still emit a pose for every timestamp."),
 ("result", "Here is EuRoC Machine Hall 1 with the official degradation. Grey is the hidden ground truth, blue is PathFinder. Error stays bounded around four metres, 3.6 m on average over twelve degraded runs, close to what an IMU alone can observe.",
  "Here is the Euroc machine hall sequence, with the official degradation. Grey is the hidden ground truth. Blue is PathFinder. Error stays bounded, around four metres. Three point six on average, over twelve degraded runs. That's close to what an I M U alone can observe."),
 ("perf", "It is light and fast: 2.45 MB peak memory, 1.8 ms per second of data, one thread, and exactly one pose per input row.",
  "It is light and fast. Two point four five megabytes peak memory. One point eight milliseconds per second of data. One thread. And exactly one pose per input row."),
 ("run", "Running it is one command, with nothing to install. It writes the trajectory and a metadata report.",
  "Running it is one command, with nothing to install. It writes the trajectory, and a metadata report."),
 ("outro", "We also tested a rotor-drag physics model and documented why we left it out. That's PathFinder. Thanks for watching!",
  "We also tested a rotor drag physics model, and documented why we left it out. That's PathFinder. Thanks for watching!"),
]

# ------------------------------------------------------------------ audio
from kokoro_onnx import Kokoro
import soundfile as sf
kok = Kokoro(os.path.join(KDIR, 'kokoro-v1.0.onnx'), os.path.join(KDIR, 'voices-v1.0.bin'))
VOICE = os.environ.get('VOICE', 'am_michael')
SPEED = float(os.environ.get('SPEED', '1.08'))
durs, wavs = [], []
for i, (name, cap, say) in enumerate(SCENES):
    s, sr = kok.create(say, voice=VOICE, speed=SPEED, lang='en-us')
    pad = np.zeros(int(sr * 0.45), dtype=np.float32)
    s = np.concatenate([pad, s.astype(np.float32), pad])
    p = os.path.join(TMP, f'v{i:02d}.wav'); sf.write(p, s, sr)
    wavs.append(p); durs.append(len(s) / sr)
total = sum(durs)
print('scene durations', [round(d, 1) for d in durs], 'total %.1f s' % total)

# ------------------------------------------------------------------ drawing helpers
fig = plt.figure(figsize=(W, H), dpi=100, facecolor=BG)


def base(title):
    fig.clf(); fig.set_facecolor(BG)
    if title:
        fig.text(0.04, 0.93, title.upper(), color=CYAN, fontsize=13, weight='bold', alpha=0.9)


def caption(text, u):
    """subtitle: show the sentence active at progress u (by character share)."""
    sents = [s.strip() for s in text.replace('! ', '!|').replace('. ', '.|').replace('? ', '?|').replace(': ', ':|').split('|') if s.strip()]
    tot = sum(len(s) for s in sents); acc = 0; cur = sents[-1]
    for s in sents:
        acc += len(s)
        if u * 1.03 <= acc / tot:
            cur = s; break
    wrapped = textwrap.fill(cur, 80)
    fig.text(0.5, 0.045, wrapped, ha='center', va='bottom', fontsize=15, color=WHITE,
             bbox=dict(boxstyle='round,pad=0.45', fc='#000000', ec='none', alpha=0.62))


def ease(x):
    x = min(max(x, 0.0), 1.0); return 0.5 - 0.5 * math.cos(math.pi * x)


def box(ax, x, y, w, h, fc=CARD, ec=None, lw=1.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.008,rounding_size=0.015', fc=fc, ec=ec or fc, lw=lw,
                                transform=ax.transAxes))


def canvas_ax():
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off'); return ax


def dark(ax):
    ax.set_facecolor(BG)
    for s in ax.spines.values(): s.set_color('#3a4560')


# ------------------------------------------------------------------ scenes
def sc_intro(u, t):
    base(None); ax = canvas_ax()
    a = ease(u * 3)
    ax.text(0.5, 0.62, 'PathFinder', ha='center', fontsize=64, weight='bold', color=WHITE, alpha=a)
    ax.text(0.5, 0.53, 'Trajectory estimation from a jammed, dying IMU', ha='center', fontsize=20, color=CYAN, alpha=ease(u * 3 - 0.4))
    ax.text(0.5, 0.42, 'Samsung PRISM XR Hackathon 2026  |  Track 3: Path Finder', ha='center', fontsize=15, color=MUTED, alpha=ease(u * 3 - 0.8))
    ax.text(0.5, 0.36, 'Team: Team  |  Manipal Institute of Technology  |  Nadir Hussain, Abdul Haq', ha='center', fontsize=14,
            color=MUTED, alpha=ease(u * 3 - 1.1))
    # flying dot along the GT path
    k = int(ease(u) * (len(PG) - 1))
    m = fig.add_axes([0.38, 0.12, 0.24, 0.18]); m.axis('off'); m.set_aspect('equal')
    m.plot(PG[:k + 1, 0], PG[:k + 1, 1], color=CYAN, lw=1.2, alpha=0.8); m.plot(PG[k, 0], PG[k, 1], 'o', color=WHITE, ms=5)
    m.set_xlim(PG[:, 0].min() - .5, PG[:, 0].max() + .5); m.set_ylim(PG[:, 1].min() - .5, PG[:, 1].max() + .5)


def sc_mission(u, t):
    base('The mission'); ax = fig.add_axes([0.06, 0.15, 0.55, 0.72]); dark(ax); ax.set_aspect('equal'); ax.axis('off')
    k = int(min(1, u * 1.08) * (len(PG) - 1))
    ax.plot(PG[:, 0], PG[:, 1], color='#222b44', lw=1)
    ax.plot(PG[:k + 1, 0], PG[:k + 1, 1], color=CYAN, lw=1.6)
    cps = np.linspace(0, len(PG) - 1, 8).astype(int)[1:-1]
    for c in cps:
        ax.plot(PG[c, 0], PG[c, 1], 's', color=TEAL if c <= k else '#2a3550', ms=9)
    dead = u > 0.85
    ax.plot(PG[k, 0], PG[k, 1], 'o', color=RED if dead else WHITE, ms=9)
    for r in range(3):  # jamming rings
        rr = ((t * 0.9 + r * 0.33) % 1.0)
        ax.add_patch(Circle((PG[k, 0], PG[k, 1]), 0.3 + rr * 2.5 * (0.3 + u), fill=False, ec=RED, alpha=(1 - rr) * min(1, u * 2), lw=1.5))
    ax.set_xlim(PG[:, 0].min() - 2, PG[:, 0].max() + 2); ax.set_ylim(PG[:, 1].min() - 2, PG[:, 1].max() + 2)
    c = canvas_ax()
    items = [('No GPS', 0.0), ('No camera', 0.12), ('Jamming grows', 0.3), ('IMU only:\ngyro + accelerometer', 0.45), ('IMU dies at the end', 0.8)]
    for i, (s, start) in enumerate(items):
        a = ease((u - start) * 5)
        col = RED if i in (2, 4) else WHITE
        c.text(0.66, 0.78 - i * 0.12, s, fontsize=20, color=col, alpha=a, weight='bold' if i == 3 else 'normal', va='top')
    if dead:
        c.text(0.33, 0.85, 'IMU FAILED', color=RED, fontsize=26, weight='bold', ha='center', alpha=ease((u - 0.85) * 8))


def sc_degradation(u, t):
    base('What the organisers do to the data')
    span = 30.0; tend = 20 + u * (tc[-1] - 25)
    for row, (lab, cc, dd, j) in enumerate([('gyro z [rad/s]', wc, wd, 2), ('accel y [m/s²]', ac, ad, 1)]):
        ax = fig.add_axes([0.07, 0.58 - row * 0.38, 0.6, 0.3]); dark(ax)
        m = (tc > tend - span) & (tc <= tend); md = (td > tend - span) & (td <= tend)
        ax.plot(tc[m], cc[m, j], color=GREY, lw=0.7, label='clean')
        ax.plot(td[md], dd[md, j], color=RED, lw=0.6, alpha=0.85, label='degraded')
        gaps = td[1:][np.diff(td) > 0.009]; gaps = gaps[(gaps > tend - span) & (gaps <= tend)]
        for g in gaps[::2]: ax.axvline(g, color=ORANGE, lw=0.4, alpha=0.35)
        if tend > tc[-1] - 5: ax.axvspan(tc[-1] - 5, tend, color=RED, alpha=0.15)
        ax.set_xlim(tend - span, tend); ax.set_ylabel(lab, fontsize=11)
        lim = 1.6 if j == 2 and row == 0 else 9; ax.set_ylim(-lim, lim) if row == 0 else ax.set_ylim(-8, 8)
        if row == 0: ax.legend(loc='upper left', fontsize=10, facecolor=BG, edgecolor='#3a4560', labelcolor=WHITE)
        if row == 1: ax.set_xlabel('time [s]')
    c = canvas_ax()
    tags = [('noise grows', RED, 0.05), ('bias drifts', RED, 0.2), ('spikes', ORANGE, 0.35), ('rows go missing', ORANGE, 0.5),
            ('rows duplicated', ORANGE, 0.6), ('last 5 s: all zeros', RED, 0.72), ('output: 1 pose per row', TEAL, 0.85)]
    for i, (s, col, st) in enumerate(tags):
        c.text(0.72, 0.82 - i * 0.085, '• ' + s, color=col, fontsize=17, alpha=ease((u - st) * 6))


def sc_drift(u, t):
    base('Why it is hard')
    ax = fig.add_axes([0.08, 0.18, 0.55, 0.66]); dark(ax)
    k = int(ease(u * 1.1) * (len(td5) - 1))
    ax.plot(td5[:k + 1], naive_err[:k + 1], color=RED, lw=2, label='naive double integration')
    ax.plot(TT[TT <= td5[k]], ERR[TT <= td5[k]], color=CYAN, lw=2, label='PathFinder')
    ax.set_xlim(0, td5[-1]); ax.set_ylim(0, naive_err.max() * 1.05)
    ax.set_xlabel('time [s]'); ax.set_ylabel('position error [m]'); ax.legend(loc='upper left', facecolor=BG, edgecolor='#3a4560', labelcolor=WHITE, fontsize=11)
    c = canvas_ax()
    c.text(0.68, 0.72, 'p = ∬ a dt²', fontsize=30, color=WHITE, alpha=ease(u * 4))
    c.text(0.68, 0.6, 'bias error grows with t²', fontsize=18, color=MUTED, alpha=ease(u * 4 - 0.5))
    c.text(0.68, 0.45, f'{naive_err[k]:6.0f} m', fontsize=44, color=RED, weight='bold', family='DejaVu Sans Mono')
    c.text(0.68, 0.39, 'naive error so far', fontsize=14, color=MUTED)


def sc_budget(u, t):
    base('The budget')
    c = canvas_ax()
    c.text(0.08, 0.78, 'Memory limit: 8 MB', fontsize=24, weight='bold')
    bars = [('import numpy', 8.05, RED, 0.1), ('PathFinder (whole process)', 2.45, TEAL, 0.5)]
    for i, (lab, val, col, st) in enumerate(bars):
        y = 0.6 - i * 0.2; f = ease((u - st) * 3)
        c.add_patch(Rectangle((0.08, y), 0.6, 0.08, fc=CARD, ec='#3a4560'))
        c.add_patch(Rectangle((0.08, y), 0.6 * min(1.0, val / 8.0) * f, 0.08, fc=col))
        c.text(0.08, y + 0.1, lab, fontsize=17, color=WHITE, alpha=ease((u - st) * 6))
        c.text(0.7, y + 0.025, f'{val * f:4.2f} MB', fontsize=20, color=col, weight='bold')
    c.plot([0.68, 0.68], [0.2, 0.72], color=RED, ls='--', lw=1.5); c.text(0.665, 0.73, '8 MB', color=RED, fontsize=12)
    c.text(0.08, 0.17, 'Pure Python standard library: float32 arrays, buffers reused in place, lazy imports',
           fontsize=16, color=MUTED, alpha=ease((u - 0.65) * 4))


STAGES = ['Parse', 'Sanitise', 'Static detector', 'Bias + gravity', 'Attitude', 'Velocity', 'Position', 'Blind 5 s']


def draw_pipeline(c, active=-1, appear=1.0, y0=0.55):
    for i, s in enumerate(STAGES):
        r, col = divmod(i, 4)
        x = 0.06 + col * 0.23; y = y0 - r * 0.25
        a = ease(appear * 8 - i)
        on = i == active
        c.add_patch(FancyBboxPatch((x, y), 0.19, 0.15, boxstyle='round,pad=0.005,rounding_size=0.02',
                                   fc=CYAN if on else CARD, ec=CYAN, lw=2 if on else 1, alpha=a))
        c.text(x + 0.095, y + 0.075, f'{i + 1}\n{s}', ha='center', va='center', fontsize=15, color=BG if on else WHITE,
               weight='bold', alpha=a)


def sc_pipeline(u, t):
    base('Architecture'); c = canvas_ax(); draw_pipeline(c, appear=u * 1.2)


def sc_static(u, t):
    base('Stages 1-4: clean, find rest, measure bias')
    c = canvas_ax(); draw_pipeline_mini(c, [0, 1, 2, 3])
    ax = fig.add_axes([0.07, 0.2, 0.86, 0.5]); dark(ax)
    m = (td < 60)
    ax.plot(td[m], wd[m, 2], color=GREY, lw=0.7)
    st = [(21.1, 31.6), (33.6, 38.8)]
    for i, (a, b) in enumerate(st):
        al = ease((u - 0.35 - i * 0.12) * 6)
        ax.axvspan(a, b, color=TEAL, alpha=0.25 * al)
        if al > 0: ax.text((a + b) / 2, 0.45, 'at rest', ha='center', color=TEAL, fontsize=13, alpha=al)
    ax.axhline(0.0799, color=ORANGE, lw=1.5, ls='--', alpha=ease((u - 0.7) * 5))
    ax.text(41, 0.12, 'gyro z bias = 0.080 rad/s\n(EuRoC reference: 0.082)', color=ORANGE, fontsize=13, alpha=ease((u - 0.72) * 5))
    ax.set_ylim(-0.6, 0.6); ax.set_xlim(0, 60); ax.set_xlabel('time [s]'); ax.set_ylabel('gyro z [rad/s]')


def draw_pipeline_mini(c, act):
    for i, s in enumerate(STAGES):
        x = 0.06 + i * 0.112
        on = i in act
        c.add_patch(FancyBboxPatch((x, 0.8), 0.1, 0.07, boxstyle='round,pad=0.004,rounding_size=0.01', fc=CYAN if on else CARD, ec=CYAN, lw=1))
        c.text(x + 0.05, 0.835, s, ha='center', va='center', fontsize=9.5, color=BG if on else MUTED, weight='bold')


def sc_attitude(u, t):
    base('Stage 5: attitude'); c = canvas_ax(); draw_pipeline_mini(c, [4])
    ax = fig.add_axes([0.05, 0.12, 0.5, 0.64], projection='3d'); ax.set_facecolor(BG)
    k = int(np.searchsorted(TT, 40 + u * 100)); Rk = qrot(QE[k])
    for v, col, lab in zip(Rk.T, [RED, TEAL, CYAN], ['x', 'y', 'z']):
        ax.quiver(0, 0, 0, *v, color=col, lw=3, arrow_length_ratio=0.15); ax.text(*(v * 1.12), lab, color=col, fontsize=13)
    ax.set_xlim(-1, 1); ax.set_ylim(-1, 1); ax.set_zlim(-1, 1); ax.set_axis_off(); ax.view_init(20, 35 + 20 * u)
    ax.text2D(0.05, 0.02, f't = {TT[k]:5.1f} s', transform=ax.transAxes, color=MUTED, fontsize=12)
    pts = [('gyro bias from every rest,\ninterpolated in time', 0.05), ('Mahony filter: gyro + gravity', 0.3),
           ('full trust in gravity at rest,\nlight trust in flight', 0.5), ('runs forward and backward', 0.7), ('tilt error ≈ 1°', 0.85)]
    for i, (s, st) in enumerate(pts):
        c.text(0.58, 0.68 - i * 0.11, s, fontsize=17, color=TEAL if i == 4 else WHITE, alpha=ease((u - st) * 6), va='top',
               weight='bold' if i == 4 else 'normal')


VEL_T = TT; VEL = np.gradient(PA, TE, axis=0)


def sc_velocity(u, t):
    base('Stages 6-7: velocity and position'); c = canvas_ax(); draw_pipeline_mini(c, [5, 6])
    ax = fig.add_axes([0.07, 0.2, 0.55, 0.52]); dark(ax)
    k = int(ease(u * 1.1) * (len(td5) - 1)); tk = td5[k]
    vn = np.linalg.norm(v_naive[:, :2], axis=1)
    ax.plot(td5[:k + 1], vn[:k + 1], color=RED, lw=1.6, label='raw integrated speed')
    mm = VEL_T <= tk
    ax.plot(VEL_T[mm], np.linalg.norm(VEL[mm, :2], axis=1), color=CYAN, lw=1.2, label='PathFinder speed')
    ax.axvspan(21.1, 38.8, color=TEAL, alpha=0.15)
    ax.text(30, vn.max() * 0.9, 'ZUPT', color=TEAL, ha='center', fontsize=12)
    ax.set_xlim(0, td5[-1]); ax.set_ylim(0, vn.max() * 1.05); ax.set_xlabel('time [s]'); ax.set_ylabel('horizontal speed [m/s]')
    ax.legend(loc='upper left', facecolor=BG, edgecolor='#3a4560', labelcolor=WHITE, fontsize=11)
    pts = [('remove gravity, integrate', 0.0), ('at rest: v = 0 (ZUPT)', 0.25), ('linear de-drift\nbetween rests', 0.45),
           ('zero-phase smoothing\n(allowed: task is offline)', 0.65)]
    for i, (s, st) in enumerate(pts):
        c.text(0.66, 0.68 - i * 0.13, s, fontsize=17, alpha=ease((u - st) * 6), va='top')


def sc_blind(u, t):
    base('Stage 8: the blind 5 seconds'); c = canvas_ax(); draw_pipeline_mini(c, [7])
    ax = fig.add_axes([0.06, 0.14, 0.5, 0.6]); dark(ax); ax.set_aspect('equal')
    nb = TT > TT[-1] - 5; pre = (TT > TT[-1] - 25) & ~nb
    kb = np.flatnonzero(nb); kk = kb[:max(1, int(ease(u * 1.2) * len(kb)))]
    ax.plot(PA[pre, 0], PA[pre, 1], color=CYAN, lw=1.5, label='estimate (IMU alive)')
    ax.plot(PA[kk, 0], PA[kk, 1], color=ORANGE, lw=3, label='dead reckoning (IMU dead)')
    ax.plot(PA[kk[-1], 0], PA[kk[-1], 1], 'o', color=ORANGE, ms=9)
    sel = pre | nb
    ax.set_xlim(PA[sel, 0].min() - 0.6, PA[sel, 0].max() + 0.6); ax.set_ylim(PA[sel, 1].min() - 0.6, PA[sel, 1].max() + 0.6)
    ax.legend(loc='upper left', facecolor=BG, edgecolor='#3a4560', labelcolor=WHITE, fontsize=11)
    pts = [('IMU rows become all zeros', 0.0), ('take last trusted velocity\nand turn rate (0.5 s average)', 0.2),
           ('let both decay (τ = 3 s, 1 s)', 0.45), ('emit a pose for every\nblind timestamp', 0.65)]
    for i, (s, st) in enumerate(pts):
        c.text(0.6, 0.7 - i * 0.13, s, fontsize=17, alpha=ease((u - st) * 6), va='top', color=RED if i == 0 else WHITE)


def sc_result(u, t):
    base('Result: EuRoC MH_01 + official degradation')
    ax = fig.add_axes([0.04, 0.12, 0.5, 0.74]); dark(ax); ax.set_aspect('equal')
    k = int(min(1, u * 1.05) * (len(TT) - 1))
    ax.plot(PG[:k + 1, 0], PG[:k + 1, 1], color='#8892a6', lw=1.2, label='ground truth (hidden)')
    blind = TT[k] > TT[-1] - 5
    ax.plot(PA[:k + 1, 0], PA[:k + 1, 1], color=CYAN, lw=1.1, label='PathFinder')
    ax.plot(PA[k, 0], PA[k, 1], 'o', color=ORANGE if blind else CYAN, ms=8); ax.plot(PG[k, 0], PG[k, 1], 'o', color=WHITE, ms=4)
    ax.set_xlim(PG[:, 0].min() - 1, PG[:, 0].max() + 1); ax.set_ylim(PG[:, 1].min() - 1, PG[:, 1].max() + 1)
    ax.legend(loc='lower left', facecolor=BG, edgecolor='#3a4560', labelcolor=WHITE, fontsize=11)
    a2 = fig.add_axes([0.6, 0.55, 0.36, 0.28]); dark(a2)
    a2.plot(TT[:k + 1], ERR[:k + 1], color=CYAN); a2.set_xlim(0, TT[-1]); a2.set_ylim(0, ERR.max() * 1.1)
    a2.axvspan(TT[-1] - 5, TT[-1], color=ORANGE, alpha=0.2); a2.set_xlabel('time [s]'); a2.set_ylabel('error [m]')
    c = canvas_ax()
    c.text(0.6, 0.42, f't = {TT[k]:5.1f} s    ATE so far = {np.sqrt((ERR[:k + 1] ** 2).mean()):4.2f} m', fontsize=15,
           family='DejaVu Sans Mono', color=ORANGE if blind else WHITE)
    c.text(0.6, 0.33, 'mean over 12 degraded runs: 3.62 m', fontsize=16, color=TEAL, weight='bold', alpha=ease((u - 0.5) * 5))
    c.text(0.6, 0.27, 'naive integration: 200+ m', fontsize=16, color=RED, alpha=ease((u - 0.6) * 5))
    if blind: c.text(0.04, 0.88, 'IMU FAILED: dead reckoning', color=ORANGE, fontsize=18, weight='bold')


def sc_perf(u, t):
    base('Performance vs limits'); c = canvas_ax()
    rows = [('Peak memory', 2.45, 8, 'MB', TEAL, 0.05), ('Compute per IMU-second', 1.8, 20, 'ms', CYAN, 0.3)]
    for i, (lab, v, lim, unit, col, st) in enumerate(rows):
        y = 0.62 - i * 0.24; f = ease((u - st) * 3)
        c.text(0.08, y + 0.1, lab, fontsize=20, weight='bold', alpha=ease((u - st) * 6))
        c.add_patch(Rectangle((0.08, y), 0.6, 0.07, fc=CARD, ec='#3a4560'))
        c.add_patch(Rectangle((0.08, y), 0.6 * v / lim * f, 0.07, fc=col))
        c.text(0.7, y + 0.02, f'{v * f:4.2f} / {lim} {unit}', fontsize=20, color=col, weight='bold', family='DejaVu Sans Mono')
    c.text(0.08, 0.2, '1 CPU thread   •   offline   •   35 629 rows in  →  35 629 poses out', fontsize=18, color=WHITE,
           alpha=ease((u - 0.65) * 5))


TERM = ['$ python src/main.py dataset.zip -o estimated_trajectory.txt --meta metadata.json',
        'rows=35629  duration=184.1s  cpu=0.32s (1.8 ms per IMU-second) -> estimated_trajectory.txt',
        '$ head -2 estimated_trajectory.txt',
        '# timestamp tx ty tz qx qy qz qw',
        '1403636579.758555392 0.000000 0.000000 0.000000 -0.1163427 -0.8060970 -0.0517267 0.5779241']


def sc_run(u, t):
    base('Run it'); c = canvas_ax()
    c.add_patch(FancyBboxPatch((0.05, 0.25), 0.9, 0.55, boxstyle='round,pad=0.01,rounding_size=0.02', fc='#05070d', ec='#3a4560'))
    for i, x in enumerate([0.08, 0.1, 0.12]): c.add_patch(Circle((x, 0.76), 0.008, fc=[RED, ORANGE, TEAL][i]))
    chars = int(u * 1.25 * sum(len(l) for l in TERM)); y = 0.68
    for l in TERM:
        s = l[:max(0, chars)]; chars -= len(l)
        if not s: break
        c.text(0.08, y, s, fontsize=12.5, family='DejaVu Sans Mono', color=TEAL if l.startswith('$') else WHITE); y -= 0.075
    c.text(0.08, 0.17, 'Python 3.8+  •  no pip install  •  csv, folder or zip input  •  Dockerfile included', fontsize=16, color=MUTED)


def sc_outro(u, t):
    base(None); c = canvas_ax()
    c.text(0.5, 0.66, 'PathFinder', ha='center', fontsize=56, weight='bold', alpha=ease(u * 3))
    c.text(0.5, 0.56, 'bounded  •  light  •  fast  •  honest about its limits', ha='center', fontsize=20, color=CYAN, alpha=ease(u * 3 - 0.3))
    c.text(0.5, 0.44, 'Team: Team  •  Manipal Institute of Technology', ha='center', fontsize=17, color=WHITE, alpha=ease(u * 3 - 0.6))
    c.text(0.5, 0.38, 'Nadir Hussain  •  Abdul Haq', ha='center', fontsize=17, color=MUTED, alpha=ease(u * 3 - 0.8))
    c.text(0.5, 0.28, 'Explored too: rotor-drag EKF (documented in README)', ha='center', fontsize=14, color=MUTED, alpha=ease(u * 3 - 1.0))


FUNCS = [sc_intro, sc_mission, sc_degradation, sc_drift, sc_budget, sc_pipeline, sc_static, sc_attitude, sc_velocity,
         sc_blind, sc_result, sc_perf, sc_run, sc_outro]

# ------------------------------------------------------------------ render
silent = os.path.join(TMP, 'video.mp4')
proc = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', '1280x720',
                         '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', silent],
                        stdin=subprocess.PIPE)
for (name, cap, _), fn, d in zip(SCENES, FUNCS, durs):
    n = int(round(d * FPS))
    for f in range(n):
        u = f / max(1, n - 1)
        fn(u, f / FPS)
        caption(cap, u)
        fig.canvas.draw()
        proc.stdin.write(bytes(fig.canvas.buffer_rgba()))
    print('rendered', name, n, 'frames', flush=True)
proc.stdin.close(); proc.wait()
lst = os.path.join(TMP, 'a.txt'); open(lst, 'w').write(''.join(f"file '{w}'\n" for w in wavs))
audio = os.path.join(TMP, 'audio.wav')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', audio], check=True)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', silent, '-i', audio, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k',
                '-shortest', OUT], check=True)
print('wrote', OUT, 'duration %.1f s' % total)
