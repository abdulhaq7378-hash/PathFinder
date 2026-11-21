import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, Img, staticFile } from "remotion";
import D0 from "../../public/pathfinder/mh01.json";
import { C, INTER, MONO, HAND, ease, usePop, GridBG, Photo, Kicker, Title, Note, MarkerLoop, Arrow, Chip, Counter, Card, bounds, toPath, seriesPath, IdeaTag } from "./ui";

const D: any = D0;
const fmt = (n: number, d = 1) => n.toFixed(d);

/** error over time on a log axis: naive (red) vs PathFinder (blue). `up` = 0..1 reveal */
export const ErrChart: React.FC<{ w: number; h: number; up: number; upEst?: number; showNaive?: boolean }> = ({ w, h, up, upEst = up, showNaive = true }) => {
  const lo = Math.log10(0.5), hi = Math.log10(700);
  const Y = (v: number) => h - ((Math.log10(Math.max(0.5, v)) - lo) / (hi - lo)) * h;
  const T = D.duration;
  const path = (t: number[], v: number[], u: number) => { let d = ""; for (let i = 0; i < t.length; i++) { if (t[i] > u * T) break; d += (i ? "L" : "M") + ((t[i] / T) * w).toFixed(1) + "," + Y(v[i]).toFixed(1); } return d; };
  return (
    <svg width={w} height={h} style={{ overflow: "visible" }}>
      {[1, 10, 100].map((v) => (
        <g key={v}>
          <line x1={0} x2={w} y1={Y(v)} y2={Y(v)} stroke={C.line} strokeWidth={1.5} strokeDasharray="6 8" />
          <text x={-14} y={Y(v) + 8} textAnchor="end" fill={C.mute} style={{ fontFamily: MONO, fontSize: 22 }}>{v} m</text>
        </g>
      ))}
      <text x={w} y={h + 40} textAnchor="end" fill={C.mute} style={{ fontFamily: MONO, fontSize: 20 }}>flight time →</text>
      {showNaive ? <path d={path(D.naive_t, D.naive_err, up)} fill="none" stroke={C.red} strokeWidth={5} strokeLinejoin="round" /> : null}
      <path d={path(D.t, D.err, upEst)} fill="none" stroke={C.blue} strokeWidth={5} strokeLinejoin="round" />
    </svg>
  );
};

/* ---------------- 01 HOOK ---------------- */
export const S01: React.FC = () => {
  const f = useCurrentFrame(); const { durationInFrames: N } = useVideoConfig();
  const split = Math.round(N * 0.5);
  const W = 1180, H = 860;
  const bGT = bounds([D.gt], 0.12); const bAll = bounds([D.gt, D.naive], 0.06);
  const z = f < split ? ease(f, 10, split - 10) : 1 - ease(f, split, split + 22);
  const b = { x0: interpolate(z, [0, 1], [bGT.x0, bAll.x0]), x1: interpolate(z, [0, 1], [bGT.x1, bAll.x1]), y0: interpolate(z, [0, 1], [bGT.y0, bAll.y0]), y1: interpolate(z, [0, 1], [bGT.y1, bAll.y1]) };
  const naiveUp = ease(f, 6, split - 12);
  const gt = toPath(D.gt, b, W, H, true, f < split ? naiveUp : 1);
  const nv = toPath(D.naive, b, W, H, true, naiveUp);
  const naiveOp = f < split ? 1 : 0.35;
  const shake = f > split - 14 && f < split ? Math.sin(f * 2.3) * 6 : 0;
  const mapOp = f < split ? 1 : 1 - ease(f, split, split + 12);
  const chOp = ease(f, split + 6, split + 18);
  return (
    <AbsoluteFill>
      <GridBG tint={f < split ? C.red : C.blue} />
      <div style={{ position: "absolute", left: 640, top: 110, width: W, height: H, transform: `translateX(${shake}px)`, opacity: mapOp }}>
        <svg width={W} height={H} style={{ overflow: "visible" }}>
          <path d={gt.d} fill="none" stroke={C.gt} strokeWidth={4} strokeLinejoin="round" opacity={0.85} />
          <path d={nv.d} fill="none" stroke={C.red} strokeWidth={5} strokeLinejoin="round" />
          <circle cx={nv.end[0]} cy={nv.end[1]} r={11} fill={C.red} />
        </svg>
      </div>
      {f >= split ? (
        <div style={{ position: "absolute", left: 800, top: 170, opacity: chOp }}>
          <div style={{ fontFamily: MONO, fontSize: 22, color: C.mute, marginBottom: 26, marginLeft: -10 }}>position error over the whole flight (log scale)</div>
          <ErrChart w={1000} h={640} up={ease(f, split + 10, split + 40)} upEst={ease(f, split + 30, N - 50)} />
        </div>
      ) : null}
      <div style={{ position: "absolute", left: 90, top: 150, width: 600 }}>
        <Kicker color={C.red}>textbook integration</Kicker>
        <div style={{ fontFamily: INTER, fontWeight: 800, fontSize: 150, color: C.red, letterSpacing: -4, lineHeight: 1, marginTop: 10, opacity: naiveOp }}>
          {Math.round(naiveUp * D.stats.naive_ate)}<span style={{ fontSize: 70 }}> m</span>
        </div>
        <div style={{ fontFamily: INTER, fontSize: 30, color: C.mute, marginTop: 6 }}>average error (ATE), drifting off the map</div>
        {f >= split + 10 ? (
          <div style={{ marginTop: 60 }}>
            <Kicker color={C.blue} delay={split + 10}>PathFinder, same data</Kicker>
            <Title size={150} delay={split + 14} style={{ color: C.blue, letterSpacing: -4 }}>{fmt(D.stats.ate)}<span style={{ fontSize: 70 }}> m</span></Title>
            <div style={{ fontFamily: INTER, fontSize: 30, color: C.mute, marginTop: 6, opacity: ease(f, split + 20, split + 30) }}>this flight, 3.6 m average over 12 runs</div>
            <div style={{ marginTop: 34 }}><Chip delay={split + 40} color={C.green}>2.5 MB of memory</Chip></div>
          </div>
        ) : null}
      </div>
      <div style={{ position: "absolute", right: 70, ...(f < split ? { bottom: 150 } : { top: 110 }), display: "flex", gap: 26, fontFamily: INTER, fontSize: 24, color: C.mute }}>
        {f < split ? <span><b style={{ color: C.gt }}>━</b> real flight (ground truth)</span> : null}
        <span><b style={{ color: C.red }}>━</b> naive</span>
        {f > split ? <span><b style={{ color: C.blue }}>━</b> PathFinder</span> : null}
      </div>
      {f > split + 60 ? <Note x={1400} y={455} delay={split + 60} color={C.yellow}>same jammed IMU!</Note> : null}
    </AbsoluteFill>
  );
};

