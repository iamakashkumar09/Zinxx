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

let characterColorMap = new Map();
let characterNameMap = new Map();

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
  stepsEl.hidden = false;
  resetSteps();

  try {
    setStepState("story", "active");
    setStatus("Extracting story structure...");
    const storyRes = await fetch("/api/story", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!storyRes.ok) {
      const err = await storyRes.json().catch(() => ({}));
      throw new Error(err.detail || "Story extraction failed.");
    }
    const story = await storyRes.json();
    setStepState("story", "done");
    renderStory(story);

    setStatus("Directing voices, designing sound, and mixing the final track...");
    const audioOrder = ["emotion", "voice", "sound", "mix"];
    const audioEstimates = [1500, 16000, 5000, 2500];
    const audioFetch = fetch("/api/audio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ story }),
    });
    const audioRes = await withSimulatedProgress(audioFetch, audioOrder, audioEstimates);

    if (!audioRes.ok) {
      const err = await audioRes.json().catch(() => ({}));
      throw new Error(err.detail || "Audio generation failed.");
    }
    const result = await audioRes.json();
    renderStory(result.story);
    renderAudio(result.audio_url);
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
        renderStory(ex.story);
        renderAudio(ex.audio_url);
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
