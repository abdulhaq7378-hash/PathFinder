# src: PathFinder estimator

Standalone, **Python ≥ 3.8, standard library only**. Single thread, offline.

## Run

```bash
python main.py <imu0/data.csv | dataset_folder | dataset.zip> -o estimated_trajectory.txt
```

| Option | Meaning |
|---|---|
| `-o FILE` | output trajectory (default `estimated_trajectory.txt`) |
| `--meta FILE` | write run statistics json: runtime, detected gaps, failure window, static intervals, gyro bias, parameters |
| `--profile` | measure peak traced heap with `tracemalloc` (adds overhead, so do not use for timing) |
| `--set k=v ...` | override tuning parameters (see dict `P` at the top of `main.py`) |

## Input

EuRoC MAV `imu0/data.csv`:

```
#timestamp [ns],w_RS_S_x [rad s^-1],w_RS_S_y [rad s^-1],w_RS_S_z [rad s^-1],a_RS_S_x [m s^-2],a_RS_S_y [m s^-2],a_RS_S_z [m s^-2]
1403636579758555392,-0.0991,0.1473,0.0272,8.1477,-0.3759,-2.4026
```

These are detected automatically:
- gyro/accel column order
- accel in g
- gyro in deg/s
- s/ms/µs/ns stamps
- missing rows (dropouts)
- duplicated rows
- the all-zero dead-sensor tail

## Output

TUM format, space separated, exactly one pose per input row:

```
# timestamp tx ty tz qx qy qz qw
1403636579.758555392 0.000000 0.000000 0.000000 -0.1163427 -0.8060970 -0.0517267 0.5779241
```

## Measured (EuRoC MH_01 degraded, 184 s, 35 629 rows)

- CPU 0.33 s, i.e. **1.8 ms per IMU-second** (limit 20 ms)
- peak traced heap **2.45 MB** for the whole process including imports (limit 8 MB); 3.8 MB when reading straight from a zip
