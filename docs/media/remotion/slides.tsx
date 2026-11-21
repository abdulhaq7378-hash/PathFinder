import React from "react";
import { AbsoluteFill } from "remotion";
import D0 from "../../public/pathfinder/mh01.json";
import { C, INTER, MONO, HAND, GridBG, Photo, bounds, toPath, seriesPath } from "./ui";
import { ErrChart } from "./scenes";

const D: any = D0;
export const SLIDE_COUNT = 10;

const Head: React.FC<{ k: string; t: string; color?: string }> = ({ k, t, color = C.blue }) => (
  <div style={{ position: "absolute", left: 100, top: 80 }}>
    <div style={{ fontFamily: MONO, fontSize: 24, letterSpacing: 3, color, textTransform: "uppercase" }}>{k}</div>
    <div style={{ fontFamily: INTER, fontWeight: 800, fontSize: 64, color: C.text, letterSpacing: -1.5, marginTop: 8 }}>{t}</div>
  </div>
);
const Foot: React.FC<{ n: number }> = ({ n }) => (
  <div style={{ position: "absolute", left: 100, right: 100, bottom: 40, display: "flex", justifyContent: "space-between", fontFamily: MONO, fontSize: 18, color: C.mute }}>
    <span>MIT_Team  |  Track 03  |  PathFinder</span><span>{n} / {SLIDE_COUNT}</span>
  </div>
);
const Box: React.FC<{ x: number; y: number; w: number; h: number; label?: string; children?: React.ReactNode; tint?: string }> = ({ x, y, w, h, label, children, tint }) => (
  <div style={{ position: "absolute", left: x, top: y, width: w, height: h, borderRadius: 18, background: tint ? `${tint}14` : C.panel, border: `1.5px solid ${tint ? tint + "66" : C.line}`, overflow: "hidden" }}>
    {label ? <div style={{ position: "absolute", left: 26, top: 20, fontFamily: MONO, fontSize: 19, color: C.mute, letterSpacing: 1 }}>{label}</div> : null}
    {children}
  </div>
);
const P: React.FC<{ children: React.ReactNode; size?: number; color?: string; style?: React.CSSProperties }> = ({ children, size = 28, color = C.text, style }) => (
  <div style={{ fontFamily: INTER, fontSize: size, color, lineHeight: 1.38, ...style }}>{children}</div>
);
const Stat: React.FC<{ v: string; l: string; c: string }> = ({ v, l, c }) => (
  <div><div style={{ fontFamily: INTER, fontWeight: 800, fontSize: 76, color: c, letterSpacing: -2, lineHeight: 1 }}>{v}</div><div style={{ fontFamily: INTER, fontSize: 24, color: C.mute, marginTop: 8 }}>{l}</div></div>
);
const Traj: React.FC<{ w: number; h: number; naive?: boolean }> = ({ w, h, naive }) => {
  const b = bounds(naive ? [D.gt, D.naive] : [D.gt], 0.08);
  return (
    <svg width={w} height={h}>
      <path d={toPath(D.gt, b, w, h).d} fill="none" stroke={C.gt} strokeWidth={3} />
      {naive ? <path d={toPath(D.naive, b, w, h).d} fill="none" stroke={C.red} strokeWidth={3.5} /> : null}
      <path d={toPath(D.est, b, w, h).d} fill="none" stroke={C.blue} strokeWidth={naive ? 3 : 4} />
    </svg>
  );
};

const S1 = () => (
  <AbsoluteFill>
    <Photo src="pathfinder/drone_indoor.jpg" dim={0.55} shift={460} />
    <div style={{ position: "absolute", left: 110, top: 150 }}>
      <div style={{ display: "inline-block", padding: "10px 22px", borderRadius: 10, background: C.blue, color: "#04101f", fontFamily: MONO, fontWeight: 600, fontSize: 30 }}>TRACK 03</div>
      <div style={{ fontFamily: MONO, fontSize: 26, letterSpacing: 3, color: C.mute, marginTop: 30 }}>SAMSUNG PRISM  XR HACKATHON 2026</div>
      <div style={{ fontFamily: INTER, fontWeight: 800, fontSize: 170, color: C.text, letterSpacing: -5, lineHeight: 1, marginTop: 14 }}>PathFinder</div>
      <P size={40} style={{ marginTop: 14 }}>Path Finder: Trajectory Estimation Under Sensor Degradation</P>
      <div style={{ marginTop: 70, display: "grid", gridTemplateColumns: "260px 1fr", rowGap: 18, fontFamily: INTER, fontSize: 30 }}>
        <span style={{ color: C.mute }}>Team name</span><span style={{ color: C.text, fontWeight: 700 }}>Team</span>
        <span style={{ color: C.mute }}>College</span><span style={{ color: C.text, fontWeight: 700 }}>Manipal Institute of Technology, Manipal</span>
        <span style={{ color: C.mute }}>Members</span><span style={{ color: C.text }}><b>Nadir Hussain</b>, Electronics and Instrumentation, 3rd year<br /><b>Abdul Haq</b>, Biomedical Engineering, 3rd year</span>
      </div>
    </div>
  </AbsoluteFill>
);

