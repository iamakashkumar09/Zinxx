const SAMPLE_DREAMS = [
  "I kept opening doors in a house I didn't recognize, but none of them led where they should. I was looking for my sister, and I could hear her calling from somewhere, but every room was empty.",
  "I was back in my old school, but the hallways kept stretching longer. My friend Sam was next to me laughing about something, and then suddenly the lights went out and I couldn't find him.",
  "I was standing on a beach at night, alone, and the waves kept getting louder. I felt calm at first, then a strange fear crept in as the water started rising toward me.",
];

const CHARACTER_COLORS = ["#a78bfa", "#f0abfc", "#ff9e7a", "#6ee7b7", "#7dd3fc", "#fca5a5", "#fcd34d", "#c4b5fd"];

const TONE_STYLES = [
  { keywords: ["fear", "dread", "tense", "tension", "anxious", "panic"], color: "#fca5a5", icon: "\u{1F630}" },
  { keywords: ["sad", "grief", "loss", "lonely", "melanchol"], color: "#7dd3fc", icon: "\u{1F622}" },
  { keywords: ["anger", "rage", "fury"], color: "#f87171", icon: "\u{1F620}" },
  { keywords: ["joy", "happy", "relief", "warm", "nostalg"], color: "#fcd34d", icon: "\u{1F60A}" },
  { keywords: ["calm", "peace", "quiet", "still"], color: "#6ee7b7", icon: "\u{1F319}" },
  { keywords: ["confus", "surreal", "disorient", "strange"], color: "#a78bfa", icon: "\u{1F300}" },
  { keywords: ["climax", "chaos", "urgent"], color: "#ff9e7a", icon: "⚡" },
];
const DEFAULT_TONE_STYLE = { color: "#f0abfc", icon: "✨" };

const dreamInput = document.getElementById("dream-input");
const sampleRow = document.getElementById("sample-row");
const generateBtn = document.getElementById("generate-btn");
const statusEl = document.getElementById("status");
const stepsEl = document.getElementById("steps");
const storyPanel = document.getElementById("story-panel");
const storyKicker = document.getElementById("story-kicker");
const storyTitle = document.getElementById("story-title");
const storyCharacters = document.getElementById("story-characters");
const storyScenes = document.getElementById("story-scenes");
const audioPanel = document.getElementById("audio-panel");
const audioPlayer = document.getElementById("audio-player");
const downloadLink = document.getElementById("download-link");
const visualizerCanvas = document.getElementById("visualizer");
const playBtn = document.getElementById("play-btn");
const seekInput = document.getElementById("seek");
const timeCurrent = document.getElementById("time-current");
const timeTotal = document.getElementById("time-total");
const micBtn = document.getElementById("mic-btn");
const micStatus = document.getElementById("mic-status");
const storyInsights = document.getElementById("story-insights");
const qaPanel = document.getElementById("qa-panel");
const qaBadge = document.getElementById("qa-badge");
const qaIssues = document.getElementById("qa-issues");

let characterColorMap = new Map();
let characterNameMap = new Map();

/** Stable per-browser id for Module 2's totem memory (Dream Graph) — separate from the
 * server's httpOnly dream_user_id cookie (used for the /api/story fast path), since
 * /api/dream takes user_id as an explicit request field rather than reading the cookie. */
function getClientUserId() {
  const KEY = "dream_client_user_id";
  let id = localStorage.getItem(KEY);
  if (!id) {
    id = "web_" + crypto.randomUUID().replace(/-/g, "").slice(0, 24);
    localStorage.setItem(KEY, id);
  }
  return id;
}

SAMPLE_DREAMS.forEach((dream, i) => {
  const btn = document.createElement("button");
  btn.textContent = `Sample ${i + 1}`;
  btn.type = "button";
  btn.addEventListener("click", () => {
    dreamInput.value = dream;
    dreamInput.focus();
  });
  sampleRow.appendChild(btn);
});

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

/* ---------------------------------------------------------------- */
/* Voice input — record a dream instead of typing it (Module 1)      */
/* ---------------------------------------------------------------- */

const MAX_RECORDING_SECONDS = 90;
const MIME_CANDIDATES = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];

