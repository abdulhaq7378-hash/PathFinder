#!/usr/bin/env python3
"""Run src/main.py on every test set and score it. usage: bench.py [key=value ...] [--sets a,b]"""
import json, os, subprocess, sys, tempfile
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from evaluate import score

def one(job):
    seq, var, sets = job
    out = tempfile.mktemp(suffix='.txt', dir='/tmp/claude-0')
    cmd = [sys.executable, os.path.join(ROOT, 'src', 'main.py'), os.path.join(ROOT, 'data', seq, var), '-o', out]
    if sets: cmd += ['--set'] + sets
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: return seq, var, {'error': r.stderr[-400:]}
    s = score(out, os.path.join(ROOT, 'data', seq, 'gt.tum')); os.remove(out)
    return seq, var, s

if __name__ == '__main__':
    sets = [a for a in sys.argv[1:] if '=' in a]
    seqs = sorted(d for d in os.listdir(os.path.join(ROOT, 'data')) if os.path.isfile(os.path.join(ROOT, 'data', d, 'gt.tum')))
    vars_ = ['clean', 'deg', 'deg_raw', 'deg_hard']
    jobs = [(s, v, sets) for s in seqs for v in vars_]
    with ProcessPoolExecutor(4) as ex: res = list(ex.map(one, jobs))
    tot = {'ate': [], 'blind': [], 'wp': [], 'base': []}
    for seq, var, s in res:
        if 'error' in s: print(seq, var, 'ERROR', s['error']); continue
        print(f"{seq:12s} {var:9s} ATE {s['ate_rmse']:7.3f}  wp {s['waypoint_mean']:7.3f}  blind5 {s['blind5_rmse']:7.3f}  rpe1s {s['rpe1s_rmse']:.3f}  (static-baseline {s['baseline_static_rmse']:.2f})")
        if var != 'clean':
            tot['ate'].append(s['ate_rmse']); tot['blind'].append(s['blind5_rmse']); tot['wp'].append(s['waypoint_mean']); tot['base'].append(s['baseline_static_rmse'])
    m = lambda x: sum(x) / len(x)
    print(f"MEAN(degraded) ATE {m(tot['ate']):.3f}  wp {m(tot['wp']):.3f}  blind5 {m(tot['blind']):.3f}  base {m(tot['base']):.3f}  ratio {m(tot['ate'])/m(tot['base']):.3f}")
