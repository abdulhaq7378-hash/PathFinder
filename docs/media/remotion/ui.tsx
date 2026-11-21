import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import { loadFont as loadHand } from "@remotion/google-fonts/Caveat";

export const INTER = loadInter("normal", { weights: ["400", "500", "600", "700", "800"], subsets: ["latin"] }).fontFamily;
export const MONO = loadMono("normal", { weights: ["400", "600"], subsets: ["latin"] }).fontFamily;
export const HAND = loadHand("normal", { weights: ["500", "700"], subsets: ["latin"] }).fontFamily;

export const C = {
  bg: "#0a0f1c", panel: "#121a2e", line: "#24304d", text: "#eef2fa", mute: "#8f9bb5",
  blue: "#4ea8ff", red: "#ff5a5f", gt: "#b9c2d6", yellow: "#ffd166", green: "#3ddc97",
};

export const ease = (f: number, a: number, b: number, from = 0, to = 1) =>
  interpolate(f, [a, b], [from, to], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.22, 1, 0.36, 1) });

export const usePop = (delay = 0, damping = 14) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  return spring({ frame: f - delay, fps, config: { damping, mass: 0.7 } });
};

/** engineering-notebook background: dark navy with a faint grid that drifts slowly */
export const GridBG: React.FC<{ tint?: string }> = ({ tint }) => {
  const f = useCurrentFrame();
  const off = (f * 0.25) % 60;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <AbsoluteFill style={{
        backgroundImage: `linear-gradient(${C.line}55 1px, transparent 1px), linear-gradient(90deg, ${C.line}55 1px, transparent 1px)`,
        backgroundSize: "60px 60px", backgroundPosition: `${off}px ${off}px`, opacity: 0.55,
      }} />
      {tint ? <AbsoluteFill style={{ background: `radial-gradient(1200px 700px at 70% 30%, ${tint}22, transparent 70%)` }} /> : null}
    </AbsoluteFill>
  );
};

