import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, interpolate, useVideoConfig } from "remotion";
import { SCENES } from "./scenes";
import { C, INTER } from "./ui";
import TIM from "./timings.json";

export type Word = { w: string; s: number; e: number };
export type SceneT = { id: string; dur: number; audio?: string; words: Word[] };
export const FPS = 30;
const T: { scenes: SceneT[] } = TIM as any;
const LEAD = 0.25; // seconds of picture before the voice starts in each scene

export const totalFrames = () => Math.round((T.scenes.reduce((a, s) => a + s.dur + LEAD, 0) + 1.2) * FPS);

/** captions: phrases of up to ~7 words, shown while spoken */
const Captions: React.FC<{ words: Word[] }> = ({ words }) => {
  const f = useCurrentFrame(); const t = f / FPS - LEAD;
  if (!words.length) return null;
  const phrases: Word[][] = []; let cur: Word[] = [];
  words.forEach((w, i) => {
    cur.push(w);
    const end = /[.,!?:;]$/.test(w.w) || cur.length >= 7 || i === words.length - 1;
    if (end) { phrases.push(cur); cur = []; }
  });
  const ph = phrases.find((p, i) => t >= p[0].s - 0.05 && t < (phrases[i + 1] ? phrases[i + 1][0].s - 0.05 : p[p.length - 1].e + 0.4));
  if (!ph) return null;
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 46, display: "flex", justifyContent: "center", pointerEvents: "none" }}>
      <div style={{ maxWidth: 1500, padding: "12px 26px", borderRadius: 14, background: "rgba(4,7,14,0.72)", fontFamily: INTER, fontWeight: 600, fontSize: 38, color: C.text, textAlign: "center", lineHeight: 1.3 }}>
        {ph.map((w, i) => <span key={i} style={{ color: t >= w.s ? C.text : "#ffffff88" }}>{w.w} </span>)}
      </div>
    </div>
  );
};

const SceneWrap: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const f = useCurrentFrame(); const { durationInFrames: N } = useVideoConfig();
  const inP = interpolate(f, [0, 9], [0, 1], { extrapolateRight: "clamp" });
  const outP = interpolate(f, [N - 6, N], [1, 0], { extrapolateLeft: "clamp" });
  return <AbsoluteFill style={{ opacity: Math.min(inP * 1.2, 1) * outP, transform: `translateX(${(1 - inP) * 60}px)` }}>{children}</AbsoluteFill>;
};

export const PathFinderVideo: React.FC<{ captions?: boolean }> = ({ captions = true }) => {
  let at = 0;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      {T.scenes.map((s, i) => {
        const from = Math.round(at * FPS); const len = Math.round((s.dur + LEAD) * FPS) + (i === T.scenes.length - 1 ? Math.round(1.2 * FPS) : 0);
        at += s.dur + LEAD;
        const S = SCENES[s.id];
        return (
          <Sequence key={s.id} from={from} durationInFrames={len} name={`scene ${s.id}`}>
            <SceneWrap><S /></SceneWrap>
            {s.audio ? <Sequence from={Math.round(LEAD * FPS)}><Audio src={staticFile(s.audio)} /></Sequence> : null}
            {i > 0 ? <Audio src={staticFile("sfx/whoosh.wav")} volume={0.12} /> : null}
            {captions ? <Captions words={s.words} /> : null}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
