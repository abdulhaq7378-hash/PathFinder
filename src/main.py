#!/usr/bin/env python3
"""
PathFinder - 6-DoF trajectory from a degraded IMU stream
Samsung PRISM XR Hackathon 2026, Track 3 "Path Finder: Trajectory Estimation Under Sensor Degradation"

Pure Python standard library (no numpy / scipy): importing numpy alone costs ~8 MB of traced heap,
which is the whole budget. Samples live in compact float32 `array` buffers and every stage works
in place, so peak heap is ~3-4 MB for a 3-minute 200 Hz sequence.

Usage
    python main.py <imu.csv | dataset_dir | dataset.zip> [-o estimated_trajectory.txt]
                   [--meta metadata.json] [--profile] [--set key=value ...]

Input   EuRoC MAV imu0/data.csv : #timestamp[ns], w_x, w_y, w_z [rad/s], a_x, a_y, a_z [m/s^2]
        (gyro/accel column order, g vs m/s^2, deg/s, s/ms/us/ns stamps are auto-detected)
Output  TUM: "timestamp[s] tx ty tz qx qy qz qw", exactly one pose per input IMU row.

Pipeline (offline, non-causal smoothing allowed by the organisers)
    1 parse      streaming csv -> float32 buffers
    2 sanitise   duplicate stamps, dropout gaps (time-aware integration), 3-point spike filter,
                 dead-sensor tail (IMU failure, all-zero rows) detection
    3 static     sliding-window variance detector finds every stationary interval
    4 bias       gyro bias per static interval, linearly interpolated in time (tracks bias drift),
                 gravity magnitude from static accel norm
    5 attitude   Mahony complementary filter (gyro + gated low-passed gravity reference + online
                 bias integral). Runs forward from the first static interval and backward for
                 anything recorded before it.
    6 velocity   gravity removal, trapezoid integration, zero-velocity updates in static intervals,
                 linear de-drift of every motion segment that ends at rest, zero-phase drift
                 suppression (forward/backward exponential high-pass) for the rest
    7 position   integration + zero-phase high-pass (bounded workspace prior)
    8 blind 5 s  dead reckoning from the last trusted state with decaying velocity / turn rate
"""
import sys
import tracemalloc

_PROFILE = "--profile" in sys.argv
if _PROFILE:
    tracemalloc.start()

import math
import os
import time
from array import array

G0 = 9.80665

# ----------------------------------------------------------------------------- parameters
P = {
    "static_win": 0.5,        # s     window of the stationarity test
    "static_gyro": 0.03,      # rad/s max gyro std (all axes) inside a static window
    "static_acc": 0.25,       # m/s^2 max std of |a| inside a static window
    "static_min": 0.6,        # s     minimum length of a static interval
    "kp": 0.15,               # Mahony proportional gain
    "ki": 0.02,               # Mahony integral gain (bias learning)
    "kp_static": 2.0,         # gravity-correction gain multiplier while stationary
    "acc_lp_tau": 0.25,       # s     low-pass of accel used as gravity reference
    "acc_gate": 0.8,          # m/s^2 skip gravity reference when ||a_lp|-g| is larger
    "spike_k": 6.0,           # spike threshold (x running robust scale)
    "vel_tau_h": 1.5,         # s     horizontal velocity drift suppression (<=0 off)
    "vel_tau_v": 1.0,         # s     vertical velocity drift suppression
    "pos_tau_h": 5.0,         # s     horizontal position high-pass (<=0 off)
    "pos_tau_v": 2.0,         # s     vertical position high-pass
    "dedrift": 1.0,           # 1 = linear velocity de-drift between rest intervals
    "blind_v_tau": 3.0,       # s     velocity decay during IMU failure
    "blind_w_tau": 1.0,       # s     turn-rate decay during IMU failure
    "blind_avg_s": 0.5,       # s     averaging window for the last trusted v / w
    "gap_factor": 1.8,        # dt > gap_factor * median dt  => dropout gap
}


