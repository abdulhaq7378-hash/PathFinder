"""numpy prototype: error-state EKF with rotor-drag velocity measurement (not the submission)."""
import sys, json
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import proto
from proto import rot, lp

G0 = 9.80665


def skew(v):
    return np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])


def expq(phi):
    th = np.linalg.norm(phi)
    if th < 1e-12:
        return np.array([1.0, *(0.5 * phi)])
    return np.r_[np.cos(th / 2), np.sin(th / 2) * phi / th]


def run(path, prm):
    ts, w, a = proto.load_imu(path)
    n = len(ts)
    nf = n
    while nf > 0 and not np.any(w[nf - 1]) and not np.any(a[nf - 1]):
        nf -= 1
    t = ts * 1e-9
    dt = np.r_[0, np.diff(t)]; dt[dt < 0] = 0
    st = proto.static_mask(t[:nf], w[:nf], a[:nf], gstd=prm['gstd'], astd=prm['astd'])
    idx = np.flatnonzero(st)
    segs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1) if len(idx) else []
    if segs:
        bt = np.array([t[s].mean() for s in segs]); bv = np.array([w[s].mean(0) for s in segs])
        gmag = np.mean(np.linalg.norm(a[idx], axis=1)); k0 = segs[0][0]; a0 = a[segs[0]].mean(0)
        bg0 = bv[0]
    else:
        gmag = G0; k0 = 0; a0 = a[:100].mean(0); bg0 = np.zeros(3)
    mv = np.zeros(nf, bool); mv[:] = ~st
    nb = a[:nf][mv].mean(0); nb /= np.linalg.norm(nb)
    tmp = np.array([1.0, 0, 0]) if abs(nb[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(nb, tmp); e1 /= np.linalg.norm(e1); e2 = np.cross(nb, e1)
    E = np.stack([e1, e2], 1)  # 3x2
    mu = prm['mu']
    u = a0 / np.linalg.norm(a0); q = np.array([1 + u[2], u[1], -u[0], 0.0]); q /= np.linalg.norm(q)
    v = np.zeros(3); bg = bg0.copy(); ba = np.zeros(2)
    N = 11
    Pm = np.diag([1e-4] * 3 + [1e-4] * 3 + [1e-6] * 3 + [prm['ba0'] ** 2] * 2)
    Q = np.zeros((nf, 4)); V = np.zeros((nf, 3))
    upd = prm['upd']
    acc_f = np.zeros(3); acc_w = np.zeros(3); acc_t = 0.0; cnt = 0; stat_cnt = 0
    nis = []
    for k in range(k0, nf):
        d = dt[k] if k > k0 else 0.0
        if d > 0:
            wc = w[k] - bg
            fc = a[k] - (E @ ba if prm['ba_prop'] else 0)
            R = rot(q)
            v = v + (R @ fc - np.array([0, 0, gmag])) * d
            q = proto.qmul(q, expq(wc * d)); q /= np.linalg.norm(q)
            acc_f += a[k] * d; acc_w += wc * d; acc_t += d; cnt += 1; stat_cnt += st[k]
        Q[k] = q; V[k] = v
        if acc_t >= upd:
            fm = acc_f / acc_t; wm = acc_w / acc_t; T = acc_t
            R = rot(q)
            A = np.zeros((N, N))
            A[0:3, 0:3] = -skew(wm); A[0:3, 6:9] = -np.eye(3)
            A[3:6, 0:3] = -R @ skew(fm - (E @ ba if prm['ba_prop'] else 0)); A[3:6, 9:11] = -R @ E if prm['ba_prop'] else 0
            F = np.eye(N) + A * T
            Qd = np.diag([prm['sg'] ** 2] * 3 + [prm['sv'] ** 2] * 3 + [prm['sbg'] ** 2] * 3 + [prm['sba'] ** 2] * 2) * T
            Pm = F @ Pm @ F.T + Qd
            Hs = []; rs = []; Rs = []
            ub = R.T @ v
            if stat_cnt > 0.8 * cnt:
                # zero velocity + gravity tilt
                Hs.append(np.c_[np.zeros((3, 3)), np.eye(3), np.zeros((3, 5))]); rs.append(-v); Rs.append([prm['szupt'] ** 2] * 3)
                gb = R.T @ np.array([0, 0, gmag])
                H = np.zeros((3, N)); H[:, 0:3] = skew(gb); H[:, 9:11] = E if prm['ba_prop'] else 0
                Hs.append(H); rs.append(fm - (gb + (E @ ba if prm['ba_prop'] else 0))); Rs.append([prm['stilt'] ** 2] * 3)
            else:
                # rotor drag: e_i^T f = -mu e_i^T R^T v + ba_i
                H = np.zeros((2, N))
                H[:, 0:3] = -mu * E.T @ skew(ub)
                H[:, 3:6] = -mu * E.T @ R.T
                H[:, 9:11] = np.eye(2)
                z = E.T @ fm
                h = -mu * E.T @ ub + ba
                Hs.append(H); rs.append(z - h); Rs.append([prm['sdrag'] ** 2] * 2)
                if prm['svz'] > 0:
                    H = np.zeros((1, N)); H[0, 5] = 1
                    Hs.append(H); rs.append(np.array([-v[2]])); Rs.append([prm['svz'] ** 2])
            H = np.vstack(Hs); r = np.concatenate(rs); Rn = np.diag(np.concatenate(Rs))
            S = H @ Pm @ H.T + Rn
            K = Pm @ H.T @ np.linalg.inv(S)
            dx = K @ r
            nis.append(float(r @ np.linalg.solve(S, r)) / len(r))
            Pm = (np.eye(N) - K @ H) @ Pm
            Pm = 0.5 * (Pm + Pm.T)
            q = proto.qmul(q, expq(dx[0:3])); q /= np.linalg.norm(q)
            v = v + dx[3:6]; bg = bg + dx[6:9]; ba = ba + dx[9:11]
            acc_f[:] = 0; acc_w[:] = 0; acc_t = 0.0; cnt = 0; stat_cnt = 0
            Q[k] = q; V[k] = v
    # before k0: backward gyro integration, zero velocity
    qb = Q[k0].copy()
    for k in range(k0 - 1, -1, -1):
        qb = proto.qmul(qb, expq(-(w[k + 1] - bg0) * dt[k + 1])); qb /= np.linalg.norm(qb); Q[k] = qb
    # position
    vv = V.copy()
    for i in range(3):
        if prm['vel_tau'][i] > 0:
            vv[:, i] -= lp(vv[:, i], prm['vel_tau'][i], dt[:nf])
    p = np.cumsum(vv * dt[:nf, None], 0)
    for i in range(3):
        if prm['pos_tau'][i] > 0:
            p[:, i] -= lp(p[:, i], prm['pos_tau'][i], dt[:nf]) - p[0, i]
    P = np.zeros((n, 3)); QQ = np.zeros((n, 4)); P[:nf] = p; QQ[:nf] = Q
    m = int(prm['bavg'] / 0.005)
    vl = vv[nf - m:nf].mean(0) if nf < n else 0
    pp = p[nf - 1].copy(); tb = 0
    for k in range(nf, n):
        tb += dt[k]; pp = pp + vl * np.exp(-tb / prm['btau']) * dt[k]; P[k] = pp; QQ[k] = Q[nf - 1]
    return ts, P, QQ, dict(nis=float(np.mean(nis)), ba=ba.tolist(), bg=bg.tolist(), nb=nb.tolist()), st


DEF = dict(gstd=0.02, astd=0.15, mu=0.22, upd=0.1, sg=2e-3, sv=0.3, sbg=2e-4, sba=2e-3, ba0=0.3,
           szupt=0.02, stilt=0.05, sdrag=0.15, svz=0.5, ba_prop=False, vel_tau=[0, 0, 0], pos_tau=[0, 0, 0], bavg=0.5, btau=3.0)

if __name__ == '__main__':
    prm = dict(DEF); prm.update(json.loads(sys.argv[3]) if len(sys.argv) > 3 else {})
    ts, P, Q, info, st = run(sys.argv[1], prm)
    gt = np.loadtxt(sys.argv[2])
    print(json.dumps(info), proto.score(ts, P, gt))
    if len(sys.argv) > 4:
        np.savez(sys.argv[4], ts=ts, P=P, Q=Q)