const S2 = () => (
  <AbsoluteFill>
    <GridBG />
    <div style={{ position: "absolute", right: 0, top: 0, width: 760, height: 1080, overflow: "hidden" }}><Photo src="pathfinder/aircraft_night.jpg" dim={0.25} /></div>
    <Head k="the problem" t="A jammed aircraft must fly blind" color={C.red} />
    <div style={{ position: "absolute", left: 100, top: 260, width: 1000, display: "flex", flexDirection: "column", gap: 26 }}>
      {[
        ["Only an IMU", "No GPS, camera or magnetometer. Waypoints and ground truth are hidden."],
        ["Degradation grows with time", "White noise, bias random walk, scale drift, spikes, stuck samples."],
        ["Rows go missing, then the sensor dies", "2 s dropouts, duplicated rows, and the last 5 s are unusable."],
        ["Strict budget", "8 MB peak RAM, 20 ms per 1 s of IMU, one CPU thread, offline."],
      ].map(([h, b], i) => (
        <div key={i} style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
          <div style={{ width: 52, height: 52, flex: "none", borderRadius: 14, background: `${C.red}26`, border: `2px solid ${C.red}88`, display: "grid", placeItems: "center", fontFamily: MONO, fontWeight: 600, fontSize: 24, color: C.text }}>{i + 1}</div>
          <div><P size={32} style={{ fontWeight: 700 }}>{h}</P><P size={26} color={C.mute}>{b}</P></div>
        </div>
      ))}
    </div>
    <Box x={100} y={810} w={1000} h={170} tint={C.yellow}>
      <P size={27} style={{ position: "absolute", left: 30, top: 28, right: 30 }}><b style={{ color: C.yellow }}>Why it is hard:</b> double integration turns a 0.1 m/s² bias into 1.6 km of error in 3 minutes, and 1° of tilt leaks 0.17 m/s² of gravity into position.</P>
    </Box>
    <Foot n={2} />
  </AbsoluteFill>
);

const S3 = () => (
  <AbsoluteFill>
    <GridBG tint={C.blue} />
    <Head k="solution" t="Estimate what the IMU can observe, bound the rest" />
    <div style={{ position: "absolute", left: 100, top: 250, display: "flex", gap: 60 }}>
      <Stat v="2.45 MB" l="peak memory (limit 8 MB)" c={C.green} />
      <Stat v="1.8 ms" l="per IMU-second (limit 20 ms)" c={C.blue} />
      <Stat v="1 : 1" l="one pose per IMU row" c={C.yellow} />
      <Stat v="0" l="dependencies, stdlib only" c={C.gt} />
    </div>
    {[
      ["Find every rest", "A variance detector finds every still period. Gyro bias is measured at each one and interpolated over time to follow drift."],
      ["Mahony attitude", "Gyro plus gravity: full trust in gravity at rest, light trust in flight, online bias learning, run forward and backward."],
      ["Velocity resets", "Zero-velocity updates at rest, linear de-drift between rests, zero-phase smoothing (the task is offline)."],
      ["Blind 5 s", "Dead reckoning from the last trusted velocity and turn rate, both decaying. A pose is still written for every row."],
    ].map(([h, b], i) => (
      <Box key={i} x={100 + (i % 2) * 870} y={470 + Math.floor(i / 2) * 250} w={840} h={220}>
        <div style={{ position: "absolute", left: 30, top: 28, right: 30 }}>
          <P size={32} style={{ fontWeight: 800 }}><span style={{ color: C.blue, fontFamily: MONO }}>0{i + 1}  </span>{h}</P>
          <P size={25} color={C.mute} style={{ marginTop: 10 }}>{b}</P>
        </div>
      </Box>
    ))}
    <Foot n={3} />
  </AbsoluteFill>
);

