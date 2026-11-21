#!/usr/bin/env python3
"""Fill the organiser submission template with PathFinder content.
usage: python docs/build_ppt.py "<College>" "<TeamName>" [repo_url] [video_url]
writes docs/<College>_<TeamName>.pptx
"""
import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COLLEGE = sys.argv[1] if len(sys.argv) > 1 else "MIT"
COLLEGE_FULL = "Manipal Institute of Technology, Manipal"
TEAM = sys.argv[2] if len(sys.argv) > 2 else "TEAM_NAME"
REPO = sys.argv[3] if len(sys.argv) > 3 else "github.com/abdulhaq7378-hash/PathFinder"
VIDEO = sys.argv[4] if len(sys.argv) > 4 else "<demo video link>"

BG = RGBColor(0x0A, 0x0E, 0x1A)
CARD = RGBColor(0x13, 0x1B, 0x33)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0xA9, 0xB4, 0xC8)
CYAN = RGBColor(0x00, 0xB4, 0xD8)
TEAL = RGBColor(0x2E, 0xC4, 0xA0)
ORANGE = RGBColor(0xF0, 0x8C, 0x00)
RED = RGBColor(0xE0, 0x5A, 0x5A)

prs = Presentation(os.path.join(HERE, "_template.pptx"))
S = prs.slides


def tb(slide, x, y, w, h, paras, size=14, color=WHITE, font="Calibri", anchor=MSO_ANCHOR.TOP, align=PP_ALIGN.LEFT,
       space=4):
    """paras: list of str or (str, dict(bold, color, size, font))"""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    for i, p in enumerate(paras):
        txt, o = (p, {}) if isinstance(p, str) else p
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        para.space_after = Pt(o.get("space", space))
        r = para.add_run()
        r.text = txt
        f = r.font
        f.size = Pt(o.get("size", size))
        f.bold = o.get("bold", False)
        f.name = o.get("font", font)
        f.color.rgb = o.get("color", color)
    return box


def card(slide, x, y, w, h, fill=CARD, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1.25)
    s.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.08
    return s


def set_runs(shape, texts):
    """Replace text of the existing paragraphs/runs keeping template formatting."""
    paras = shape.text_frame.paragraphs
    for p, t in zip(paras, texts):
        runs = p.runs
        if runs:
            runs[0].text = t
            for r in runs[1:]:
                r.text = ""


def img(slide, path, x, y, w=None, h=None):
    kw = {}
    if w: kw["width"] = Inches(w)
    if h: kw["height"] = Inches(h)
    return slide.shapes.add_picture(path, Inches(x), Inches(y), **kw)


R = os.path.join(ROOT, "results")

# ---------------------------------------------------------------- 1 title
s = S[0]
for sh in s.shapes:
    if not sh.has_text_frame:
        continue
    t = sh.text_frame.text
    if t == "Track No":
        set_runs(sh, ["TRACK 03"])
    elif t.startswith("Team Name"):
        set_runs(sh, ["Team name: " + TEAM + "   |   Project: PathFinder", COLLEGE_FULL])
    elif t == "Members Details":
        sh.text_frame.paragraphs[0].runs[0].text = ""
tb(s, 0.55, 3.45, 8.0, 0.5, [("Path Finder: Trajectory Estimation Under Sensor Degradation", {"size": 18, "color": CYAN, "bold": True})])
tb(s, 0.55, 4.0, 4.5, 1.2, [("Team members", {"size": 12, "color": MUTED, "bold": True}),
                             ("Nadir Hussain  (Electronics & Instrumentation, 3rd yr)", {"size": 13}),
                             ("Abdul Haq  (Biomedical Engineering, 3rd yr)", {"size": 13})])
tb(s, 5.4, 4.0, 3.9, 1.2, [("Deliverable", {"size": 12, "color": MUTED, "bold": True}),
                            ("main.py: degraded IMU in, 6-DoF trajectory out", {"size": 13}),
                            ("Python stdlib only | 2.45 MB | 1.8 ms per IMU-s", {"size": 13})])

