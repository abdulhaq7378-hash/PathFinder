"""numpy prototype for fast iteration (not the submission)."""
import sys, json
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluate import umeyama

G0 = 9.80665


def load_imu(p):
    a = np.loadtxt(p, delimiter=',', comments='#')
    return a[:, 0].astype(np.int64), a[:, 1:4].copy(), a[:, 4:7].copy()


def lp(x, tau, dt):
    y = np.array(x, float, copy=True)
    for i in range(1, len(y)):
        al = dt[i] / (tau + dt[i]); y[i] = y[i - 1] + al * (y[i] - y[i - 1])
    for i in range(len(y) - 2, -1, -1):
        al = dt[i + 1] / (tau + dt[i + 1]); y[i] = y[i + 1] + al * (y[i] - y[i + 1])
    return y


def static_mask(t, w, a, win=0.5, gstd=0.02, astd=0.15):
    n = len(t); dt = np.median(np.diff(t)); m = max(5, int(win / dt))
    cs = lambda x: np.concatenate([[0], np.cumsum(x)])
    def rstd(x):
        s1, s2 = cs(x), cs(x * x)
        mu = (s1[m:] - s1[:-m]) / m; v = (s2[m:] - s2[:-m]) / m - mu * mu
        return np.sqrt(np.maximum(v, 0))
    ws = np.max([rstd(w[:, i]) for i in range(3)], 0)
    an = np.linalg.norm(a, axis=1); as_ = rstd(an)
    ok = (ws < gstd) & (as_ < astd)
    mask = np.zeros(n, bool)
    for j in np.flatnonzero(ok):
        mask[j:j + m] = True
    return mask


def qmul(q, r):
    w0, x0, y0, z0 = q; w1, x1, y1, z1 = r
    return np.array([w0*w1-x0*x1-y0*y1-z0*z1, w0*x1+x0*w1+y0*z1-z0*y1, w0*y1-x0*z1+y0*w1+z0*x1, w0*z1+x0*y1-y0*x1+z0*w1])


def rot(q):
    w, x, y, z = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)], [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)], [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]])