const S4 = () => {
  const st = [["Parse", "csv, folder or zip; units and column order detected"], ["Sanitise", "per-row dt across gaps, spike filter, duplicates, dead tail"], ["Rest detector", "sliding-window variance of gyro and |a|"], ["Bias + gravity", "per rest interval, interpolated in time"],
    ["Attitude", "Mahony filter, forward and backward"], ["Velocity", "ZUPT, de-drift, zero-phase drift suppression"], ["Position", "integrate plus zero-phase high-pass"], ["Blind 5 s", "decaying velocity and turn rate"]];
  return (
    <AbsoluteFill>
      <GridBG />
      <Head k="architecture" t="8-stage offline pipeline" />
      <div style={{ position: "absolute", left: 100, top: 230, fontFamily: MONO, fontSize: 24, color: C.mute }}>imu0/data.csv  →</div>
      {st.map(([h, b], i) => {
        const row = Math.floor(i / 4), col = row === 0 ? i % 4 : 3 - (i % 4);
        const x = 100 + col * 435, y = 290 + row * 330;
        return (
          <React.Fragment key={i}>
            <Box x={x} y={y} w={390} h={240} tint={i === 7 ? C.red : undefined}>
              <div style={{ position: "absolute", left: 26, top: 24, right: 22 }}>
                <div style={{ fontFamily: MONO, fontSize: 26, color: i === 7 ? C.red : C.blue }}>{i + 1}</div>
                <P size={32} style={{ fontWeight: 800, marginTop: 4 }}>{h}</P>
                <P size={23} color={C.mute} style={{ marginTop: 8 }}>{b}</P>
              </div>
            </Box>
            {i !== 3 && i !== 7 ? <div style={{ position: "absolute", left: row === 0 ? x + 396 : x - 40, top: y + 100, fontFamily: INTER, fontSize: 36, color: C.yellow }}>{row === 0 ? "→" : "←"}</div> : null}
            {i === 3 ? <div style={{ position: "absolute", left: x + 175, top: y + 248, fontFamily: INTER, fontSize: 40, color: C.yellow }}>↓</div> : null}
          </React.Fragment>
        );
      })}
      <div style={{ position: "absolute", left: 100, top: 940, fontFamily: MONO, fontSize: 24, color: C.mute }}>→  estimated_trajectory.txt     memory: float32 array buffers reused in place, about 57 B per IMU row</div>
      <Foot n={4} />
    </AbsoluteFill>
  );
};