# ---------------------------------------------------------------- 2 problem
s = S[1]
tb(s, 0.5, 1.05, 4.4, 0.45, [("A jammed aircraft must fly blind", {"size": 20, "bold": True})])
tb(s, 0.5, 1.6, 4.3, 3.7, [
    ("Only an IMU: no GPS, camera or magnetometer. Ground truth and waypoints are hidden.", {"size": 14}),
    ("Jamming gets worse over time: white noise, bias random walk, scale drift, spikes, stuck samples.", {"size": 14}),
    ("Missing rows (dropouts) and duplicated rows, then the IMU dies: the last 5 s are all zeros.", {"size": 14}),
    ("Output: a 6-DoF pose for every IMU row, including the blind 5 s.", {"size": 14}),
    ("Budget: 8 MB RAM, 20 ms per 1 s of IMU, 1 CPU thread, offline.", {"size": 14, "color": ORANGE, "bold": True}),
], space=8)
img(s, os.path.join(R, "degradation.png"), 4.95, 1.15, w=4.6)
tb(s, 4.95, 4.05, 4.6, 0.9, [("Why it is hard: double integration turns a 0.1 m/s² bias into 1.6 km of drift in 3 minutes, "
                               "and 1° of tilt error leaks 0.17 m/s² of gravity into position.", {"size": 12, "color": MUTED})])

# ---------------------------------------------------------------- 3 solution
s = S[2]
tb(s, 0.5, 1.1, 9.0, 0.5, [("PathFinder: estimate what the IMU can observe, and keep the rest bounded", {"size": 20, "bold": True})])
stats = [("2.45 MB", "peak heap, whole process (limit 8 MB)", CYAN),
         ("1.8 ms", "per IMU-second (limit 20 ms)", TEAL),
         ("1 : 1", "one pose per IMU row, blind 5 s included", ORANGE)]
for i, (big, small, col) in enumerate(stats):
    x = 0.5 + i * 3.05
    card(s, x, 1.75, 2.85, 1.35)
    tb(s, x + 0.15, 1.8, 2.6, 0.7, [(big, {"size": 32, "bold": True, "color": col})])
    tb(s, x + 0.15, 2.5, 2.6, 0.55, [(small, {"size": 12, "color": MUTED})])
ideas = [
    ("Pure Python stdlib.", " Importing numpy alone uses 8 MB of heap, so we keep float32 array buffers and reuse them in place."),
    ("Finds every rest period.", " A variance detector gives the gyro bias at each rest, interpolated over time to follow bias drift."),
    ("Attitude.", " Mahony filter that fully trusts gravity at rest, trusts it lightly in flight, and learns bias online. It runs forward and backward."),
    ("Velocity.", " Zero-velocity updates at rest, linear de-drift between rests, and zero-phase drift suppression (offline smoothing)."),
    ("Blind 5 s.", " Dead reckoning from the last trusted state, with velocity and turn rate decaying."),
]
tb(s, 0.5, 3.3, 9.0, 2.1, [(a + b, {"size": 13}) for a, b in ideas], space=5)

# ---------------------------------------------------------------- 4 architecture
s = S[3]
tb(s, 0.5, 1.05, 9.0, 0.45, [("8-stage offline pipeline, single pass per stage, buffers reused", {"size": 18, "bold": True})])
stages = [("1 Parse", "csv | folder | zip\nunits + column order"), ("2 Sanitise", "gaps, duplicates,\nspikes, dead tail"),
          ("3 Static detector", "sliding-window\nvariance test"), ("4 Bias + gravity", "per rest interval,\ntime-interpolated"),
          ("8 Blind 5 s", "decaying v, w\nfrom last state"), ("7 Position", "integrate +\nzero-phase HP"),
          ("6 Velocity", "ZUPT + de-drift +\ndrift suppression"), ("5 Attitude", "Mahony fwd + bwd,\ngated gravity")]
cols = [CYAN, CYAN, TEAL, TEAL, ORANGE, ORANGE, TEAL, CYAN]
W, H = 1.95, 1.2
for i, (t, d) in enumerate(stages):
    r, c = divmod(i, 4)
    x = 0.5 + c * 2.3
    y = 1.65 + r * 1.85
    card(s, x, y, W, H, line=cols[i])
    tb(s, x + 0.08, y + 0.08, W - 0.16, 0.4, [(t, {"size": 14, "bold": True, "color": cols[i]})])
    tb(s, x + 0.08, y + 0.5, W - 0.16, 0.7, [(l, {"size": 11, "color": MUTED, "space": 0}) for l in d.split("\n")])
    if c < 3:
        a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW if r == 0 else MSO_SHAPE.LEFT_ARROW,
                               Inches(x + W + 0.07), Inches(y + H / 2 - 0.1), Inches(0.21), Inches(0.2))
        a.fill.solid(); a.fill.fore_color.rgb = MUTED; a.line.fill.background()
