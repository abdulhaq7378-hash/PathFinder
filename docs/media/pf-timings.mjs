// usage: node pf-timings.mjs [voiceDir]
// Builds src/pathfinder/timings.json. For each scene NN, uses <voiceDir>/NN.* if present:
// trims silence, normalises loudness -> public/pathfinder/voice/NN.wav, Whisper word times aligned to the script.
// Without a recording, falls back to an estimated duration (placeholder captions).
import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, writeFileSync, statSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
const require = createRequire(import.meta.url);
const FF = require("ffmpeg-static");

const VOICE = process.argv[2] || "C:/Users/Admin/Desktop/xr-hackathon/voice";
const SCRIPT = {
  "01": "Over two hundred metres. That's how far off you end up when you integrate this jammed IMU the textbook way. Our estimator stays around three and a half metres off on average, and it uses just two and a half megabytes of memory.",
  "02": "We're Nadir and Abdul from Manipal Institute of Technology, and this is PathFinder, our entry for Track 3.",
  "03": "A plane flies a recon mission with no GPS. It's being jammed, so its only sensor, the IMU, gets worse every second. Noise, drift, spikes, missing chunks, and for the last five seconds, nothing at all. From that, we have to rebuild its full path.",
  "04": "The hard part is double integration. A tiny accelerometer bias turns into over a kilometre of error in three minutes. And one degree of tilt leaks gravity straight into your position.",
  "05": "Then there's the budget: eight megabytes. When we profiled it, importing numpy alone used all eight. So we dropped numpy and wrote everything in plain Python.",
  "06": "PathFinder runs on four ideas. One: find every moment the vehicle is still. At rest, the gyro should read zero, so whatever it reads is bias. We measure it at every stop and follow the drift in between.",
  "07": "Two: a Mahony filter blends the gyro with gravity to track orientation. It trusts gravity fully at rest, and only lightly in flight.",
  "08": "Three: velocity has to be zero at every stop, so we reset it there and remove the drift that built up in between. And since the task is offline, we smooth in both directions.",
  "09": "Four: when the IMU dies, we coast on the last velocity and turn rate we trust, let them fade out, and still output a pose for every single timestamp.",
  "10": "We tested on EuRoC Machine Hall 1, degraded with the organisers' own script. Across twelve runs, the average error is three point six metres. Honestly, an IMU alone can't see slow drift over minutes. What we could do was stop it from exploding.",
  "11": "And it's light: two point four five megabytes peak, one point eight milliseconds per second of data, eleven times under the limit, on one thread with zero dependencies.",
  "12": "Running it is one line. Give it the CSV, the folder or the zip, and it writes the trajectory, plus a report of every gap and spike it found.",
  "13": "We also tried a rotor-drag physics model, and wrote down why we dropped it. Everything is on our GitHub. That's PathFinder. Thanks for watching!",
};
const norm = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, "");
const OUTV = path.resolve("public/pathfinder/voice"); mkdirSync(OUTV, { recursive: true });
const files = existsSync(VOICE) ? readdirSync(VOICE) : [];
let asr = null;
async function whisper(wav) {
  if (!asr) {
    const { pipeline, env } = await import("@huggingface/transformers");
    env.cacheDir = "./.models";
    asr = await pipeline("automatic-speech-recognition", "onnx-community/whisper-small_timestamped", { dtype: "fp32" });
  }
  const raw = execFileSync(FF, ["-nostdin", "-v", "error", "-i", wav, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], { maxBuffer: 1 << 30 });
  const audio = new Float32Array(raw.buffer, raw.byteOffset, raw.length / 4);
  const r = await asr(audio, { return_timestamps: "word", chunk_length_s: 30, stride_length_s: 5, language: "en", task: "transcribe" });
  return r.chunks.map((c) => ({ w: c.text.trim(), s: c.timestamp[0], e: c.timestamp[1] ?? c.timestamp[0] + 0.3 }));
}
// align script words to whisper words (LCS on normalised tokens), interpolate the rest
function align(script, hyp, dur) {
  const A = script.map(norm), B = hyp.map((h) => norm(h.w));
  const n = A.length, m = B.length; const L = Array.from({ length: n + 1 }, () => new Int16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) L[i][j] = A[i] === B[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const t = new Array(n).fill(null); let i = 0, j = 0;
  while (i < n && j < m) { if (A[i] === B[j]) { t[i] = [hyp[j].s, hyp[j].e]; i++; j++; } else if (L[i + 1][j] >= L[i][j + 1]) i++; else j++; }
  const matched = t.filter(Boolean).length;
  const anchors = [[-1, 0], ...t.map((x, k) => (x ? [k, x[0]] : null)).filter(Boolean), [n, dur]];
  const out = script.map((w, k) => {
    if (t[k]) return { w, s: t[k][0], e: t[k][1] };
    let a = anchors[0], b = anchors[anchors.length - 1];
    for (const an of anchors) { if (an[0] < k) a = an; if (an[0] > k) { b = an; break; } }
    const s = a[1] + ((b[1] - a[1]) * (k - a[0])) / (b[0] - a[0]);
    return { w, s, e: s + 0.3 };
  });
  return { words: out, ratio: matched / n };
}
const scenes = [];
for (const id of Object.keys(SCRIPT).sort()) {
  const words = SCRIPT[id].split(/\s+/);
  const src = files.find((f) => {
    const m = f.match(/^(\d+)/);
    if (m) return m[1].padStart(2, "0") === id;
    return id === "01" && /^hook/i.test(f);
  });
  if (src) {
    const out = path.join(OUTV, `${id}.wav`);
    const run = (af, t) => execFileSync(FF, ["-nostdin", "-v", "error", "-y", "-i", path.join(VOICE, src), "-vn", "-ac", "1", "-ar", "48000", "-af", af, out], { stdio: ["ignore", "pipe", "pipe"], timeout: t });
    const chains = [
      "highpass=f=70,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15,areverse,loudnorm=I=-16:TP=-2:LRA=9",
      "highpass=f=70,loudnorm=I=-16:TP=-2:LRA=9",
      "highpass=f=70,dynaudnorm=f=150:g=15,volume=0.9",
      "volume=1.0",
    ];
    let okc = -1;
    for (let k = 0; k < chains.length && okc < 0; k++) { try { run(chains[k], 25000); okc = k; } catch (e) { console.log(`  ${id}: filter ${k} failed, trying next`); } }
    if (okc < 0) throw new Error("audio conversion failed for " + src);
    const dur = (statSync(out).size - 44) / (48000 * 2);
    const hyp = await whisper(out);
    let { words: w, ratio } = align(words, hyp, dur);
    if (ratio < 0.55) { console.log(`  ${id}: low script match (${(ratio * 100) | 0}%), using Whisper text`); w = hyp; }
    scenes.push({ id, dur: Math.max(dur + 0.35, 2), audio: `pathfinder/voice/${id}.wav`, words: w });
    console.log(id, src, dur.toFixed(2) + "s", "match", (ratio * 100 | 0) + "%");
  } else {
    const dur = words.length / 2.55 + 0.4;
    scenes.push({ id, dur, words: words.map((w, k) => ({ w, s: (k / words.length) * (dur - 0.4), e: ((k + 1) / words.length) * (dur - 0.4) })) });
    console.log(id, "placeholder", dur.toFixed(2) + "s");
  }
}
writeFileSync("src/pathfinder/timings.json", JSON.stringify({ scenes }, null, 1));
const total = scenes.reduce((a, s) => a + s.dur + 0.25, 0) + 1.2;
console.log("TOTAL", total.toFixed(1), "s", total > 180 ? "OVER 3:00!" : "");

