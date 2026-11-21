# PathFinder: 6-DoF Trajectory from a Degraded IMU

**Team: Team | Manipal Institute of Technology | Nadir Hussain, Abdul Haq**

**Samsung PRISM XR Hackathon 2026, Track 3: Path Finder (Trajectory Estimation Under Sensor Degradation)**

The input is a jammed IMU stream: noise and bias drift that grow over time, spikes, stuck samples, dropouts, duplicated rows, and a dead sensor for the last 5 s. PathFinder turns that stream into a full 6-DoF trajectory (`timestamp tx ty tz qx qy qz qw`) with exactly one pose per IMU row. It also dead-reckons through the IMU failure.

| Budget (organisers) | Limit | PathFinder (EuRoC MH_01, 184 s, 35.6 k rows) |
|---|---|---|
| Peak memory | ≤ 8 MB | **2.45 MB** traced heap for the *whole process* (tracemalloc, imports included) |
| Compute | ≤ 20 ms per 1 s of IMU | **1.8 ms per IMU-second** (0.33 s CPU total) |
| Threads | single CPU thread | 1 |
| Network / GPU | offline | none |
| Dependencies | — | **Python standard library only** (no numpy) |

> Why no numpy? `import numpy` alone allocates ~8 MB of traced heap, which is the entire budget. PathFinder keeps samples in `float32` `array` buffers and reuses them stage by stage. A 3-minute 200 Hz sequence fits in about 2.5 MB.

---

## Quick start

Repository: https://github.com/abdulhaq7378-hash/PathFinder

```bash
git clone https://github.com/abdulhaq7378-hash/PathFinder.git && cd PathFinder
# input can be the csv, the dataset folder (…/imu0/data.csv) or the zipped folder
python src/main.py path/to/dataset.zip -o estimated_trajectory.txt --meta metadata.json
```

Optional flags:

| Flag | Effect |
|---|---|
| `--profile` | Reports peak heap via tracemalloc (slower, timing not representative) |
| `--set key=value ...` | Overrides tuning parameters (see `P` in `src/main.py`) |

With Docker:

```bash
docker build -t pathfinder .
docker run --rm -v "$PWD/data:/data" pathfinder /data/MH01/deg -o /data/estimated_trajectory.txt
```

Input is EuRoC `imu0/data.csv`: `#timestamp [ns], w_x, w_y, w_z [rad/s], a_x, a_y, a_z [m/s²]`. These variations are auto-detected:
- column order (ts, gyro, accel vs ts, accel, gyro)
- accel in g
- gyro in deg/s
- timestamps in s/ms/µs/ns
- comma or space separators

Output is `estimated_trajectory.txt` in TUM format:
- space separated
- `# timestamp tx ty tz qx qy qz qw` header
- seconds with ns precision
- unit quaternions
- **one row per input IMU row**: no rows added or dropped, duplicates kept

---

## Pipeline

```
imu0/data.csv ─► 1 parse ─► 2 sanitise ─► 3 static detector ─► 4 bias + gravity
                                                                       │
     estimated_trajectory.txt ◄─ 8 blind 5 s ◄─ 7 position ◄─ 6 velocity ◄─ 5 attitude
```

| # | Stage | What it does | Degradation handled |
|---|---|---|---|
| 1 | Streaming parse | csv / folder / zip → `float32` buffers; unit and column-order detection | format variations |
| 2 | Sanitise | time-aware integration (`dt` per row), 3-point spike filter with a running robust scale, dead-tail detection (all-zero rows) | dropouts (missing rows), duplicates, spikes, IMU failure |
| 3 | Static detector | sliding-window variance of gyro and \|a\|, finds *every* stationary interval, not only the first | — |
| 4 | Bias / gravity | gyro bias measured in each static interval and **linearly interpolated in time**; gravity magnitude taken from static \|a\| (absorbs accel scale error) | bias drift |
| 5 | Attitude | Mahony complementary filter: gyro, plus a gated, low-passed gravity reference, plus integral bias learning. Full trust at rest, light trust in motion. Runs **forward** from the first rest and **backward** for anything before it | noise, residual bias, unknown gravity alignment |
| 6 | Velocity | gravity removal → trapezoid integration across gaps. Zero-velocity updates at rest. **Linear de-drift** of every motion segment that ends at rest (offline, non-causal). Zero-phase drift suppression (forward + backward exponential high-pass) for the rest | quadratic drift of double integration |
| 7 | Position | integration plus a zero-phase high-pass (bounded-workspace prior) | random-walk drift |
| 8 | Blind 5 s | from the last trusted state: velocity averaged over 0.5 s, decaying (τ = 3 s); turn rate decaying (τ = 1 s). Rows are emitted for every blind timestamp | complete IMU failure |