a = s.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(0.5 + 3 * 2.3 + W / 2 - 0.1), Inches(1.65 + H + 0.12), Inches(0.2), Inches(0.4))
a.fill.solid(); a.fill.fore_color.rgb = MUTED; a.line.fill.background()
tb(s, 0.5, 5.0, 9.0, 0.4, [("Memory: float32 arrays (~57 B per IMU row). Accel buffers become world acceleration, then position; gyro buffers become velocity.",
                            {"size": 11, "color": MUTED})])

# ---------------------------------------------------------------- 5 final output
s = S[4]
for sh in s.shapes:
    if sh.has_text_frame and "Track Final Output" in sh.text_frame.text:
        set_runs(sh, ["TRACK 3 FINAL OUTPUT"])
tb(s, 0.5, 1.05, 4.5, 0.45, [("Output exactly as required", {"size": 18, "bold": True})])
card(s, 0.5, 1.55, 4.6, 1.35)
tb(s, 0.6, 1.6, 4.45, 1.3, [("estimated_trajectory.txt  (TUM, space separated)", {"size": 10, "color": MUTED}),
                             ("# timestamp tx ty tz qx qy qz qw", {"size": 9, "font": "Courier New", "color": TEAL}),
                             ("1403636579.758555392 0.000000 0.000000 0.000000", {"size": 9, "font": "Courier New"}),
                             ("   -0.1163427 -0.8060970 -0.0517267 0.5779241", {"size": 9, "font": "Courier New"}),
                             ("35 629 input rows -> 35 629 poses, unit quaternions", {"size": 10, "color": ORANGE})], space=1)
rows = [("Test set (EuRoC MH_01, degraded)", "ATE", "Waypoints", "Blind 5 s"),
        ("Full 184 s", "4.29", "3.74", "4.48"), ("0-120 s", "4.56", "4.48", "2.18"),
        ("60-150 s (starts mid-flight)", "2.13", "1.84", "2.91"), ("45 s - end (starts mid-flight)", "3.54", "2.50", "6.52"),
        ("Mean of 12 degraded runs [m]", "3.62", "3.14", "3.68")]
tbl = s.shapes.add_table(len(rows), 4, Inches(0.5), Inches(3.05), Inches(4.6), Inches(2.1)).table
tbl.columns[0].width = Inches(1.9)
for j in range(1, 4):
    tbl.columns[j].width = Inches(0.9)
for i, row in enumerate(rows):
    for j, v in enumerate(row):
        cell = tbl.cell(i, j)
        cell.text = v
        cell.fill.solid()
        cell.fill.fore_color.rgb = CARD if i % 2 else RGBColor(0x0D, 0x1B, 0x3E)
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
        f = p.runs[0].font
        f.size = Pt(10); f.name = "Calibri"; f.color.rgb = CYAN if i == 0 else WHITE
        f.bold = i in (0, len(rows) - 1)
        cell.margin_top = cell.margin_bottom = Inches(0.02)
img(s, os.path.join(R, "trajectory_topview.png"), 5.3, 1.05, h=3.6)
tb(s, 5.3, 4.65, 4.3, 0.75, [("ATE after SE(3) Umeyama alignment; evo_ape agrees (4.287 m). "
                              "Naive strap-down on the same data: 200+ m.", {"size": 11, "color": MUTED})])

# ---------------------------------------------------------------- 6 differentiation
s = S[5]
tb(s, 0.5, 1.05, 9.0, 0.45, [("What sets PathFinder apart", {"size": 18, "bold": True})])
cmp_rows = [("", "Typical approach", "PathFinder"),
            ("Memory", "numpy/scipy EKF: 10-40 MB heap", "2.45 MB whole process, stdlib only"),
            ("Runtime", "matrix EKF at 200 Hz in Python", "1.8 ms per IMU-second (11x margin)"),
            ("Drift", "strap-down: 100s of metres", "bounded: 0.98x stand-still error"),
            ("Gyro bias", "first 1-2 s only", "every rest period, time-interpolated"),
            ("Dropouts", "assume fixed dt", "per-row dt, trapezoid across gaps"),
            ("Robustness", "fixed column order / units", "auto order, g, deg/s, s..ns, zip/folder/csv")]