# ----------------------------------------------------------------------------- input
def _open_text(path):
    """Text stream for a csv, a dataset folder (imu0/data.csv inside) or a zip of that folder."""
    if os.path.isdir(path):
        for cand in ("imu0/data.csv", "mav0/imu0/data.csv", "data.csv"):
            p = os.path.join(path, cand)
            if os.path.isfile(p):
                return open(p, "r", encoding="utf-8-sig")
        for root, _, files in os.walk(path):
            if "data.csv" in files and os.path.basename(root) == "imu0":
                return open(os.path.join(root, "data.csv"), "r", encoding="utf-8-sig")
        raise FileNotFoundError("no imu0/data.csv inside " + path)
    with open(path, "rb") as fb:
        is_zip = fb.read(4) == b"PK\x03\x04"
    if is_zip:
        import io, zipfile          # lazy: only paid for zip input
        zf = zipfile.ZipFile(path)
        names = [n for n in zf.namelist() if n.endswith(".csv") and "__MACOSX" not in n]
        pick = [n for n in names if n.endswith("imu0/data.csv")] or names
        if not pick:
            raise FileNotFoundError("no csv in zip " + path)
        return io.TextIOWrapper(zf.open(pick[0]), encoding="utf-8-sig")
    return open(path, "r", encoding="utf-8-sig")


def _f(x):
    v = float(x)
    return 0.0 if v != v else v          # NaN -> 0 (treated like a dead sample)


def read_imu(path):
    """Stream the csv into compact buffers: ts (int64 ns) + 6 float32 channels in file order."""
    ts = array("q")
    ch = [array("f") for _ in range(6)]
    a0, a1, a2, a3, a4, a5 = (c.append for c in ch)
    tapp = ts.append
    with _open_text(path) as f:
        for line in f:
            if not line or line[0] == "#":
                continue
            parts = line.split(",")
            if len(parts) < 7:
                parts = line.split()
                if len(parts) < 7:
                    continue
            s0 = parts[0].strip()
            try:
                if "." in s0 or "e" in s0 or "E" in s0:
                    tf = float(s0)
                    t = int(round(tf * 1e9)) if tf < 1e11 else int(tf)
                else:
                    t = int(s0)
                v0, v1, v2, v3, v4, v5 = (_f(x) for x in parts[1:7])
            except ValueError:
                continue                      # header / garbage
            tapp(t)
            a0(v0); a1(v1); a2(v2); a3(v3); a4(v4); a5(v5)
    return ts, ch