function pickSupportedMimeType() {
  if (typeof MediaRecorder === "undefined") return null;
  return MIME_CANDIDATES.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

function setMicStatus(message, cls) {
  micStatus.textContent = message;
  micStatus.className = "mic-status" + (cls ? ` ${cls}` : "");
}

function extensionFor(mimeType) {
  if (mimeType.includes("webm")) return "webm";
  if (mimeType.includes("ogg")) return "ogg";
  if (mimeType.includes("mp4")) return "m4a";
  return "webm";
}

const micSupported =
  typeof navigator !== "undefined" &&
  navigator.mediaDevices &&
  typeof navigator.mediaDevices.getUserMedia === "function" &&
  typeof MediaRecorder !== "undefined";

let mediaRecorder = null;
let recordedChunks = [];
let recordingStream = null;
let recordingTimerId = null;
let recordingSeconds = 0;
let micState = "idle"; // idle | recording | transcribing

function formatSeconds(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function setMicState(state) {
  micState = state;
  micBtn.classList.toggle("recording", state === "recording");
  micBtn.classList.toggle("transcribing", state === "transcribing");
  micBtn.disabled = state === "transcribing";
}

async function startRecording() {
  const mimeType = pickSupportedMimeType();
  try {
    recordingStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    setMicStatus("Microphone permission denied.", "error");
    return;
  }

  recordedChunks = [];
  mediaRecorder = mimeType
    ? new MediaRecorder(recordingStream, { mimeType })
    : new MediaRecorder(recordingStream);

  mediaRecorder.addEventListener("dataavailable", (e) => {
    if (e.data && e.data.size > 0) recordedChunks.push(e.data);
  });
  mediaRecorder.addEventListener("stop", onRecordingStopped);

  mediaRecorder.start();
  setMicState("recording");
  recordingSeconds = 0;
  setMicStatus(`Recording... ${formatSeconds(recordingSeconds)} (tap to stop)`, "recording");

  recordingTimerId = setInterval(() => {
    recordingSeconds += 1;
    setMicStatus(`Recording... ${formatSeconds(recordingSeconds)} (tap to stop)`, "recording");
    if (recordingSeconds >= MAX_RECORDING_SECONDS) stopRecording();
  }, 1000);
}

function stopRecording() {
  if (recordingTimerId) {
    clearInterval(recordingTimerId);
    recordingTimerId = null;
  }
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
  if (recordingStream) {
    recordingStream.getTracks().forEach((track) => track.stop());
    recordingStream = null;
  }
}

async function onRecordingStopped() {
  setMicState("transcribing");
  setMicStatus("Transcribing...");

  const mimeType = mediaRecorder.mimeType || "audio/webm";
  const blob = new Blob(recordedChunks, { type: mimeType });

  if (blob.size < 500) {
    setMicState("idle");
    setMicStatus("Recording was too short — try again.", "error");
    return;
  }

  try {
    const formData = new FormData();
    formData.append("file", blob, `recording.${extensionFor(mimeType)}`);
    const res = await fetch("/api/transcribe", { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Transcription failed.");
    }
    const { text } = await res.json();
    if (!text) {
      setMicStatus("Didn't catch that — try speaking again.", "error");
    } else {
      dreamInput.value = text;
      setMicStatus("Transcribed — feel free to edit before generating.");
    }
  } catch (err) {
    setMicStatus(err.message, "error");
  } finally {
    setMicState("idle");
  }
}

if (micSupported) {
  micBtn.addEventListener("click", () => {
    if (micState === "idle") startRecording();
    else if (micState === "recording") stopRecording();
  });
} else {
  micBtn.hidden = true;
  setMicStatus("Voice input isn't supported in this browser.");
}

function setStepState(name, state) {
  const el = stepsEl.querySelector(`.step[data-step="${name}"]`);
  if (!el) return;
  el.classList.remove("active", "done");
  if (state) el.classList.add(state);
}

function resetSteps() {
  stepsEl.querySelectorAll(".step").forEach((el) => el.classList.remove("active", "done"));
}

/** Runs a real async task while animating the remaining pipeline steps on an
 * estimated timeline, snapping everything to "done" the moment the real
 * response actually arrives (never claims completion ahead of the real call). */
async function withSimulatedProgress(promise, order, estimatedMs) {
  let settled = false;
  const timers = [];
  setStepState(order[0], "active");

  let cumulative = 0;
  for (let i = 1; i < order.length; i++) {
    cumulative += estimatedMs[i - 1];
    timers.push(
      setTimeout(() => {
        if (settled) return;
        setStepState(order[i - 1], "done");
        setStepState(order[i], "active");
      }, cumulative)
    );
  }

  try {
    const result = await promise;
    settled = true;
    timers.forEach(clearTimeout);
    order.forEach((s) => setStepState(s, "done"));
    return result;
  } catch (err) {
    settled = true;
    timers.forEach(clearTimeout);
    throw err;
  }
}

function initials(name) {
  const parts = name.trim().split(/\s+/);
  return parts.length === 1 ? parts[0].slice(0, 2).toUpperCase() : (parts[0][0] + parts[1][0]).toUpperCase();
}

function buildCharacterColorMap(characters) {
  const map = new Map();
  characters.forEach((c, i) => map.set(c.id, CHARACTER_COLORS[i % CHARACTER_COLORS.length]));
  return map;
}

function toneStyle(tone) {
  const lower = (tone || "").toLowerCase();
  const match = TONE_STYLES.find((t) => t.keywords.some((k) => lower.includes(k)));
  return match || DEFAULT_TONE_STYLE;
}

/** Module 3 (narrative reconstruction) + Module 2 (Dream Graph) evidence — shows gap-fill
 * count and any contradiction warnings, so the reconstruction step is visible, not just a
 * black box between typing a dream and hearing dialogue. */
function renderInsights(dreamResponse) {
  const beats = dreamResponse.narrative_beats || [];
  const gapFillCount = beats.reduce((sum, b) => sum + (b.gap_fills || []).length, 0);
  const warnings = dreamResponse.warnings || [];

  if (!beats.length) {
    storyInsights.hidden = true;
    return;
  }

  const parts = [`🧠 Reconstructed across ${beats.length} narrative beat${beats.length === 1 ? "" : "s"}`];
  if (gapFillCount > 0) parts.push(`${gapFillCount} gap${gapFillCount === 1 ? "" : "s"} filled while preserving dream logic`);
  if (warnings.length > 0) parts.push(`${warnings.length} continuity note${warnings.length === 1 ? "" : "s"}`);

  storyInsights.textContent = parts.join(" · ");
  storyInsights.title = warnings.join("\n");
  storyInsights.hidden = false;
}

/** Module 11 (QA/consistency review) — advisory only, shown after audio finishes. */
function renderQA(qaReport) {
  if (!qaReport) {
    qaPanel.hidden = true;
    return;
  }

  const score = qaReport.consistency_score;
  const tier = score >= 90 ? "good" : score >= 70 ? "ok" : "poor";
  const icon = tier === "good" ? "✓" : tier === "ok" ? "!" : "⚠";

  qaBadge.className = `qa-badge ${tier}`;
  qaBadge.textContent = `${icon} Quality check: ${score}/100`;

  qaIssues.innerHTML = "";
  for (const issue of qaReport.issues || []) {
    const li = document.createElement("li");
    li.textContent = `Scene ${issue.scene_id}: ${issue.description}`;
    qaIssues.appendChild(li);
  }

  qaPanel.hidden = false;
}

function renderStory(story) {
  characterColorMap = buildCharacterColorMap(story.characters);
  characterNameMap = new Map(story.characters.map((c) => [c.id, c.name]));

  storyKicker.textContent = "now adapting";
  storyTitle.textContent = story.title;

  storyCharacters.innerHTML = "";
  story.characters.forEach((c, i) => {
    const chip = document.createElement("span");
    chip.className = "character-chip";
    chip.style.animationDelay = `${i * 60}ms`;

    const avatar = document.createElement("span");
    avatar.className = "avatar";
    avatar.style.background = characterColorMap.get(c.id);
    avatar.textContent = initials(c.name);
    chip.appendChild(avatar);

    chip.appendChild(document.createTextNode(`${c.name} — ${c.role}`));
    storyCharacters.appendChild(chip);
  });

  storyScenes.innerHTML = "";
  story.scenes.forEach((scene) => {
    const style = toneStyle(scene.emotional_tone);
    const sceneEl = document.createElement("div");
    sceneEl.className = "scene";
    sceneEl.style.setProperty("--scene-color", style.color);

    const heading = document.createElement("h3");
    heading.textContent = `${style.icon} Scene ${scene.id}`;
    sceneEl.appendChild(heading);

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `${scene.setting} — ${scene.emotional_tone}`;
    sceneEl.appendChild(meta);

    scene.lines.forEach((line, i) => {
      const lineEl = document.createElement("div");
      lineEl.className = "line";
      lineEl.style.setProperty("--i", i);

      const speaker = document.createElement("span");
      speaker.className = "speaker";
      speaker.style.color = characterColorMap.get(line.speaker) || "var(--accent)";
      speaker.textContent = `${characterNameMap.get(line.speaker) || line.speaker}: `;
      lineEl.appendChild(speaker);
      lineEl.appendChild(document.createTextNode(line.text));
      sceneEl.appendChild(lineEl);

      if (line.performance_direction) {
        const dir = document.createElement("div");
        dir.className = "direction";
        dir.textContent = line.performance_direction;
        sceneEl.appendChild(dir);
      }
    });

    storyScenes.appendChild(sceneEl);
  });

  storyPanel.hidden = false;
}

/* ---------------------------------------------------------------- */
/* Audio player + waveform visualizer                                */
/* ---------------------------------------------------------------- */

let audioCtx = null;
let analyser = null;
let sourceNode = null;
let dataArray = null;
let rafId = null;

function formatTime(sec) {
  if (!isFinite(sec)) return "0:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function ensureAudioGraph() {
  if (audioCtx) return;
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  sourceNode = audioCtx.createMediaElementSource(audioPlayer);
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 256;
  dataArray = new Uint8Array(analyser.frequencyBinCount);
  sourceNode.connect(analyser);
  analyser.connect(audioCtx.destination);
}

function drawVisualizer() {
  const ctx = visualizerCanvas.getContext("2d");
  const { width, height } = visualizerCanvas;
  ctx.clearRect(0, 0, width, height);

  if (analyser && !audioPlayer.paused) {
    analyser.getByteFrequencyData(dataArray);
  } else if (dataArray) {
    dataArray = dataArray.map((v) => Math.max(0, v * 0.85));
  }

  const barCount = 48;
  const step = dataArray ? Math.floor(dataArray.length / barCount) : 0;
  const barWidth = width / barCount;

  for (let i = 0; i < barCount; i++) {
    const value = dataArray ? dataArray[i * step] : 0;
    const barHeight = Math.max(3, (value / 255) * height * 0.85);
    const x = i * barWidth;
    const y = (height - barHeight) / 2;
    const t = i / barCount;
    ctx.fillStyle = `hsl(${265 + t * 60}, 85%, ${58 + (value / 255) * 15}%)`;
    ctx.beginPath();
    ctx.roundRect(x + 1.5, y, Math.max(1, barWidth - 3), barHeight, 3);
    ctx.fill();
  }

  rafId = requestAnimationFrame(drawVisualizer);
}

function renderAudio(audioUrl) {
  audioPlayer.src = audioUrl;
  downloadLink.href = audioUrl;
  audioPanel.hidden = false;
  playBtn.classList.remove("is-playing");
  seekInput.value = 0;
  timeCurrent.textContent = "0:00";
  timeTotal.textContent = "0:00";

  if (!rafId) drawVisualizer();
}

playBtn.addEventListener("click", () => {
  ensureAudioGraph();
  if (audioCtx.state === "suspended") audioCtx.resume();
  audioPlayer.play();
});

document.querySelector(".visualizer-wrap").addEventListener("click", (e) => {
  if (e.target === playBtn) return;
  ensureAudioGraph();
  if (audioCtx.state === "suspended") audioCtx.resume();
  if (audioPlayer.paused) audioPlayer.play();
  else audioPlayer.pause();
});

audioPlayer.addEventListener("play", () => playBtn.classList.add("is-playing"));
audioPlayer.addEventListener("pause", () => playBtn.classList.remove("is-playing"));
audioPlayer.addEventListener("ended", () => playBtn.classList.remove("is-playing"));

audioPlayer.addEventListener("loadedmetadata", () => {
  seekInput.max = audioPlayer.duration || 0;
  timeTotal.textContent = formatTime(audioPlayer.duration);
});

audioPlayer.addEventListener("timeupdate", () => {
  seekInput.value = audioPlayer.currentTime;
  timeCurrent.textContent = formatTime(audioPlayer.currentTime);
});

seekInput.addEventListener("input", () => {
  audioPlayer.currentTime = Number(seekInput.value);
});

/* ---------------------------------------------------------------- */
/* Generate flow                                                     */
/* ---------------------------------------------------------------- */

async function generate() {
  const text = dreamInput.value.trim();
  if (!text) {
    setStatus("Please describe a dream or memory first.", true);
    return;
  }

  generateBtn.disabled = true;
  generateBtn.classList.add("loading");
  storyPanel.hidden = true;
  audioPanel.hidden = true;
  qaPanel.hidden = true;
  stepsEl.hidden = false;
  resetSteps();

  try {
    // Full pipeline: Module 1 (understanding) -> 2 (Dream Graph) -> 3 (narrative
    // reconstruction, gap-filling) -> 7 (screenplay conversion) -> Story ready for audio.
    setStepState("story", "active");
    setStatus("Understanding your dream, building the graph, and reconstructing the narrative...");
    const dreamRes = await fetch("/api/dream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, user_id: getClientUserId() }),
    });
    if (!dreamRes.ok) {
      const err = await dreamRes.json().catch(() => ({}));
      throw new Error(err.detail || "Dream understanding failed.");
    }
    const dreamResult = await dreamRes.json();
    setStepState("story", "done");
    renderStory(dreamResult.story);
    renderInsights(dreamResult);

    // Modules 8 (audio direction) -> 9 (voices/SFX/BGM) -> 11 (QA review) -> 10 (mix)
    setStatus("Directing voices, designing sound, and mixing the final track...");
    const audioOrder = ["emotion", "voice", "sound", "mix"];
    const audioEstimates = [1500, 16000, 5000, 2500];
    const audioFetch = fetch("/api/audio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ story: dreamResult.story }),
    });
    const audioRes = await withSimulatedProgress(audioFetch, audioOrder, audioEstimates);

    if (!audioRes.ok) {
      const err = await audioRes.json().catch(() => ({}));
      throw new Error(err.detail || "Audio generation failed.");
    }
    const result = await audioRes.json();
    renderStory(result.story);
    renderAudio(result.audio_url);
    renderQA(result.qa_report);
    setStatus("Done — press play.");
  } catch (err) {
    setStatus(`${err.message} — try a pre-made example below, or check the server logs.`, true);
  } finally {
    generateBtn.disabled = false;
    generateBtn.classList.remove("loading");
  }
}

generateBtn.addEventListener("click", generate);

async function loadExampleFallbacks() {
  try {
    const res = await fetch("/api/examples");
    if (!res.ok) return;
    const examples = await res.json();
    if (!examples.length) return;

    const wrap = document.createElement("div");
    wrap.className = "sample-row";
    const label = document.createElement("span");
    label.className = "sample-label";
    label.textContent = "Or load a pre-made example";
    wrap.appendChild(label);

    examples.forEach((ex, i) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = ex.story.title || `Example ${i + 1}`;
      btn.addEventListener("click", () => {
        stepsEl.hidden = true;
        storyPanel.hidden = true;
        storyInsights.hidden = true; // pre-baked examples predate Module 3, no beats to show
        renderStory(ex.story);
        renderAudio(ex.audio_url);
        renderQA(ex.qa_report || null);
        setStatus("Loaded pre-made example.");
      });
      wrap.appendChild(btn);
    });

    document.querySelector(".input-panel").appendChild(wrap);
  } catch {
    // examples endpoint optional — ignore failures
  }
}

loadExampleFallbacks();