/* ---------------- 02 TITLE ---------------- */
export const S02: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Photo src="pathfinder/drone_indoor.jpg" dim={0.5} shift={420} />
      <div style={{ position: "absolute", left: 110, top: 250 }}>
        <Kicker>Samsung PRISM XR Hackathon 2026, Track 3</Kicker>
        <Title size={170} delay={4} style={{ marginTop: 16, letterSpacing: -5 }}>PathFinder</Title>
        <div style={{ fontFamily: INTER, fontSize: 40, color: C.text, opacity: ease(f, 14, 26), marginTop: 10 }}>6-DoF trajectory from a jammed IMU</div>
        <div style={{ display: "flex", gap: 18, marginTop: 56 }}>
          <Chip delay={22}>Nadir Hussain</Chip>
          <Chip delay={27}>Abdul Haq</Chip>
        </div>
        <div style={{ fontFamily: INTER, fontWeight: 600, fontSize: 32, color: C.mute, marginTop: 26, opacity: ease(f, 32, 44) }}>Manipal Institute of Technology</div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------------- 03 PROBLEM ---------------- */
export const S03: React.FC = () => {
  const f = useCurrentFrame(); const { durationInFrames: N } = useVideoConfig();
  const W = 1000, H = 430;
  const T = D.duration;
  const up = ease(f, 40, N * 0.75) * T;
  const clean = seriesPath(D.sig_clean_t, D.sig_clean, [0, T], [3, 17], W, H, up);
  const deg = seriesPath(D.sig_deg_t, D.sig_deg, [0, T], [3, 17], W, H, up);
  const failX = ((T - 5) / T) * W;
  const tags = [
    { t: 0.36, x: 1290, y: 330, txt: "noise keeps growing", c: C.yellow },
    { t: 0.46, x: 900, y: 790, txt: "spikes + missing rows", c: C.yellow },
    { t: 0.64, x: 1560, y: 820, txt: "last 5 s: dead", c: C.red },
  ];
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 0, top: 0, width: 760, height: 1080, overflow: "hidden" }}>
        <Photo src="pathfinder/aircraft_night.jpg" dim={0.35} />
      </div>
      <div style={{ position: "absolute", left: 760, top: 0, right: 0, bottom: 0 }}><GridBG /></div>
      <div style={{ position: "absolute", left: 80, top: 130, width: 600 }}>
        <Kicker color={C.red}>the mission</Kicker>
        <Title size={64} delay={4} style={{ marginTop: 12 }}>No GPS. Jammed. One sensor left.</Title>
        <div style={{ marginTop: 34, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}>
          <Chip color={C.red} delay={18}><span style={{ textDecoration: "line-through" }}>GPS</span></Chip>
          <Chip color={C.red} delay={24}><span style={{ textDecoration: "line-through" }}>camera</span></Chip>
          <Chip color={C.blue} delay={30}>IMU: gyro + accelerometer</Chip>
        </div>
      </div>
      <Card x={830} y={210} w={1010} h={560} delay={30} label="real IMU, EuRoC MH_01: |accel| [m/s²]">
        <svg width={W} height={H} style={{ position: "absolute", left: 5, top: 80, overflow: "visible" }}>
          <rect x={failX} y={-20} width={W - failX} height={H + 40} fill={C.red} opacity={ease(f, N * 0.62, N * 0.7) * 0.25} />
          {D.gaps.map((g: number[], i: number) => (
            <line key={i} x1={(g[0] / T) * W} x2={(g[0] / T) * W} y1={H - 20} y2={H + 10} stroke={C.yellow} strokeWidth={3} opacity={g[0] < up ? 0.9 : 0} />
          ))}
          <path d={clean} fill="none" stroke={C.gt} strokeWidth={1.4} opacity={0.35} />
          <path d={deg} fill="none" stroke={C.blue} strokeWidth={1.6} />
        </svg>
        <div style={{ position: "absolute", right: 24, top: 18, fontFamily: MONO, fontSize: 18, color: C.mute }}><span style={{ color: C.gt }}>grey</span> clean  <span style={{ color: C.blue }}>blue</span> what we get</div>
      </Card>
      {tags.map((g, i) => <Note key={i} x={g.x} y={g.y} color={g.c} size={40} delay={N * g.t} rot={i % 2 ? 2 : -3}>{g.txt}</Note>)}
      <div style={{ position: "absolute", left: 830, top: 900, fontFamily: INTER, fontSize: 36, fontWeight: 700, color: C.text, opacity: ease(f, N * 0.8, N * 0.88) }}>
        Goal: a full 6-DoF pose for <span style={{ color: C.blue }}>every single row</span>
      </div>
    </AbsoluteFill>
  );
};

