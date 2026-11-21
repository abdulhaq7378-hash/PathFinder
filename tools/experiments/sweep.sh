#!/bin/bash
# coarse grid over drift-suppression constants; prints "ratio cfg"
cd "$(dirname "$0")/../.."
for vh in 0.5 1 1.5; do for ph in 2 3 5 8; do for pv in 2 5; do for kp in 0.15 0.5; do
  cfg="vel_tau_h=$vh pos_tau_h=$ph pos_tau_v=$pv vel_tau_v=1 kp=$kp ki=0.02"
  r=$(python3 tools/bench.py $cfg | tail -1)
  echo "$r :: $cfg"
done; done; done; done
