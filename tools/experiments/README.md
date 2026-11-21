Research prototypes (numpy) kept for transparency, not part of the submission:
- proto.py      Mahony + ZUPT + drift-suppression prototype, rotor-drag fusion variant
- ekf_proto.py  error-state EKF with rotor-drag velocity measurement (rejected, see main README)
- diag.py       attitude / position diagnostics vs ground truth
- sweep.sh      parameter grid search with tools/bench.py
- drag_check.py  checks how much of the sideways accel a rotor-drag model explains (usage: python drag_check.py <folder with deg/imu0/data.csv, est.txt, gt.tum>)