/* ---------------- 04 DOUBLE INTEGRATION ---------------- */
export const S04: React.FC = () => {
  const f = useCurrentFrame(); const { durationInFrames: N } = useVideoConfig();
  const W = 860, H = 440;
  const up = ease(f, 30, N * 0.6);
  const t: number[] = [], v: number[] = [];
  for (let i = 0; i <= 180; i += 2) { t.push(i); v.push(0.5 * 0.1 * i * i); }
  const d = seriesPath(t, v, [0, 180], [0, 1700], W, H, up * 180);
  const box = (txt: string, c: string, delay: number) => {
    const p = usePop(delay);
    return <div style={{ padding: "22px 30px", borderRadius: 16, border: `2px solid ${c}`, background: `${c}18`, fontFamily: INTER, fontWeight: 800, fontSize: 46, color: C.text, opacity: p, transform: `scale(${0.8 + 0.2 * p})` }}>{txt}</div>;
  };
  const integ = (delay: number) => <div style={{ fontFamily: MONO, fontSize: 52, color: C.yellow, opacity: ease(f, delay, delay + 8) }}>∫ →</div>;
  return (
    <AbsoluteFill>
      <GridBG tint={C.red} />
      <div style={{ position: "absolute", left: 90, top: 90 }}>
        <Kicker color={C.yellow}>why it's hard</Kicker>
        <Title size={70} delay={3} style={{ marginTop: 10 }}>Double integration</Title>
      </div>
      <div style={{ position: "absolute", left: 90, top: 300, display: "flex", alignItems: "center", gap: 22 }}>
        {box("accel", C.blue, 8)}{integ(14)}{box("velocity", C.blue, 18)}{integ(24)}{box("position", C.blue, 28)}
      </div>
      <Card x={960} y={420} w={880} h={540} delay={20} label="position error from a 0.1 m/s² bias">
        <svg width={W} height={H} style={{ position: "absolute", left: 10, top: 70, overflow: "visible" }}>
          <path d={d} fill="none" stroke={C.red} strokeWidth={6} strokeLinecap="round" />
        </svg>
        <div style={{ position: "absolute", left: 30, bottom: 16, fontFamily: MONO, fontSize: 18, color: C.mute }}>0 s</div>
        <div style={{ position: "absolute", right: 30, bottom: 16, fontFamily: MONO, fontSize: 18, color: C.mute }}>180 s</div>
        <div style={{ position: "absolute", left: 40, top: 70, fontFamily: INTER, fontWeight: 800, fontSize: 84, color: C.red }}>
          <Counter to={1.62} start={30} dur={N * 0.6 - 30} decimals={2} suffix=" km" />
        </div>
      </Card>
      <Note x={110} y={500} delay={N * 0.25} size={46}>a tiny bias...</Note>
      <Arrow x1={420} y1={560} x2={950} y2={700} delay={N * 0.3} />
      <div style={{ position: "absolute", left: 90, top: 700, width: 780, opacity: ease(f, N * 0.62, N * 0.7), transform: `translateY(${(1 - ease(f, N * 0.62, N * 0.7)) * 20}px)` }}>
        <div style={{ fontFamily: INTER, fontWeight: 700, fontSize: 44, color: C.text, lineHeight: 1.25 }}>1° of tilt error</div>
        <div style={{ fontFamily: INTER, fontSize: 36, color: C.mute, marginTop: 8 }}>leaks <span style={{ color: C.red, fontWeight: 700 }}>0.17 m/s²</span> of gravity into position</div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------------- 05 MEMORY BUDGET ---------------- */
export const S05: React.FC = () => {
  const f = useCurrentFrame(); const { durationInFrames: N } = useVideoConfig();
  const BW = 1300;
  const np = ease(f, N * 0.25, N * 0.45);
  const pf = ease(f, N * 0.62, N * 0.8) * (2.49 / 8);
  const strike = ease(f, N * 0.5, N * 0.56);
  const bar = (y: number, frac: number, color: string, label: string, val: string, op = 1) => (
    <div style={{ position: "absolute", left: 300, top: y, opacity: op }}>
      <div style={{ fontFamily: MONO, fontSize: 28, color: C.mute, marginBottom: 12 }}>{label}</div>
      <div style={{ width: BW, height: 96, borderRadius: 16, border: `2px solid ${C.line}`, background: C.panel, position: "relative", overflow: "hidden" }}>
        <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: BW * frac, background: color, opacity: 0.85 }} />
        <div style={{ position: "absolute", right: 24, top: 22, fontFamily: INTER, fontWeight: 800, fontSize: 44, color: C.text }}>{val}</div>
      </div>
    </div>
  );
  return (
    <AbsoluteFill>
      <GridBG />
      <div style={{ position: "absolute", left: 300, top: 110 }}>
        <Kicker color={C.yellow}>the budget</Kicker>
        <Title size={84} delay={3} style={{ marginTop: 10 }}>8 MB of memory. Total.</Title>
      </div>
      {bar(360, np, C.red, "$ python -c \"import numpy\"", np > 0.98 ? "≈ 8 MB, all of it" : "", 1 - strike * 0.55)}
      <svg style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080 }}>
        <line x1={280} y1={450} x2={280 + (BW + 40) * strike} y2={420} stroke={C.yellow} strokeWidth={7} strokeLinecap="round" />
      </svg>
      {bar(620, pf, C.blue, "PathFinder, whole process (tracemalloc)", pf > 0.3 ? "2.49 MB" : "")}
      <div style={{ position: "absolute", left: 300 + BW * (2.49 / 8) + 20, top: 820, opacity: ease(f, N * 0.8, N * 0.88) }}>
        <Note x={0} y={0} delay={N * 0.8} color={C.green} size={48} rot={-2}>plain Python. zero imports that cost memory</Note>
      </div>
    </AbsoluteFill>
  );
};