const S5 = () => (
  <AbsoluteFill>
    <GridBG tint={C.blue} />
    <Head k="track 3 final output" t="Output exactly as required" />
    <Box x={100} y={240} w={820} h={300} label="estimated_trajectory.txt (TUM, space separated)">
      <div style={{ position: "absolute", left: 28, top: 70, fontFamily: MONO, fontSize: 22, color: C.text, lineHeight: 1.7 }}>
        <div style={{ color: C.mute }}># timestamp tx ty tz qx qy qz qw</div>
        <div>1403636579.758555392 0.000000 0.000000 0.000000</div>
        <div style={{ paddingLeft: 40 }}>-0.1163427 -0.8060970 -0.0517267 0.5779241</div>
        <div style={{ color: C.green, marginTop: 10 }}>35 629 input rows → 35 629 poses, unit quaternions</div>
      </div>
    </Box>
    <Box x={100} y={570} w={820} h={410} label="EuRoC MH_01, degraded: error in metres">
      <div style={{ position: "absolute", left: 28, top: 70, right: 28, fontFamily: INTER, fontSize: 24 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 100px 110px 120px", color: C.mute, fontFamily: MONO, fontSize: 19, paddingBottom: 8, borderBottom: `1px solid ${C.line}` }}><span>test</span><span>ATE</span><span>waypts</span><span>blind 5 s</span></div>
        {[["Full 184 s", "4.29", "3.74", "4.48"], ["0 to 120 s", "4.56", "4.48", "2.18"], ["60 to 150 s (mid-flight)", "2.13", "1.84", "2.91"], ["45 s to end (mid-flight)", "3.54", "2.50", "6.52"]].map((r, i) => (
          <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 100px 110px 120px", padding: "9px 0", color: C.text, borderBottom: `1px solid ${C.line}` }}>{r.map((c, j) => <span key={j}>{c}</span>)}</div>
        ))}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 100px 110px 120px", padding: "10px 0", color: C.blue, fontWeight: 800 }}><span>Mean of 12 runs</span><span>3.62</span><span>3.14</span><span>3.68</span></div>
      </div>
    </Box>
    <Box x={960} y={240} w={860} h={740} label="position error over the flight, log scale">
      <div style={{ position: "absolute", left: 110, top: 90 }}><ErrChart w={700} h={460} up={1} /></div>
      <P size={24} color={C.mute} style={{ position: "absolute", left: 30, bottom: 26, right: 30 }}>Naive strap-down on the same data: <b style={{ color: C.red }}>210 m ATE</b>. PathFinder: <b style={{ color: C.blue }}>4.29 m</b>. ATE after SE(3) Umeyama alignment; evo_ape agrees.</P>
    </Box>
    <Foot n={5} />
  </AbsoluteFill>
);

const S6 = () => (
  <AbsoluteFill>
    <GridBG />
    <Head k="differentiation" t="What sets PathFinder apart" />
    <div style={{ position: "absolute", left: 100, top: 240, width: 1720, fontFamily: INTER, fontSize: 28 }}>
      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr 1fr", padding: "0 0 14px", color: C.mute, fontFamily: MONO, fontSize: 22, borderBottom: `1.5px solid ${C.line}` }}><span></span><span>typical approach</span><span style={{ color: C.blue }}>PathFinder</span></div>
      {[["Memory", "numpy/scipy EKF: 10 to 40 MB heap", "2.45 MB whole process, stdlib only"], ["Runtime", "matrix EKF at 200 Hz in Python", "1.8 ms per IMU-second (11x margin)"], ["Drift", "strap-down: hundreds of metres", "bounded, at or below stand-still error"], ["Gyro bias", "first 1 to 2 s only", "every rest period, time-interpolated"], ["Dropouts", "assume a fixed dt", "per-row dt, trapezoid across gaps"], ["Input", "fixed column order and units", "auto order, g, deg/s, s to ns, zip/folder/csv"]].map((r, i) => (
        <div key={i} style={{ display: "grid", gridTemplateColumns: "260px 1fr 1fr", padding: "22px 0", borderBottom: `1px solid ${C.line}`, alignItems: "center" }}>
          <span style={{ fontWeight: 800, color: C.text }}>{r[0]}</span><span style={{ color: C.mute }}>{r[1]}</span><span style={{ color: C.text, fontWeight: 600 }}>{r[2]}</span>
        </div>
      ))}
    </div>
    <div style={{ position: "absolute", left: 100, top: 900, fontFamily: HAND, fontWeight: 700, fontSize: 44, color: C.yellow, transform: "rotate(-1.5deg)" }}>measured gyro bias (-0.003, 0.021, 0.080) rad/s vs EuRoC's own (-0.002, 0.025, 0.082)</div>
    <Foot n={6} />
  </AbsoluteFill>
);

const S7 = () => (
  <AbsoluteFill>
    <GridBG />
    <Head k="tools and tech stack" t="Small stack, on purpose" />
    {[
      ["Submission (src/main.py)", C.blue, ["Python 3.8+, standard library only", "array (float32 buffers), math, csv, zipfile, json", "tracemalloc for the memory measurement", "single thread, no network, no GPU"]],
      ["Evaluation and research (tools/)", C.green, ["organiser degrade_imu.py, unchanged", "numpy, pandas for dataset building and scoring", "evo (evo_ape) to cross-check ATE", "matplotlib for figures"]],
      ["Data", C.yellow, ["EuRoC MAV, Machine Hall 01", "12 degraded variants: default, 1.5x harder, swapped columns", "crops that start mid-flight", "ground truth only used for scoring"]],
      ["Delivery", C.gt, ["Docker (python:3.11-slim) one-line run", "GitHub: code, README, results, slides, video", "metadata.json run report", "Remotion + ffmpeg for the demo video"]],
    ].map(([h, c, items]: any, i) => (
      <Box key={i} x={100 + (i % 2) * 870} y={240 + Math.floor(i / 2) * 365} w={840} h={335} tint={c}>
        <div style={{ position: "absolute", left: 32, top: 28, right: 30 }}>
          <P size={32} style={{ fontWeight: 800 }}>{h}</P>
          <div style={{ marginTop: 14 }}>{items.map((t: string, j: number) => <P key={j} size={25} color={C.text} style={{ marginTop: 8 }}><span style={{ color: c }}>▸ </span>{t}</P>)}</div>
        </div>
      </Box>
    ))}
    <Foot n={7} />
  </AbsoluteFill>
);

const S8 = () => (
  <AbsoluteFill>
    <GridBG />
    <Head k="demo and local setup" t="Run it in one line" />
    <Box x={100} y={240} w={1100} h={470}>
      <div style={{ height: 50, background: "#0d1424", display: "flex", alignItems: "center", gap: 12, paddingLeft: 22 }}>{["#ff5f57", "#febc2e", "#28c840"].map((c) => <div key={c} style={{ width: 15, height: 15, borderRadius: 99, background: c }} />)}</div>
      <div style={{ padding: "26px 34px", fontFamily: MONO, fontSize: 25, lineHeight: 1.75, color: C.text }}>
        <div style={{ color: C.mute }}># no install needed (Python 3.8+)</div>
        <div><span style={{ color: C.green }}>$ </span>python src/main.py dataset.zip -o estimated_trajectory.txt</div>
        <div style={{ paddingLeft: 40 }}>--meta metadata.json</div>
        <div style={{ color: C.mute, marginTop: 10 }}># memory check</div>
        <div><span style={{ color: C.green }}>$ </span>python src/main.py dataset.zip --profile</div>
        <div style={{ color: C.mute, marginTop: 10 }}># docker</div>
        <div><span style={{ color: C.green }}>$ </span>docker build -t pathfinder . && docker run ...</div>
      </div>
    </Box>
    <Box x={1240} y={240} w={580} h={470} tint={C.blue}>
      <div style={{ position: "absolute", left: 32, top: 32, right: 30 }}>
        <P size={24} color={C.mute}>Repository</P>
        <P size={30} style={{ fontWeight: 700, fontFamily: MONO, marginTop: 6 }}>github.com/abdulhaq7378-hash/PathFinder</P>
        <P size={24} color={C.mute} style={{ marginTop: 34 }}>Demo video</P>
        <P size={28} style={{ marginTop: 6 }}>docs/MIT_Team_video.mp4, link in the form</P>
        <P size={24} color={C.mute} style={{ marginTop: 34 }}>Reproduce the scores</P>
        <P size={26} style={{ fontFamily: MONO, marginTop: 6 }}>tools/make_data.py, tools/bench.py</P>
      </div>
    </Box>
    <div style={{ position: "absolute", left: 100, top: 760, display: "flex", gap: 24 }}>
      {[["csv, folder or zip", C.blue], ["metadata.json: gaps, duplicates, spikes, rests, bias", C.green], ["bounded error through 774 dropout gaps", C.yellow]].map(([t, c], i) => (
        <div key={i} style={{ padding: "16px 26px", borderRadius: 999, background: `${c}1f`, border: `2px solid ${c}88`, fontFamily: INTER, fontWeight: 600, fontSize: 26, color: C.text }}>{t}</div>
      ))}
    </div>
    <Foot n={8} />
  </AbsoluteFill>
);

const S9 = () => (
  <AbsoluteFill>
    <GridBG tint={C.yellow} />
    <Head k="brownie points" t="Research beyond the baseline" color={C.yellow} />
    {[
      ["Rotor-drag physics", "Multirotor horizontal acceleration is proportional to minus velocity (corr 0.82 on ground truth). Our drag-velocity EKF was 4 to 10x worse with estimated attitude, so it stays out of the submission and is documented."],
      ["Memory engineering", "Lazy imports and a tiny argument parser save 1.8 MB of interpreter heap. Arrays are reused in place: about 57 bytes per IMU row."],
      ["Robust evaluation", "12 degraded variants: default, 1.5x harder, swapped-column script misuse, and crops that start mid-flight. Our scorer matches evo."],
      ["Honest limits and next steps", "An IMU alone cannot observe slow drift over minutes. Next: a tiny learned motion prior (about 200 KB 1D-CNN) and a drag model calibrated per platform."],
    ].map(([h, b], i) => (
      <Box key={i} x={100 + (i % 2) * 870} y={240 + Math.floor(i / 2) * 365} w={840} h={335}>
        <div style={{ position: "absolute", left: 32, top: 30, right: 30 }}>
          <P size={34} style={{ fontWeight: 800 }}>{h}</P>
          <P size={26} color={C.mute} style={{ marginTop: 14 }}>{b}</P>
        </div>
      </Box>
    ))}
    <Foot n={9} />
  </AbsoluteFill>
);

const S10 = () => (
  <AbsoluteFill>
    <Photo src="pathfinder/pcb.jpg" dim={0.7} />
    <div style={{ position: "absolute", left: 110, top: 300 }}>
      <div style={{ fontFamily: INTER, fontWeight: 800, fontSize: 160, color: C.text, letterSpacing: -5 }}>Thank you</div>
      <P size={40} color={C.mute} style={{ marginTop: 10 }}>Nadir Hussain and Abdul Haq, Manipal Institute of Technology</P>
      <div style={{ fontFamily: MONO, fontSize: 40, color: C.blue, marginTop: 50 }}>github.com/abdulhaq7378-hash/PathFinder</div>
    </div>
  </AbsoluteFill>
);

const ALL = [S1, S2, S3, S4, S5, S6, S7, S8, S9, S10];
export const Slide: React.FC<{ n: number }> = ({ n }) => { const S = ALL[n - 1]; return <AbsoluteFill style={{ background: C.bg }}><S /></AbsoluteFill>; };
