// usage: node pf-render.mjs stills <t1,t2,...seconds>  |  node pf-render.mjs slides  |  node pf-render.mjs video
import { bundle } from "@remotion/bundler";
import { renderMedia, renderStill, selectComposition } from "@remotion/renderer";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import path from "node:path";
const FF = createRequire(import.meta.url)("ffmpeg-static");
const [mode, arg] = process.argv.slice(2);
const serveUrl = await bundle({ entryPoint: path.resolve("src/pathfinder/index.ts") });
const OUT = path.resolve("out/pathfinder"); mkdirSync(OUT, { recursive: true });
if (mode === "stills") {
  const comp = await selectComposition({ serveUrl, id: "PathFinder" });
  console.log("duration", (comp.durationInFrames / comp.fps).toFixed(1), "s");
  for (const t of arg.split(",")) {
    const frame = Math.min(comp.durationInFrames - 1, Math.round(parseFloat(t) * comp.fps));
    await renderStill({ composition: comp, serveUrl, frame, output: `${OUT}/still_${t}.png` });
    console.log("still", t);
  }
} else if (mode === "slides") {
  for (let i = 1; i <= 10; i++) {
    const comp = await selectComposition({ serveUrl, id: `Slide${i}` });
    await renderStill({ composition: comp, serveUrl, output: `${OUT}/slide_${String(i).padStart(2, "0")}.png` });
    console.log("slide", i);
  }
} else if (mode === "video") {
  const comp = await selectComposition({ serveUrl, id: "PathFinder" });
  const raw = `${OUT}/PathFinder_raw.mp4`;
  await renderMedia({ composition: comp, serveUrl, codec: "h264", crf: 16, outputLocation: raw, audioBitrate: "320k", concurrency: 4,
    onProgress: ({ progress }) => { if (Math.round(progress * 100) % 10 === 0) process.stdout.write(`\r${Math.round(progress * 100)}%`); } });
  execFileSync(FF, ["-v", "error", "-y", "-i", raw, "-c:v", "libx264", "-crf", "20", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", `${OUT}/MIT_Team_video.mp4`]);
  console.log("\nwrote", `${OUT}/MIT_Team_video.mp4`, (comp.durationInFrames / comp.fps).toFixed(1), "s");
}