/* ---------------- 06 IDEA 1: REST DETECTION ---------------- */
export const S06: React.FC = () => {
  const f = useCurrentFrame(); const { durationInFrames: N } = useVideoConfig();
  const W = 1700, H = 330; const T = D.fail_t; const t0 = 0, t1 = 70;
  const up = ease(f, 20, N * 0.5) * t1;
  const g = seriesPath(D.gyro_t, D.gyro_mag, [t0, t1], [0, 1.6], W, H, up);
  return (
    <AbsoluteFill>
      <GridBG />
      <IdeaTag n={1} label="Find every stop" />
      <Card x={110} y={190} w={1700} h={430} delay={6} label="gyro magnitude [rad/s], first 70 s">
        <svg width={W} height={H} style={{ position: "absolute", left: 0, top: 70, overflow: "visible" }}>
          {D.rest.filter((r: number[]) => r[0] < t1).map((r: number[], i: number) => (
            <rect key={i} x={(r[0] / t1) * W} y={-10} width={((Math.min(r[1], t1) - r[0]) / t1) * W} height={H + 20} fill={C.green} opacity={ease(f, N * 0.4 + i * 6, N * 0.48 + i * 6) * 0.22} />
          ))}
          <path d={g} fill="none" stroke={C.blue} strokeWidth={2} />
        </svg>
      </Card>
      <Note x={(D.rest[0][0] / t1) * W + 150} y={150} delay={N * 0.45} color={C.green} size={44}>still! gyro should read 0</Note>
      <Card x={110} y={660} w={1000} h={300} delay={N * 0.55} label="so whatever it reads = bias  [rad/s]">
        <div style={{ position: "absolute", left: 40, top: 80, fontFamily: MONO, fontSize: 34, color: C.text, lineHeight: 1.7 }}>
          <div><span style={{ color: C.mute }}>PathFinder  </span><span style={{ color: C.blue }}>(-0.003, 0.021, 0.080)</span></div>
          <div><span style={{ color: C.mute }}>EuRoC ref.  </span><span style={{ color: C.gt }}>(-0.002, 0.025, 0.082)</span></div>
        </div>
      </Card>
      <div style={{ position: "absolute", left: 1170, top: 700, width: 640, fontFamily: INTER, fontSize: 38, fontWeight: 600, color: C.text, lineHeight: 1.3, opacity: ease(f, N * 0.72, N * 0.8) }}>
        Measured at <span style={{ color: C.green }}>every</span> stop, then followed over time as it drifts.
      </div>
    </AbsoluteFill>
  );
};