def _ts_scale(ts):
    n = len(ts)
    if n < 3:
        return 1
    steps = sorted(ts[i + 1] - ts[i] for i in range(min(n - 1, 2000)))
    med = steps[len(steps) // 2]
    if med >= 100_000:
        return 1              # ns
    if med >= 100:
        return 1000           # us
    if med >= 1:
        return 1_000_000      # ms
    return 1


# ----------------------------------------------------------------------------- helpers
def _mean_norm(c0, c1, c2, idx):
    s = 0.0
    for i in idx:
        s += math.sqrt(c0[i] * c0[i] + c1[i] * c1[i] + c2[i] * c2[i])
    return s / max(1, len(idx))


def despike(c, n, k):
    """In-place 3-point spike filter on c[:n]; scale = EMA of |second difference|."""
    if n < 5:
        return 0
    m = min(200, n - 2)
    scale = sum(abs(c[i] - 0.5 * (c[i - 1] + c[i + 1])) for i in range(1, m + 1)) / m + 1e-6
    prev, cur, fixed = c[0], c[1], 0
    for i in range(1, n - 1):
        nxt = c[i + 1]
        d = cur - 0.5 * (prev + nxt)
        ad = d if d >= 0 else -d
        if ad > k * scale and ad > 3.0 * abs(nxt - prev):
            cur = 0.5 * (prev + nxt)
            c[i] = cur
            fixed += 1
        else:
            scale += 0.002 * (ad - scale)
        prev, cur = cur, nxt
    return fixed


def lowpass_zero_phase(x, out, dts, tau, lo, hi):
    """out[lo:hi] = forward-backward exponential low-pass of x[lo:hi] (time-aware, edge-following)."""
    if hi - lo < 2:
        for i in range(lo, hi):
            out[i] = x[i]
        return
    y = x[lo]
    for i in range(lo, hi):
        d = dts[i]
        y += d / (tau + d) * (x[i] - y)
        out[i] = y
    y = out[hi - 1]
    for i in range(hi - 2, lo - 1, -1):
        d = dts[i + 1]
        y += d / (tau + d) * (out[i] - y)
        out[i] = y


def highpass_inplace(x, tmp, dts, tau, lo, hi, keep_start=False):
    if tau <= 0 or hi - lo < 2:
        return
    lowpass_zero_phase(x, tmp, dts, tau, lo, hi)
    off = tmp[lo] if keep_start else 0.0
    for i in range(lo, hi):
        x[i] = x[i] - tmp[i] + off


def static_intervals(ts, gx, gy, gz, ax, ay, az, nf, med_dt, prm):
    """Sliding-window variance test. Returns list of [i0, i1) stationary intervals."""
    m = max(5, int(prm["static_win"] / med_dt))
    if nf < m:
        return []
    thr_g = prm["static_gyro"] ** 2
    thr_a = prm["static_acc"] ** 2
    s = [0.0] * 8   # sums: gx, gy, gz, gx2, gy2, gz2, an, an2
    out = []
    cur0 = -1
    covered = -1
    for i in range(nf):
        x, y, z = gx[i], gy[i], gz[i]
        an = math.sqrt(ax[i] * ax[i] + ay[i] * ay[i] + az[i] * az[i])
        s[0] += x; s[1] += y; s[2] += z; s[3] += x * x; s[4] += y * y; s[5] += z * z
        s[6] += an; s[7] += an * an
        j = i - m
        if j >= 0:
            x, y, z = gx[j], gy[j], gz[j]
            an = math.sqrt(ax[j] * ax[j] + ay[j] * ay[j] + az[j] * az[j])
            s[0] -= x; s[1] -= y; s[2] -= z; s[3] -= x * x; s[4] -= y * y; s[5] -= z * z
            s[6] -= an; s[7] -= an * an
        if i < m - 1:
            continue
        inv = 1.0 / m
        vg = (s[3] - s[0] * s[0] * inv + s[4] - s[1] * s[1] * inv + s[5] - s[2] * s[2] * inv) * inv
        va = (s[7] - s[6] * s[6] * inv) * inv
        ok = vg < thr_g and va < thr_a and (ts[i] - ts[i - m + 1]) * 1e-9 < 1.5 * m * med_dt
        if ok:
            lo = i - m + 1
            if cur0 < 0 or lo > covered + 1:
                if cur0 >= 0:
                    out.append([cur0, covered + 1])
                cur0 = lo
            covered = i
    if cur0 >= 0:
        out.append([cur0, covered + 1])
    min_n = prm["static_min"] / med_dt
    return [iv for iv in out if iv[1] - iv[0] >= min_n]


def _qmul_exp(qw, qx, qy, qz, cx, cy, cz, dt):
    """q <- q (x) Exp(c*dt), normalised."""
    w = math.sqrt(cx * cx + cy * cy + cz * cz)
    th = w * dt
    if th < 1e-12:
        return qw, qx, qy, qz
    s = math.sin(0.5 * th) / w
    c = math.cos(0.5 * th)
    dx, dy, dz = cx * s, cy * s, cz * s
    nw = qw * c - qx * dx - qy * dy - qz * dz
    nx = qw * dx + qx * c + qy * dz - qz * dy
    ny = qw * dy - qx * dz + qy * c + qz * dx
    nz = qw * dz + qx * dy - qy * dx + qz * c
    r = 1.0 / math.sqrt(nw * nw + nx * nx + ny * ny + nz * nz)
    return nw * r, nx * r, ny * r, nz * r


def _q_from_gravity(mx, my, mz):
    """Shortest-arc rotation taking the measured up-vector (body) to world +z."""
    an = math.sqrt(mx * mx + my * my + mz * mz) or 1.0
    ux, uy, uz = mx / an, my / an, mz / an
    qw, qx, qy, qz = 1.0 + uz, uy, -ux, 0.0
    qn = math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
    if qn < 1e-9:
        return 0.0, 1.0, 0.0, 0.0
    return qw / qn, qx / qn, qy / qn, qz / qn


# ----------------------------------------------------------------------------- core
def estimate(ts, ch, prm=P, stats=None):
    if stats is None:
        stats = {}
    n = len(ts)
    stats["rows"] = n
    if n == 0:
        return None

    # ---- column order / units ---------------------------------------------------------
    probe = [i for i in range(0, n, max(1, n // 500)) if any(ch[j][i] != 0.0 for j in range(6))]
    probe = probe or [0]
    nA = _mean_norm(ch[0], ch[1], ch[2], probe)
    nB = _mean_norm(ch[3], ch[4], ch[5], probe)

    def accel_like(v):
        return min(abs(v - G0), abs(v - 1.0) * 6.0)

    if accel_like(nB) <= accel_like(nA):
        gx, gy, gz, ax, ay, az = ch
        order, na = "ts,gyro,accel", nB
    else:
        ax, ay, az, gx, gy, gz = ch
        order, na = "ts,accel,gyro", nA
    stats["column_order"] = order
    if abs(na - 1.0) < abs(na - G0):
        for c in (ax, ay, az):
            for i in range(n):
                c[i] *= G0
        stats["accel_unit"] = "g"
    if _mean_norm(gx, gy, gz, probe) > 5.0:
        d2r = math.pi / 180.0
        for c in (gx, gy, gz):
            for i in range(n):
                c[i] *= d2r
        stats["gyro_unit"] = "deg/s"

    # ---- time base ----------------------------------------------------------------------
    sc = _ts_scale(ts)
    if sc != 1:
        for i in range(n):
            ts[i] *= sc
    dts = array("f", bytes(4 * n))
    steps = sorted(max(0, ts[i + 1] - ts[i]) for i in range(min(n - 1, 4000)))
    med_dt = max(1e-4, steps[len(steps) // 2] * 1e-9) if steps else 0.005
    gaps = dups = 0
    gap_time = 0.0
    for i in range(1, n):
        d = (ts[i] - ts[i - 1]) * 1e-9
        if d <= 0.0:
            d = 0.0
            dups += 1
        elif d > prm["gap_factor"] * med_dt:
            gaps += 1
            gap_time += d - med_dt
        dts[i] = d
    stats.update(median_dt_s=round(med_dt, 6), dropout_gaps=gaps, dropout_time_s=round(gap_time, 3),
                 duplicate_stamps=dups)

    # ---- dead-sensor tail -------------------------------------------------------------------
    nf = n
    while nf > 0 and all(abs(ch[j][nf - 1]) < 1e-12 for j in range(6)):
        nf -= 1
    if n - nf < 3:
        nf = n
    stats["failure_rows"] = n - nf
    stats["failure_seconds"] = round((ts[n - 1] - ts[nf - 1]) * 1e-9, 3) if nf < n else 0.0
    if nf < 10:
        nf = n   # nothing usable: treat everything as data

    # ---- spikes -------------------------------------------------------------------------------
    stats["spikes_fixed"] = sum(despike(c, nf, prm["spike_k"]) for c in (ax, ay, az, gx, gy, gz))

    # ---- static intervals, gyro bias, gravity --------------------------------------------
    ivs = static_intervals(ts, gx, gy, gz, ax, ay, az, nf, med_dt, prm)
    is_static = bytearray(n)
    bias_t, bias_v = [], []
    gsum = gcnt = 0.0
    for i0, i1 in ivs:
        for k in range(i0, i1):
            is_static[k] = 1
        m = i1 - i0
        bias_t.append(0.5 * (ts[i0] + ts[i1 - 1]))
        bias_v.append((sum(gx[i0:i1]) / m, sum(gy[i0:i1]) / m, sum(gz[i0:i1]) / m))
        for k in range(i0, i1):
            gsum += math.sqrt(ax[k] ** 2 + ay[k] ** 2 + az[k] ** 2)
        gcnt += m
    gmag = gsum / gcnt if gcnt else G0
    if not 9.0 < gmag < 10.6:
        gmag = G0
    stats.update(static_intervals=len(ivs), static_seconds=round(sum(b - a for a, b in ivs) * med_dt, 2),
                 gravity=round(gmag, 4),
                 gyro_bias_static=[[round(c, 5) for c in b] for b in bias_v[:6]])

    def bias_at(t):
        if not bias_t:
            return 0.0, 0.0, 0.0
        if t <= bias_t[0]:
            return bias_v[0]
        if t >= bias_t[-1]:
            return bias_v[-1]
        j = 1
        while bias_t[j] < t:
            j += 1
        u = (t - bias_t[j - 1]) / (bias_t[j] - bias_t[j - 1])
        b0, b1 = bias_v[j - 1], bias_v[j]
        return (b0[0] + u * (b1[0] - b0[0]), b0[1] + u * (b1[1] - b0[1]), b0[2] + u * (b1[2] - b0[2]))

    # anchor = first static interval (or start)
    if ivs:
        k0 = ivs[0][0]
        i0, i1 = ivs[0]
        m = i1 - i0
        mx, my, mz = sum(ax[i0:i1]) / m, sum(ay[i0:i1]) / m, sum(az[i0:i1]) / m
    else:
        k0 = 0
        m = min(nf, max(1, int(0.5 / med_dt)))
        mx, my, mz = sum(ax[:m]) / m, sum(ay[:m]) / m, sum(az[:m]) / m
    q_init = _q_from_gravity(mx, my, mz)

    # ---- attitude (Mahony) --------------------------------------------------------------
    QW = array("f", bytes(4 * n)); QX = array("f", bytes(4 * n))
    QY = array("f", bytes(4 * n)); QZ = array("f", bytes(4 * n))
    kp, ki, tau_a, gate = prm["kp"], prm["ki"], prm["acc_lp_tau"], prm["acc_gate"]
    ks = prm["kp_static"]
    last_w = [0.0, 0.0, 0.0]
    avg_n = max(1, int(prm["blind_avg_s"] / med_dt))

    def attitude_pass(k_from, k_to, step, q):
        qw, qx, qy, qz = q
        ix = iy = iz = 0.0
        lx, ly, lz = mx, my, mz
        bt_next = None
        bx, by, bz = bias_at(ts[k_from])
        pk = k_from
        acc_w = [0.0, 0.0, 0.0, 0]
        for k in range(k_from, k_to, step):
            if k != k_from:
                dt = dts[k] if step > 0 else dts[pk]
                if (k & 63) == 0:
                    bx, by, bz = bias_at(ts[k])
                if dt > 0.0:
                    axk, ayk, azk = ax[k], ay[k], az[k]
                    a = dt / (tau_a + dt)
                    lx += a * (axk - lx); ly += a * (ayk - ly); lz += a * (azk - lz)
                    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
                    ex = ey = ez = 0.0
                    if ln > 1e-6 and abs(ln - gmag) < gate:
                        vx = 2.0 * (qx * qz - qw * qy)
                        vy = 2.0 * (qy * qz + qw * qx)
                        vz = qw * qw - qx * qx - qy * qy + qz * qz
                        inv = 1.0 / ln
                        mxn, myn, mzn = lx * inv, ly * inv, lz * inv
                        ex = myn * vz - mzn * vy
                        ey = mzn * vx - mxn * vz
                        ez = mxn * vy - myn * vx
                        if is_static[k]:
                            ex *= ks; ey *= ks; ez *= ks         # trust gravity fully at rest
                        if step > 0:
                            ix += ki * ex * dt; iy += ki * ey * dt; iz += ki * ez * dt
                    # trapezoid turn rate across the step (bridges dropout gaps)
                    wx = 0.5 * (gx[k] + gx[pk]) - bx
                    wy = 0.5 * (gy[k] + gy[pk]) - by
                    wz = 0.5 * (gz[k] + gz[pk]) - bz
                    g_k = 1.0 if is_static[k] else kp
                    if step > 0:
                        cx, cy, cz = wx + g_k * ex + ix, wy + g_k * ey + iy, wz + g_k * ez + iz
                    else:   # reversed time: rotate backwards, correction keeps its sense
                        cx, cy, cz = -wx + g_k * ex - ix, -wy + g_k * ey - iy, -wz + g_k * ez - iz
                    qw, qx, qy, qz = _qmul_exp(qw, qx, qy, qz, cx, cy, cz, dt)
                    if step > 0 and k >= nf - avg_n:
                        acc_w[0] += wx + ix; acc_w[1] += wy + iy; acc_w[2] += wz + iz; acc_w[3] += 1
            QW[k] = qw; QX[k] = qx; QY[k] = qy; QZ[k] = qz
            pk = k
        if step > 0 and acc_w[3]:
            last_w[:] = [acc_w[j] / acc_w[3] for j in range(3)]
        return ix, iy, iz

    ib = attitude_pass(k0, nf, 1, q_init)
    if k0 > 0:
        attitude_pass(k0, -1, -1, q_init)
    stats["mahony_bias_correction"] = [round(-c, 5) for c in ib]

    # ---- world linear acceleration (overwrites accel buffers) ------------------------------
    for k in range(nf):
        qw, qx, qy, qz = QW[k], QX[k], QY[k], QZ[k]
        a0, a1, a2 = ax[k], ay[k], az[k]
        if is_static[k]:
            ax[k] = 0.0; ay[k] = 0.0; az[k] = 0.0
            continue
        ax[k] = (1 - 2 * (qy * qy + qz * qz)) * a0 + 2 * (qx * qy - qw * qz) * a1 + 2 * (qx * qz + qw * qy) * a2
        ay[k] = 2 * (qx * qy + qw * qz) * a0 + (1 - 2 * (qx * qx + qz * qz)) * a1 + 2 * (qy * qz - qw * qx) * a2
        az[k] = 2 * (qx * qz - qw * qy) * a0 + 2 * (qy * qz + qw * qx) * a1 + (1 - 2 * (qx * qx + qy * qy)) * a2 - gmag

    # ---- velocity (gyro buffers reused) -------------------------------------------------------
    VX, VY, VZ = gx, gy, gz
    tmp = array("f", bytes(4 * n))
    # motion segments between static intervals
    segs = []
    prev_end = 0
    for i0, i1 in ivs:
        if i0 > prev_end:
            segs.append((prev_end, i0, prev_end > 0, True))
        prev_end = i1
    if prev_end < nf:
        segs.append((prev_end, nf, bool(ivs), False))
    if not ivs:
        segs = [(0, nf, False, False)]
    for A, V in ((ax, VX), (ay, VY), (az, VZ)):
        for k in range(nf):
            V[k] = 0.0
        for lo, hi, start_rest, end_rest in segs:
            if not start_rest and end_rest and lo == 0:
                # recorded before the first rest: integrate backwards from v = 0
                v = 0.0
                for k in range(hi - 1, lo - 1, -1):
                    V[k] = v
                    v -= 0.5 * (A[k] + A[k - 1 if k > 0 else 0]) * dts[k]
                continue
            v = 0.0
            for k in range(lo, hi):
                if k > lo:
                    v += 0.5 * (A[k] + A[k - 1]) * dts[k]
                V[k] = v
            if end_rest and prm["dedrift"] > 0 and hi - lo > 1:
                # rest at both ends: remove the linear drift so v(end) = 0
                t_lo, t_span = ts[lo], (ts[hi - 1] - ts[lo]) or 1
                v_end = V[hi - 1]
                for k in range(lo, hi):
                    V[k] -= v_end * (ts[k] - t_lo) / t_span
    tau_v = (prm["vel_tau_h"], prm["vel_tau_h"], prm["vel_tau_v"])
    for V, tv in zip((VX, VY, VZ), tau_v):
        highpass_inplace(V, tmp, dts, tv, 0, nf)
        for k in range(nf):
            if is_static[k]:
                V[k] = 0.0

    # ---- position (accel buffers reused) ---------------------------------------------------
    PX, PY, PZ = ax, ay, az
    tau_p = (prm["pos_tau_h"], prm["pos_tau_h"], prm["pos_tau_v"])
    for V, Pp, tp in zip((VX, VY, VZ), (PX, PY, PZ), tau_p):
        p = 0.0
        for k in range(nf):
            if k:
                p += 0.5 * (V[k] + V[k - 1]) * dts[k]
            Pp[k] = p
        highpass_inplace(Pp, tmp, dts, tp, 0, nf, keep_start=True)
    del tmp

    # ---- blind dead reckoning over the failure window -----------------------------------------
    if 0 < nf < n:
        m = min(nf, avg_n)
        vlx = sum(VX[nf - m:nf]) / m
        vly = sum(VY[nf - m:nf]) / m
        vlz = sum(VZ[nf - m:nf]) / m
        px, py, pz = PX[nf - 1], PY[nf - 1], PZ[nf - 1]
        qw, qx, qy, qz = QW[nf - 1], QX[nf - 1], QY[nf - 1], QZ[nf - 1]
        tv, tw = prm["blind_v_tau"], prm["blind_w_tau"]
        wx, wy, wz = last_w
        tb = 0.0
        for k in range(nf, n):
            dt = max(0.0, (ts[k] - ts[k - 1]) * 1e-9)
            tb += dt
            fv = math.exp(-tb / tv) if tv > 0 else 0.0
            fw = math.exp(-tb / tw) if tw > 0 else 0.0
            px += vlx * fv * dt; py += vly * fv * dt; pz += vlz * fv * dt
            qw, qx, qy, qz = _qmul_exp(qw, qx, qy, qz, wx * fw, wy * fw, wz * fw, dt)
            PX[k] = px; PY[k] = py; PZ[k] = pz
            QW[k] = qw; QX[k] = qx; QY[k] = qy; QZ[k] = qz
        stats["blind_start_velocity"] = [round(vlx, 3), round(vly, 3), round(vlz, 3)]
    return PX, PY, PZ, QW, QX, QY, QZ


# ----------------------------------------------------------------------------- output
def write_tum(path, ts, est):
    PX, PY, PZ, QW, QX, QY, QZ = est
    with open(path, "w", buffering=1 << 16) as f:
        f.write("# timestamp tx ty tz qx qy qz qw\n")
        w = f.write
        for k in range(len(ts)):
            sec, ns = divmod(ts[k], 1_000_000_000)
            qw, qx, qy, qz = QW[k], QX[k], QY[k], QZ[k]
            if qw < 0:
                qw, qx, qy, qz = -qw, -qx, -qy, -qz
            r = 1.0 / (math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz) or 1.0)
            w("%d.%09d %.6f %.6f %.6f %.7f %.7f %.7f %.7f\n" % (
                sec, ns, PX[k], PY[k], PZ[k], qx * r, qy * r, qz * r, qw * r))


USAGE = """usage: python main.py <imu.csv | dataset_dir | dataset.zip> [-o estimated_trajectory.txt]
                    [--meta metadata.json] [--profile] [--set key=value ...]"""


def _parse_args(argv):
    """Tiny argv parser (argparse alone costs ~0.5 MB of heap)."""
    a = {"input": None, "output": "estimated_trajectory.txt", "meta": None, "set": []}
    i = 0
    while i < len(argv):
        x = argv[i]
        if x in ("-h", "--help"):
            print(USAGE)
            sys.exit(0)
        if x in ("-o", "--output", "--meta"):
            a["output" if x != "--meta" else "meta"] = argv[i + 1]
            i += 2
            continue
        if x == "--profile":
            i += 1
            continue
        if x == "--set":
            i += 1
            while i < len(argv) and "=" in argv[i] and not argv[i].startswith("-"):
                a["set"].append(argv[i])
                i += 1
            continue
        if a["input"] is None:
            a["input"] = x
        i += 1
    if a["input"] is None:
        print(USAGE)
        sys.exit(2)
    return a


def main(argv=None):
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    prm = dict(P)
    for kv in args["set"]:
        k, v = kv.split("=")
        if k not in prm:
            raise SystemExit("unknown parameter " + k)
        prm[k] = float(v)

    t_start = time.perf_counter()
    c_start = time.process_time()
    ts, ch = read_imu(args["input"])
    stats = {}
    est = estimate(ts, ch, prm, stats)
    if est is None:
        print("no IMU rows found", file=sys.stderr)
        return 1
    write_tum(args["output"], ts, est)
    wall = time.perf_counter() - t_start
    cpu = time.process_time() - c_start
    dur = (ts[-1] - ts[0]) * 1e-9 if len(ts) > 1 else 0.0
    stats.update(runtime_wall_s=round(wall, 3), runtime_cpu_s=round(cpu, 3), imu_duration_s=round(dur, 3),
                 ms_per_imu_second=round(1000 * cpu / dur, 3) if dur > 0 else None, threads=1,
                 language="Python %d.%d, standard library only" % sys.version_info[:2], params=prm)
    if _PROFILE:
        stats["peak_traced_heap_MB"] = round(tracemalloc.get_traced_memory()[1] / 1e6, 3)
        stats["note"] = "runtime measured with tracemalloc on (slower); run without --profile for timing"
    if args["meta"]:
        import json                  # lazy
        with open(args["meta"], "w") as f:
            json.dump(stats, f, indent=2)
    print("rows=%d  duration=%.1fs  cpu=%.2fs (%.1f ms per IMU-second)%s -> %s" % (
        len(ts), dur, cpu, stats["ms_per_imu_second"] or 0,
        ("  peak_heap=%.2fMB" % stats["peak_traced_heap_MB"]) if _PROFILE else "", args["output"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