def run(path, prm):
    ts, w, a = load_imu(path)
    n = len(ts)
    nf = n
    while nf > 0 and not np.any(w[nf - 1]) and not np.any(a[nf - 1]):
        nf -= 1
    t = ts * 1e-9
    dt = np.r_[0, np.diff(t)]; dt[dt < 0] = 0
    st = static_mask(t[:nf], w[:nf], a[:nf], gstd=prm['gstd'], astd=prm['astd'])
    # gyro bias: static segments, interpolated
    idx = np.flatnonzero(st)
    if len(idx) > 20:
        # segment means
        segs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
        bt = np.array([t[s].mean() for s in segs]); bv = np.array([w[s].mean(0) for s in segs])
        bias = np.stack([np.interp(t[:nf], bt, bv[:, i]) for i in range(3)], 1)
        gmag = np.mean(np.linalg.norm(a[idx], axis=1))
        a0 = a[segs[0]].mean(0)
        k0 = segs[0][0]
    else:
        bias = np.zeros((nf, 3)); gmag = G0; a0 = a[:100].mean(0); k0 = 0
    # mahony from k0 forward and backward
    def mahony(order, q0):
        q = q0.copy(); I = np.zeros(3); lpa = a[order[0]].copy(); Q = np.zeros((nf, 4)); prev = None
        for k in order:
            d = dt[k] if prev is None or k > prev else dt[prev]
            wk = w[k] - bias[k]
            if prev is not None and d > 0:
                al = d / (prm['tau_a'] + d); lpa += al * (a[k] - lpa)
                ln = np.linalg.norm(lpa); e = np.zeros(3)
                if abs(ln - gmag) < prm['gate']:
                    R = rot(q); v = R[2]; e = np.cross(lpa / ln, v); I += prm['ki'] * e * d
                sgn = 1.0 if k > prev else -1.0
                c = sgn * (wk + prm['kp'] * sgn * e + I * sgn)
                th = np.linalg.norm(c) * d
                if th > 0:
                    ax = c / np.linalg.norm(c); dq = np.r_[np.cos(th / 2), ax * np.sin(th / 2)]
                    q = qmul(q, dq); q /= np.linalg.norm(q)
            Q[k] = q; prev = k
        return Q
    u = a0 / np.linalg.norm(a0); q0 = np.array([1 + u[2], u[1], -u[0], 0.0]); q0 /= np.linalg.norm(q0)
    Qf = mahony(range(k0, nf), q0)
    if k0 > 0:
        Qb = mahony(range(k0, -1, -1), q0); Qf[:k0] = Qb[:k0]
    Rm = np.array([rot(q) for q in Qf])
    aw = np.einsum('nij,nj->ni', Rm, a[:nf]) - [0, 0, gmag]
    aw[st] = 0
    v = np.cumsum(aw * dt[:nf, None], 0)
    # ZUPT: reset in static, linear de-drift between statics
    v_raw = v.copy()
    if prm['zupt'] and len(idx) > 20:
        v = np.zeros_like(v_raw)
        # forward integrate segments starting at zero after each static
        cur = np.zeros(3)
        for k in range(nf):
            if st[k]:
                cur[:] = 0
            else:
                cur += aw[k] * dt[k]
            v[k] = cur
        # linear de-drift where a moving segment ends in static
        mv = ~st
        b = np.flatnonzero(np.diff(mv.astype(int)) != 0) + 1
        edges = np.r_[0, b, nf]
        for s, e in zip(edges[:-1], edges[1:]):
            if mv[s] and e < nf and s > 0:
                r = (t[s:e] - t[s]) / max(1e-6, t[e - 1] - t[s])
                v[s:e] -= r[:, None] * v[e - 1]
            elif mv[s] and s == 0 and e < nf:   # leading motion: integrate backward from 0
                vb = np.zeros(3)
                for k in range(e - 1, -1, -1):
                    v[k] = vb; vb = vb - aw[k] * dt[k + 1 if k + 1 < nf else k]
    # drag fusion
    info = {}
    if prm['drag']:
        mv = ~st
        nb = a[:nf][mv].mean(0); nb /= np.linalg.norm(nb)
        ap = a[:nf] - (a[:nf] @ nb)[:, None] * nb
        ap -= ap[mv].mean(0)
        vdw = np.einsum('nij,nj->ni', Rm, -ap)    # drag velocity / k
        # estimate k: d/dt(k*vdw) ~ aw   (band-pass both)
        L = lp(vdw, 0.3, dt[:nf]); dd = np.zeros_like(L); dd[1:] = np.diff(L, axis=0) / np.maximum(dt[1:nf, None], 1e-4)
        A = lp(aw, 0.3, dt[:nf])
        hp = lambda x: x - lp(x, 5.0, dt[:nf])
        X = hp(dd[mv][:, :2]).ravel() if False else (dd[:, :2] - lp(dd[:, :2], 5.0, dt[:nf]))[mv].ravel()
        Y = (A[:, :2] - lp(A[:, :2], 5.0, dt[:nf]))[mv].ravel()
        kd = float(X @ Y / (X @ X)); corr = float(np.corrcoef(X, Y)[0, 1])
        info.update(k_drag=kd, drag_corr=corr)
        if prm.get('k_fixed'):
            kd = prm['k_fixed']
        if corr > prm['drag_min_corr']:
            vd = kd * vdw
            tau = prm['drag_tau']
            for i in range(2):
                d = vd[:, i] - v[:, i]
                d[st] = 0 - v[st, i]
                v[:, i] = v[:, i] + lp(d, tau, dt[:nf])
    # remaining drift: high-pass
    for i in range(3):
        if prm['vel_tau'][i] > 0:
            v[:, i] -= lp(v[:, i], prm['vel_tau'][i], dt[:nf])
    p = np.cumsum(v * dt[:nf, None], 0)
    for i in range(3):
        if prm['pos_tau'][i] > 0:
            p[:, i] -= lp(p[:, i], prm['pos_tau'][i], dt[:nf]) - p[0, i]
    # blind
    P = np.zeros((n, 3)); Q = np.zeros((n, 4)); P[:nf] = p; Q[:nf] = Qf
    m = int(prm['bavg'] / 0.005)
    vl = v[nf - m:nf].mean(0) if nf < n else 0
    pp = p[nf - 1].copy(); tb = 0
    for k in range(nf, n):
        tb += dt[k]; pp = pp + vl * np.exp(-tb / prm['btau']) * dt[k]; P[k] = pp; Q[k] = Qf[nf - 1]
    return ts, P, Q, info, st


def score(ts, P, gt, nf_blind=5.0):
    tg = gt[:, 0]; t = ts * 1e-9
    j = np.clip(np.searchsorted(tg, t), 1, len(tg) - 1)
    jj = np.where(np.abs(t - tg[j - 1]) < np.abs(t - tg[j]), j - 1, j)
    ok = (np.abs(tg[jj] - t) < 0.006) & np.r_[True, np.diff(t) > 0]
    pe, pg, tt = P[ok], gt[jj[ok], 1:4], t[ok]
    R, tr = umeyama(pe, pg); pa = pe @ R.T + tr
    e = np.linalg.norm(pa - pg, axis=1); pre = tt < tt[-1] - nf_blind
    return dict(ate=float(np.sqrt((e**2).mean())), pre=float(np.sqrt((e[pre]**2).mean())),
                blind=float(np.sqrt((e[~pre]**2).mean())), base=float(np.sqrt(((pg - pg.mean(0))**2).sum(1).mean())))


DEF = dict(gstd=0.02, astd=0.15, tau_a=0.25, gate=0.8, kp=0.1, ki=0.002, zupt=True, drag=True, drag_min_corr=0.3,
           drag_tau=2.0, vel_tau=[0, 0, 5.0], pos_tau=[0, 0, 20.0], bavg=0.5, btau=3.0)

if __name__ == '__main__':
    prm = dict(DEF); prm.update(json.loads(sys.argv[3]) if len(sys.argv) > 3 else {})
    ts, P, Q, info, st = run(sys.argv[1], prm)
    gt = np.loadtxt(sys.argv[2])
    print(info, 'static_frac', round(st.mean(), 3), score(ts, P, gt))