/* ---------------- 07 IDEA 2: ATTITUDE ---------------- */
export const S07: React.FC = () => {
  const f = useCurrentFrame(); const { durationInFrames: N } = useVideoConfig();
  const W = 1000, H = 300; const T = D.fail_t;
  const up = ease(f, 18, N * 0.7) * T;
  const p = seriesPath(D.tilt_t, D.tilt, [0, T], [0, 6], W, H, up);
  const medY = H - (D.stats.tilt_median / 6) * H;
  const dial = ease(f, N * 0.3, N * 0.45);
  const trust = (lbl: string, frac: number, c: string, delay: number) => (
    <div style={{ opacity: ease(f, delay, delay + 8) }}>
      <div style={{ fontFamily: INTER, fontWeight: 600, fontSize: 32, color: C.text, marginBottom: 10 }}>{lbl}</div>
      <div style={{ width: 560, height: 30, borderRadius: 999, background: C.panel, border: `2px solid ${C.line}` }}>
        <div style={{ width: 556 * frac * ease(f, delay, delay + 16), height: 26, borderRadius: 999, background: c }} />
      </div>
    </div>
  );
  return (
    <AbsoluteFill>
      <GridBG />
      <IdeaTag n={2} label="Mahony filter: gyro + gravity" />
      <div style={{ position: "absolute", left: 110, top: 230, display: "flex", flexDirection: "column", gap: 44 }}>
        <div style={{ fontFamily: INTER, fontWeight: 800, fontSize: 52, color: C.text, opacity: ease(f, 6, 16) }}>How much do we trust gravity?</div>
        {trust("at rest", 1, C.green, N * 0.3)}
        {trust("in flight", 0.15, C.yellow, N * 0.42)}
      </div>
      <Card x={760} y={540} w={1060} h={380} delay={N * 0.4} label="tilt error vs ground truth [deg]">
        <svg width={W} height={H} style={{ position: "absolute", left: 30, top: 60, overflow: "visible" }}>
          <path d={p} fill="none" stroke={C.blue} strokeWidth={2.2} />
          <line x1={0} x2={W} y1={medY} y2={medY} stroke={C.green} strokeWidth={3} strokeDasharray="10 8" opacity={ease(f, N * 0.75, N * 0.82)} />
        </svg>
      </Card>
      <div style={{ position: "absolute", left: 1180, top: 300, textAlign: "left", opacity: ease(f, N * 0.75, N * 0.85) }}>
        <div style={{ fontFamily: INTER, fontWeight: 800, fontSize: 130, color: C.green, letterSpacing: -3 }}>≈1°</div>
        <div style={{ fontFamily: INTER, fontSize: 32, color: C.mute }}>median tilt error ({fmt(D.stats.tilt_median, 2)}°)</div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------------- 08 IDEA 3: VELOCITY ---------------- */
export const S08: React.FC = () => {
  const f = useCurrentFrame(); const { durationInFrames: N } = useVideoConfig();
  const W = 1640, H = 520; const T = D.fail_t;
  const up = ease(f, 14, N * 0.55) * T;
  const nv = seriesPath(D.spd_naive_t, D.spd_naive, [0, T], [0, 5.5], W, H, up);
  const gt = seriesPath(D.spd_t, D.spd_gt, [0, T], [0, 5.5], W, H, up);
  const est = seriesPath(D.spd_t, D.spd_est, [0, T], [0, 5.5], W, H, f > N * 0.45 ? ease(f, N * 0.45, N * 0.85) * T : 0);
  return (
    <AbsoluteFill>
      <GridBG />
      <IdeaTag n={3} label="Velocity resets at every stop" />
      <Card x={110} y={190} w={1700} h={640} delay={4} label="speed [m/s]">
        <svg width={W} height={H} style={{ position: "absolute", left: 30, top: 80, overflow: "visible" }}>
          {D.rest.map((r: number[], i: number) => (
            <rect key={i} x={(r[0] / T) * W} y={-10} width={((r[1] - r[0]) / T) * W} height={H + 20} fill={C.green} opacity={0.18} />
          ))}
          <path d={gt} fill="none" stroke={C.gt} strokeWidth={3} opacity={0.8} />
          <path d={nv} fill="none" stroke={C.red} strokeWidth={3.5} />
          <path d={est} fill="none" stroke={C.blue} strokeWidth={4} />
        </svg>
        <div style={{ position: "absolute", right: 30, top: 18, display: "flex", gap: 26, fontFamily: INTER, fontSize: 24, color: C.mute }}>
          <span><b style={{ color: C.gt }}>━</b> truth</span><span><b style={{ color: C.red }}>━</b> naive</span><span><b style={{ color: C.blue }}>━</b> PathFinder</span>
        </div>
      </Card>
      <Note x={1180} y={260} delay={N * 0.35} color={C.red} size={44}>naive keeps speeding up</Note>
      <Note x={250} y={250} delay={N * 0.5} color={C.green} size={44} rot={2}>stop = speed 0, reset</Note>
      <div style={{ position: "absolute", left: 110, top: 880, display: "flex", gap: 20 }}>
        <Chip delay={N * 0.7} color={C.green}>remove drift between stops</Chip>
        <Chip delay={N * 0.78}>offline: smooth forward + backward</Chip>
      </div>
    </AbsoluteFill>
  );
};

/* ---------------- 09 IDEA 4: BLIND 5 s ---------------- */
export const S09: React.FC = () => {
  const f = useCurrentFrame(); const { durationInFrames: N } = useVideoConfig();
  const W = 900, H = 230;
  const tt: number[] = D.tail_t; const t0 = tt[0], t1 = tt[tt.length - 1];
  const up = t0 + ease(f, 8, N * 0.45) * (t1 - t0);
  const sig = seriesPath(tt, D.tail_a, [t0, t1], [0, 16], W, H, up);
  const failX = ((t1 - 5 - t0) / (t1 - t0)) * W;
  const inBlind = up > t1 - 5;
  const rows: string[] = D.blind_rows;
  const shown = inBlind ? Math.floor(ease(f, N * 0.42, N * 0.95) * rows.length) : 0;
  return (
    <AbsoluteFill>
      <GridBG tint={inBlind ? C.red : undefined} />
      <IdeaTag n={4} label="The blind 5 seconds" />
      <Card x={110} y={190} w={960} h={340} delay={4} label="|accel| in the last 16 s [m/s²]">
        <svg width={W} height={H} style={{ position: "absolute", left: 30, top: 80, overflow: "visible" }}>
          <rect x={failX} y={-10} width={W - failX} height={H + 20} fill={C.red} opacity={inBlind ? 0.22 : 0} />
          <path d={sig} fill="none" stroke={C.blue} strokeWidth={2} />
        </svg>
      </Card>
      <Card x={110} y={560} w={960} h={400} delay={N * 0.4} label="estimated_trajectory.txt, still writing">
        <div style={{ position: "absolute", left: 26, top: 64, right: 20, bottom: 14, overflow: "hidden", fontFamily: MONO, fontSize: 19, lineHeight: 1.62, color: C.gt }}>
          {rows.slice(Math.max(0, shown - 10), shown).map((r, i, a) => <div key={r} style={{ whiteSpace: "nowrap", color: i === a.length - 1 ? C.blue : C.gt }}>{r}</div>)}
        </div>
      </Card>
      <div style={{ position: "absolute", left: 1150, top: 230, width: 680 }}>
        <div style={{ display: "inline-block", padding: "14px 26px", borderRadius: 12, background: C.red, color: "#fff", fontFamily: MONO, fontWeight: 600, fontSize: 40, opacity: inBlind ? (Math.floor(f / 8) % 2 ? 1 : 0.75) : 0.12 }}>IMU DEAD</div>
        <div style={{ fontFamily: INTER, fontSize: 40, color: C.text, lineHeight: 1.35, marginTop: 40, opacity: ease(f, N * 0.35, N * 0.45) }}>
          Coast on the last <b style={{ color: C.blue }}>velocity</b> and <b style={{ color: C.blue }}>turn rate</b> we trust, and let both fade out.
        </div>
        <div style={{ marginTop: 50, opacity: ease(f, N * 0.65, N * 0.75) }}>
          <div style={{ fontFamily: INTER, fontWeight: 800, fontSize: 110, color: C.text, letterSpacing: -3 }}><Counter to={D.blind_count} start={N * 0.65} dur={N * 0.2} /></div>
          <div style={{ fontFamily: INTER, fontSize: 32, color: C.mute }}>poses still written, one per timestamp</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------------- 10 RESULTS ---------------- */
export const S10: React.FC = () => {
  const f = useCurrentFrame(); const { durationInFrames: N } = useVideoConfig();
  const up = ease(f, 10, N * 0.55);
  const rows = [["Full flight, 184 s", "4.29", "3.74", "4.48"], ["0 to 120 s", "4.56", "4.48", "2.18"], ["60 to 150 s, mid-flight start", "2.13", "1.84", "2.91"], ["45 s to end, mid-flight start", "3.54", "2.50", "6.52"]];
  return (
    <AbsoluteFill>
      <GridBG tint={C.blue} />
      <Card x={90} y={150} w={900} h={820} delay={2} label="EuRoC MH_01, organiser degradation: error [m], log scale">
        <div style={{ position: "absolute", left: 110, top: 110 }}><ErrChart w={740} h={560} up={up} upEst={up} /></div>
        <div style={{ position: "absolute", left: 40, bottom: 26, display: "flex", gap: 26, fontFamily: INTER, fontSize: 24, color: C.mute }}>
          <span><b style={{ color: C.red }}>━</b> naive: 210 m ATE</span><span><b style={{ color: C.blue }}>━</b> PathFinder: 4.29 m ATE</span>
        </div>
      </Card>
      <div style={{ position: "absolute", left: 1050, top: 160, width: 790 }}>
        <Kicker>results, error in metres</Kicker>
        <div style={{ marginTop: 20, fontFamily: INTER, fontSize: 26 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 110px 110px 110px", color: C.mute, fontFamily: MONO, fontSize: 20, paddingBottom: 10, borderBottom: `1.5px solid ${C.line}` }}>
            <span>test</span><span>ATE</span><span>waypts</span><span>blind 5 s</span>
          </div>
          {rows.map((r, i) => (
            <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 110px 110px 110px", padding: "14px 0", color: C.text, borderBottom: `1px solid ${C.line}`, opacity: ease(f, 14 + i * 7, 24 + i * 7) }}>
              <span>{r[0]}</span><span>{r[1]}</span><span>{r[2]}</span><span>{r[3]}</span>
            </div>
          ))}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 110px 110px 110px", padding: "16px 0", color: C.blue, fontWeight: 800, fontSize: 32, opacity: ease(f, N * 0.35, N * 0.42) }}>
            <span>mean of 12 runs</span><span>3.62</span><span>3.14</span><span>3.68</span>
          </div>
        </div>
        <div style={{ marginTop: 40, padding: "26px 30px", borderRadius: 16, background: `${C.yellow}14`, border: `2px solid ${C.yellow}66`, opacity: ease(f, N * 0.62, N * 0.72) }}>
          <div style={{ fontFamily: HAND, fontWeight: 700, fontSize: 46, color: C.yellow }}>being honest:</div>
          <div style={{ fontFamily: INTER, fontSize: 30, color: C.text, lineHeight: 1.35, marginTop: 6 }}>an IMU alone can't see slow drift over minutes. We stop it from exploding: 4.3 m instead of 210 m.</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------------- 11 EFFICIENCY ---------------- */
export const S11: React.FC = () => {
  const { durationInFrames: N } = useVideoConfig();
  const tile = (x: number, delay: number, big: React.ReactNode, lbl: string, sub: string, c: string) => {
    const p = usePop(delay, 13);
    return (
      <div style={{ position: "absolute", left: x, top: 330, width: 400, height: 420, borderRadius: 24, background: C.panel, border: `2px solid ${c}55`, padding: 36, opacity: p, transform: `translateY(${(1 - p) * 60}px)` }}>
        <div style={{ fontFamily: INTER, fontWeight: 800, fontSize: 104, color: c, letterSpacing: -3, lineHeight: 1 }}>{big}</div>
        <div style={{ fontFamily: INTER, fontWeight: 700, fontSize: 34, color: C.text, marginTop: 26 }}>{lbl}</div>
        <div style={{ fontFamily: MONO, fontSize: 22, color: C.mute, marginTop: 12 }}>{sub}</div>
      </div>
    );
  };
  return (
    <AbsoluteFill>
      <GridBG tint={C.green} />
      <div style={{ position: "absolute", left: 110, top: 120 }}>
        <Kicker color={C.green}>efficiency</Kicker>
        <Title size={80} delay={3} style={{ marginTop: 10 }}>Light and fast</Title>
      </div>
      {tile(110, 6, <Counter to={2.45} start={6} dur={30} decimals={2} />, "MB peak memory", "limit 8 MB", C.green)}
      {tile(550, N * 0.22, <Counter to={1.8} start={N * 0.22} dur={30} decimals={1} />, "ms per IMU-second", "limit 20 ms: 11x headroom", C.blue)}
      {tile(990, N * 0.5, "1", "CPU thread", "single-threaded, offline", C.yellow)}
      {tile(1430, N * 0.62, "0", "dependencies", "Python standard library", C.gt)}
    </AbsoluteFill>
  );
};

/* ---------------- 12 RUN IT ---------------- */
export const S12: React.FC = () => {
  const f = useCurrentFrame(); const { durationInFrames: N } = useVideoConfig();
  const cmd = "python src/main.py MH01_degraded.zip -o estimated_trajectory.txt --meta metadata.json";
  const typed = Math.floor(interpolate(f, [10, 10 + cmd.length * 0.9], [0, cmd.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const outT = 10 + cmd.length * 0.9 + 12;
  const lines = [
    "rows=35629  duration=184.1s  cpu=0.33s (1.8 ms per IMU-second)",
    "  -> estimated_trajectory.txt",
    "",
    "metadata.json",
    '  "dropout_gaps": 774,      "duplicate_stamps": 49,',
    '  "spikes_fixed": 340,      "static_intervals": 3,',
    '  "failure_seconds": 5.005, "gravity": 9.7798',
  ];
  return (
    <AbsoluteFill>
      <GridBG />
      <div style={{ position: "absolute", left: 110, top: 100 }}>
        <Kicker>run it</Kicker>
        <Title size={72} delay={2} style={{ marginTop: 10 }}>One line. Nothing to install.</Title>
      </div>
      <Card x={110} y={300} w={1700} h={640} delay={4}>
        <div style={{ height: 52, background: "#0d1424", display: "flex", alignItems: "center", gap: 12, paddingLeft: 22 }}>
          {["#ff5f57", "#febc2e", "#28c840"].map((c) => <div key={c} style={{ width: 16, height: 16, borderRadius: 99, background: c }} />)}
          <div style={{ marginLeft: 20, fontFamily: MONO, fontSize: 20, color: C.mute }}>PathFinder</div>
        </div>
        <div style={{ padding: "34px 40px", fontFamily: MONO, fontSize: 30, lineHeight: 1.6, color: C.text }}>
          <div><span style={{ color: C.green }}>$ </span>{cmd.slice(0, typed)}{typed < cmd.length && Math.floor(f / 8) % 2 ? <span style={{ background: C.text }}>&nbsp;</span> : null}</div>
          {lines.map((l, i) => (
            <div key={i} style={{ color: i === 3 ? C.yellow : i > 3 ? C.gt : C.blue, opacity: f > outT + i * 5 ? 1 : 0, whiteSpace: "pre" }}>{l || " "}</div>
          ))}
        </div>
      </Card>
      <Note x={1260} y={760} delay={N * 0.75} color={C.yellow} size={42}>csv, folder or zip</Note>
    </AbsoluteFill>
  );
};

/* ---------------- 13 OUTRO ---------------- */
export const S13: React.FC = () => {
  const f = useCurrentFrame(); const { durationInFrames: N } = useVideoConfig();
  const sw = f > N * 0.42;
  return (
    <AbsoluteFill>
      <Photo src="pathfinder/pcb.jpg" dim={0.72} />
      {!sw ? (
        <div style={{ position: "absolute", left: 110, top: 260, width: 1300 }}>
          <Kicker color={C.yellow}>what we tried and dropped</Kicker>
          <Title size={70} delay={3} style={{ marginTop: 14 }}>Rotor-drag physics model</Title>
          <div style={{ fontFamily: INTER, fontSize: 38, color: C.text, marginTop: 26, lineHeight: 1.4, opacity: ease(f, 12, 22) }}>
            On MH_01 the drag signal is buried under rotor vibration: it explains at most <span style={{ color: C.red, fontWeight: 700 }}>6%</span> of the sideways acceleration, even with ideal calibration. Documented in the repo, left out of the submission.
          </div>
        </div>
      ) : (
        <div style={{ position: "absolute", left: 110, top: 250 }}>
          <Kicker delay={N * 0.42}>everything is open</Kicker>
          <div style={{ fontFamily: MONO, fontWeight: 600, fontSize: 64, color: C.text, marginTop: 20, opacity: ease(f, N * 0.44, N * 0.52) }}>github.com/abdulhaq7378-hash/PathFinder</div>
          <div style={{ display: "flex", gap: 18, marginTop: 50 }}>
            <Chip delay={N * 0.55}>Nadir Hussain</Chip><Chip delay={N * 0.58}>Abdul Haq</Chip><Chip delay={N * 0.61} color={C.gt}>Manipal Institute of Technology</Chip>
          </div>
          <Title size={120} delay={N * 0.72} style={{ marginTop: 90, letterSpacing: -4 }}>Thanks for watching</Title>
        </div>
      )}
    </AbsoluteFill>
  );
};

export const SCENES: Record<string, React.FC> = { "01": S01, "02": S02, "03": S03, "04": S04, "05": S05, "06": S06, "07": S07, "08": S08, "09": S09, "10": S10, "11": S11, "12": S12, "13": S13 };