tbl = s.shapes.add_table(len(cmp_rows), 3, Inches(0.5), Inches(1.6), Inches(9.0), Inches(3.0)).table
tbl.columns[0].width = Inches(1.6); tbl.columns[1].width = Inches(3.4); tbl.columns[2].width = Inches(4.0)
for i, row in enumerate(cmp_rows):
    for j, v in enumerate(row):
        cell = tbl.cell(i, j)
        cell.text = v
        cell.fill.solid()
        cell.fill.fore_color.rgb = CARD if i % 2 else RGBColor(0x0D, 0x1B, 0x3E)
        p = cell.text_frame.paragraphs[0]
        f = p.runs[0].font if p.runs else None
        if f:
            f.size = Pt(13); f.name = "Calibri"
            f.color.rgb = CYAN if i == 0 else (TEAL if j == 2 else (MUTED if j == 1 else WHITE))
            f.bold = i == 0 or j == 0
tb(s, 0.5, 4.75, 9.0, 0.6, [("Measured gyro bias (-0.003, 0.021, 0.080) rad/s matches EuRoC's own estimate (-0.002, 0.025, 0.082). Tilt error stays around 1°.",
                             {"size": 12, "color": MUTED})])

# ---------------------------------------------------------------- 7 demo & setup
s = S[6]
tb(s, 0.5, 1.05, 4.6, 0.45, [("Run it in one line", {"size": 18, "bold": True})])
card(s, 0.5, 1.55, 4.6, 2.1)
tb(s, 0.6, 1.62, 4.4, 2.0, [
    ("# no install needed (Python 3.8+)", {"size": 10, "font": "Courier New", "color": MUTED}),
    ("python src/main.py dataset.zip \\", {"size": 10, "font": "Courier New", "color": TEAL}),
    ("   -o estimated_trajectory.txt \\", {"size": 10, "font": "Courier New", "color": TEAL}),
    ("   --meta metadata.json", {"size": 10, "font": "Courier New", "color": TEAL}),
    ("# memory check", {"size": 10, "font": "Courier New", "color": MUTED}),
    ("python src/main.py dataset.zip --profile", {"size": 10, "font": "Courier New", "color": TEAL}),
    ("# docker", {"size": 10, "font": "Courier New", "color": MUTED}),
    ("docker build -t pathfinder . && docker run ...", {"size": 10, "font": "Courier New", "color": TEAL}),
], space=1)
tb(s, 0.5, 3.8, 4.6, 1.5, [("Repository: " + REPO, {"size": 12, "color": CYAN}),
                            ("Demo video: " + VIDEO, {"size": 12, "color": CYAN}),
                            ("Reproduce the scores: tools/make_data.py, then tools/bench.py", {"size": 12, "color": MUTED})], space=6)
img(s, os.path.join(R, "error_over_time.png"), 5.25, 1.15, w=4.35)
tb(s, 5.25, 3.0, 4.35, 2.3, [("Input accepted as csv, folder or zip", {"size": 12}),
                             ("metadata.json reports the detected gaps, duplicates, spikes, failure window, rest intervals and gyro bias", {"size": 12}),
                             ("Error stays bounded through 774 dropout gaps and the final 5 s with the IMU dead", {"size": 12})], space=6)

# ---------------------------------------------------------------- 8 brownie
s = S[7]
tb(s, 0.5, 1.05, 9.0, 0.45, [("Brownie points: research beyond the baseline", {"size": 18, "bold": True})])
items = [("Rotor-drag physics", "Multirotor horizontal accel is proportional to -velocity (corr 0.82 on ground truth). We built an error-state EKF with a drag-velocity measurement, "
                                 "but with estimated attitude it was 4-10x worse, so we left it out of the submission.", ORANGE),
         ("Memory engineering", "Lazy imports and a tiny arg parser save 1.8 MB of interpreter heap. Arrays are reused in place, so heap is about 57 B per IMU row.", CYAN),
         ("Robust evaluation", "12 degraded variants: default, 1.5x harder, swapped-column script misuse, and crops that start mid-flight. Our scorer matches evo.", TEAL),
         ("Honest limits", "With an IMU only, low-frequency drift over minutes cannot be observed. Next: a learned motion prior (tiny 1D-CNN, about 200 KB) and a drag model calibrated per platform.", MUTED)]
for i, (h, d, col) in enumerate(items):
    r, c = divmod(i, 2)
    x = 0.5 + c * 4.6
    y = 1.6 + r * 1.9
    card(s, x, y, 4.4, 1.75)
    tb(s, x + 0.12, y + 0.08, 4.15, 0.4, [(h, {"size": 15, "bold": True, "color": col})])
    tb(s, x + 0.12, y + 0.5, 4.15, 1.2, [(d, {"size": 12})])

out = os.path.join(HERE, f"{COLLEGE.replace(' ', '')}_{TEAM}.pptx")
prs.save(out)
print(out)