---

## Results

Test data: EuRoC MH_01_easy (the only EuRoC sequence reachable from our environment), full and cropped.
- **Full and 0–120 s crops** start at rest.
- **45 s → end and 60–150 s crops** start mid-flight, with no rest for initialisation.

Each set was degraded three ways:
- `deg`: organiser script, default settings
- `deg_hard`: `--max-level 1.5`
- `deg_raw`: script run on the raw EuRoC column order, so gyro and accel noise are swapped

Scoring:
- `tools/evaluate.py`: SE(3) Umeyama alignment, then ATE RMSE.
- Waypoint error: 10 evenly spaced checkpoints before the failure.
- Blind-5 s RMSE.
- Cross-checked with `evo_ape tum gt.tum estimated_trajectory.txt -a`, which gives 4.287 m on MH_01-deg, identical to our evaluator.

| Sequence | Variant | ATE [m] | Waypoints [m] | Blind 5 s [m] | Stand-still baseline [m] |
|---|---|---|---|---|---|
| MH_01 (184 s) | deg | 4.29 | 3.74 | 4.48 | 4.32 |
| MH_01 0–120 s | deg | 4.56 | 4.48 | 2.18 | 4.60 |
| MH_01 60–150 s | deg | 2.13 | 1.84 | 2.91 | 2.21 |
| MH_01 45 s→end | deg | 3.54 | 2.50 | 6.52 | 3.70 |
| **mean over 12 degraded runs** | | **3.62** | **3.14** | **3.68** | 3.71 |

Full table: `results/benchmark.txt`. Figures: `results/*.png`.

**Honest reading of these numbers.** With no vision, GPS, magnetometer or learned motion model, low-frequency position drift over minutes is not observable from an IMU. Naive double integration on the same data drifts by **hundreds of metres** (we measured 200 to 260 m ATE in early experiments). PathFinder keeps the error bounded, at or below the "stand-still" reference, in every run, including sequences that start mid-flight and the swapped-column degradation. It still recovers attitude accurately: tilt error is about 1°, and the gyro bias it finds (−0.003, 0.021, 0.080) rad/s matches EuRoC's own estimate (−0.002, 0.025, 0.082).

### What we tried and dropped (and why)

| Idea | Result | Decision |
|---|---|---|
| Plain strap-down integration | 12 m to 260 m ATE | rejected |
| Gyro-only attitude in flight (no accel correction) | ATE ratio 1.7× to 70× baseline | rejected: tilt drift leaks gravity |
| Rotor-drag velocity EKF (multirotor accel ∝ −velocity) | the relation holds on GT (corr 0.82), but with *estimated* attitude and self-calibrated offsets ATE got 4× to 10× worse | rejected for robustness; kept as future work |
| Numpy implementation | `import numpy` = 8 MB traced heap | replaced by stdlib `array` buffers |

---

## Repository layout

```
estimated_trajectory.txt    output on EuRoC MH_01 degraded (sample run)
metadata.json               runtime, peak heap, detected degradations, parameters
src/main.py                 the submission: standalone, stdlib-only
src/README.md               how to run
tools/degrade_imu.py        organiser degradation script (unchanged)
tools/make_data.py          builds clean / deg / deg_raw / deg_hard sets + TUM ground truth from EuRoC
tools/evaluate.py           ATE / waypoint / blind-5 s / RPE scoring (SE3 Umeyama)
tools/bench.py              runs main.py on every test set and prints the table
tools/plot.py               figures
tools/explainer_video.py    renders the narrated video (offline Kokoro TTS)
results/                    benchmark table + figures
docs/                       MIT_Team.pptx/.pdf presentation, MIT_Team_video.mp4 narrated walkthrough (<3 min), build_ppt.py
Dockerfile, requirements.txt
```

Reproduce the benchmark (tools need `numpy pandas matplotlib evo`; `main.py` needs nothing):

```bash
pip install -r requirements.txt
python tools/make_data.py <EuRoC>/MH_01_easy/mav0 MH01 data
python tools/bench.py
```