/** real photo with slow push-in */
export const Photo: React.FC<{ src: string; dim?: number; from?: number; to?: number; x?: number; shift?: number }> = ({ src, dim = 0.55, from = 1.04, to = 1.16, x = 0, shift = 0 }) => {
  const f = useCurrentFrame(); const { durationInFrames } = useVideoConfig();
  const s = interpolate(f, [0, durationInFrames], [from, to]) + (shift ? 0.12 : 0);
  return (
    <AbsoluteFill style={{ overflow: "hidden", background: "#000" }}>
      <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${s}) translateX(${shift + x * f * 0.02}px)` }} />
      <AbsoluteFill style={{ background: `linear-gradient(90deg, rgba(5,8,16,${dim + 0.25}) 0%, rgba(5,8,16,${dim}) 55%, rgba(5,8,16,${dim * 0.6}) 100%)` }} />
    </AbsoluteFill>
  );
};

export const Kicker: React.FC<{ children: React.ReactNode; color?: string; delay?: number; style?: React.CSSProperties }> = ({ children, color = C.blue, delay = 0, style }) => {
  const p = usePop(delay);
  return (
    <div style={{ fontFamily: MONO, fontSize: 24, letterSpacing: 3, color, textTransform: "uppercase", opacity: p, transform: `translateY(${(1 - p) * 14}px)`, ...style }}>{children}</div>
  );
};

export const Title: React.FC<{ children: React.ReactNode; size?: number; delay?: number; style?: React.CSSProperties }> = ({ children, size = 76, delay = 0, style }) => {
  const p = usePop(delay, 16);
  return (
    <div style={{ fontFamily: INTER, fontWeight: 800, fontSize: size, lineHeight: 1.04, color: C.text, letterSpacing: -1.5, opacity: p, transform: `translateY(${(1 - p) * 28}px)`, ...style }}>{children}</div>
  );
};

/** handwritten note, like something scribbled on the slide */
export const Note: React.FC<{ children: React.ReactNode; x: number; y: number; color?: string; size?: number; delay?: number; rot?: number }> = ({ children, x, y, color = C.yellow, size = 44, delay = 0, rot = -3 }) => {
  const f = useCurrentFrame();
  const o = ease(f, delay, delay + 8);
  return (
    <div style={{ position: "absolute", left: x, top: y, fontFamily: HAND, fontWeight: 700, fontSize: size, color, transform: `rotate(${rot}deg)`, opacity: o, clipPath: `inset(0 ${100 - o * 100}% 0 0)`, whiteSpace: "nowrap" }}>{children}</div>
  );
};

/** hand-drawn marker loop around something (slightly wobbly, drawn on) */
export const MarkerLoop: React.FC<{ cx: number; cy: number; rx: number; ry: number; color?: string; delay?: number; dur?: number; seed?: number }> = ({ cx, cy, rx, ry, color = C.yellow, delay = 0, dur = 14, seed = 1 }) => {
  const f = useCurrentFrame();
  const pts: string[] = [];
  const n = 48;
  for (let i = 0; i <= n + 6; i++) {
    const a = (i / n) * Math.PI * 2 - 0.6;
    const wob = 1 + 0.035 * Math.sin(i * 1.7 + seed) + (i > n ? 0.06 : 0);
    pts.push(`${cx + Math.cos(a) * rx * wob},${cy + Math.sin(a) * ry * wob}`);
  }
  const d = "M" + pts.join(" L");
  const len = 2 * Math.PI * Math.max(rx, ry) * 1.25;
  const p = ease(f, delay, delay + dur);
  return (
    <svg style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, overflow: "visible", pointerEvents: "none" }}>
      <path d={d} fill="none" stroke={color} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={len} strokeDashoffset={len * (1 - p)} opacity={0.95} />
    </svg>
  );
};

export const Arrow: React.FC<{ x1: number; y1: number; x2: number; y2: number; color?: string; delay?: number }> = ({ x1, y1, x2, y2, color = C.yellow, delay = 0 }) => {
  const f = useCurrentFrame();
  const p = ease(f, delay, delay + 10);
  const mx = (x1 + x2) / 2 + (y2 - y1) * 0.15, my = (y1 + y2) / 2 - (x2 - x1) * 0.15;
  const ex = x1 + (x2 - x1) * p, ey = y1 + (y2 - y1) * p;
  const ang = Math.atan2(y2 - my, x2 - mx);
  return (
    <svg style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, overflow: "visible", pointerEvents: "none" }}>
      <path d={`M${x1},${y1} Q${mx},${my} ${x2},${y2}`} fill="none" stroke={color} strokeWidth={4.5} strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - p} />
      {p > 0.95 ? <path d={`M${ex - 22 * Math.cos(ang - 0.45)},${ey - 22 * Math.sin(ang - 0.45)} L${ex},${ey} L${ex - 22 * Math.cos(ang + 0.45)},${ey - 22 * Math.sin(ang + 0.45)}`} fill="none" stroke={color} strokeWidth={4.5} strokeLinecap="round" strokeLinejoin="round" /> : null}
    </svg>
  );
};

export const Chip: React.FC<{ children: React.ReactNode; color?: string; delay?: number; style?: React.CSSProperties }> = ({ children, color = C.blue, delay = 0, style }) => {
  const p = usePop(delay, 12);
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 12, padding: "12px 22px", borderRadius: 999, background: `${color}1f`, border: `2px solid ${color}88`, color: C.text, fontFamily: INTER, fontWeight: 600, fontSize: 30, transform: `scale(${0.85 + 0.15 * p})`, opacity: p, ...style }}>{children}</div>
  );
};

export const Counter: React.FC<{ to: number; from?: number; start: number; dur: number; decimals?: number; suffix?: string; style?: React.CSSProperties }> = ({ to, from = 0, start, dur, decimals = 0, suffix = "", style }) => {
  const f = useCurrentFrame();
  const v = interpolate(f, [start, start + dur], [from, to], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  return <span style={style}>{v.toFixed(decimals)}{suffix}</span>;
};

/** a framed card like a figure on a poster */
export const Card: React.FC<{ x: number; y: number; w: number; h: number; delay?: number; children: React.ReactNode; label?: string }> = ({ x, y, w, h, delay = 0, children, label }) => {
  const p = usePop(delay, 16);
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: h, background: C.panel, border: `1.5px solid ${C.line}`, borderRadius: 18, boxShadow: "0 30px 80px rgba(0,0,0,0.45)", opacity: p, transform: `translateY(${(1 - p) * 40}px)`, overflow: "hidden" }}>
      {label ? <div style={{ position: "absolute", left: 24, top: 18, fontFamily: MONO, fontSize: 20, color: C.mute, letterSpacing: 1 }}>{label}</div> : null}
      {children}
    </div>
  );
};

type XY = number[][];
export const bounds = (sets: XY[], pad = 0.08) => {
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const s of sets) for (const [x, y] of s) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  const dx = (x1 - x0) * pad, dy = (y1 - y0) * pad;
  return { x0: x0 - dx, x1: x1 + dx, y0: y0 - dy, y1: y1 + dy };
};
export const toPath = (pts: XY, b: { x0: number; x1: number; y0: number; y1: number }, w: number, h: number, equal = true, upto = 1) => {
  let sx = w / (b.x1 - b.x0), sy = h / (b.y1 - b.y0);
  let ox = 0, oy = 0;
  if (equal) { const s = Math.min(sx, sy); ox = (w - (b.x1 - b.x0) * s) / 2; oy = (h - (b.y1 - b.y0) * s) / 2; sx = sy = s; }
  const n = Math.max(2, Math.floor(pts.length * upto));
  let d = "";
  for (let i = 0; i < n; i++) { const [x, y] = pts[i]; d += (i ? "L" : "M") + (ox + (x - b.x0) * sx).toFixed(1) + "," + (h - oy - (y - b.y0) * sy).toFixed(1); }
  const last = pts[n - 1];
  return { d, end: [ox + (last[0] - b.x0) * sx, h - oy - (last[1] - b.y0) * sy] };
};
/** time series -> path, x = time */
export const seriesPath = (t: number[], v: number[], tx: [number, number], vy: [number, number], w: number, h: number, upto = Infinity) => {
  let d = ""; let k = 0;
  for (let i = 0; i < t.length; i++) {
    if (t[i] > upto) break;
    const x = ((t[i] - tx[0]) / (tx[1] - tx[0])) * w; const y = h - ((v[i] - vy[0]) / (vy[1] - vy[0])) * h;
    d += (k++ ? "L" : "M") + x.toFixed(1) + "," + Math.max(-50, Math.min(h + 50, y)).toFixed(1);
  }
  return d;
};

/** progress strip for the four ideas */
export const IdeaTag: React.FC<{ n: number; label: string }> = ({ n, label }) => {
  const p = usePop(0, 14);
  return (
    <div style={{ position: "absolute", left: 90, top: 70, display: "flex", alignItems: "center", gap: 18, opacity: p }}>
      {[1, 2, 3, 4].map((i) => (
        <div key={i} style={{ width: 54, height: 54, borderRadius: 14, display: "grid", placeItems: "center", fontFamily: MONO, fontWeight: 600, fontSize: 26,
          background: i === n ? C.blue : i < n ? `${C.blue}33` : "transparent", color: i === n ? "#04101f" : C.mute, border: `2px solid ${i <= n ? C.blue : C.line}` }}>{i}</div>
      ))}
      <div style={{ marginLeft: 10, fontFamily: INTER, fontWeight: 700, fontSize: 34, color: C.text }}>{label}</div>
    </div>
  );
};
