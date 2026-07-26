'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Waves, Activity, Download, Pause, Play, RotateCcw, RotateCw, AlertCircle } from 'lucide-react';
import { FauxWaveform, BACKEND_URL } from '@/lib/constants';

function formatTime(sec) {
  if (!isFinite(sec) || sec < 0) return "0:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

const CinematicAudioPlayer = ({ title = "Final Master.mp3", storyData = null }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0); // 0-100
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [statusLabel, setStatusLabel] = useState('AI NARRATOR READY');

  const audioRef = useRef(null);
  const progressBarRef = useRef(null);
  const audioCtxRef = useRef(null);
  const analyserRef = useRef(null);
  const sourceNodeRef = useRef(null);

  const [currentAudioUrl, setCurrentAudioUrl] = useState(() => {
    if (!storyData?.audio_url) return null;
    if (storyData.audio_url.startsWith('http')) return storyData.audio_url;
    return `${BACKEND_URL}${storyData.audio_url}`;
  });

  useEffect(() => {
    if (!storyData?.audio_url) {
      setCurrentAudioUrl(null);
    } else if (storyData.audio_url.startsWith('http')) {
      setCurrentAudioUrl(storyData.audio_url);
    } else {
      setCurrentAudioUrl(`${BACKEND_URL}${storyData.audio_url}`);
    }
  }, [storyData?.audio_url]);

  const handleAudioError = () => {
    if (currentAudioUrl && currentAudioUrl.startsWith(BACKEND_URL) && storyData?.audio_url) {
      console.info("Backend audio URL unreachable, falling back to local frontend public URL:", storyData.audio_url);
      setCurrentAudioUrl(storyData.audio_url);
    }
  };

  useEffect(() => {
    return () => {
      if (audioCtxRef.current) {
        try { audioCtxRef.current.close(); } catch (e) { /* already closed */ }
      }
    };
  }, []);

  // Real audio graph — same AnalyserNode approach as the plain HTML frontend
  // (frontend/app.js's ensureAudioGraph), so playback drives the waveform for real.
  const ensureAudioGraph = () => {
    if (audioCtxRef.current || !audioRef.current) return;
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const source = ctx.createMediaElementSource(audioRef.current);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    analyser.connect(ctx.destination);
    audioCtxRef.current = ctx;
    analyserRef.current = analyser;
    sourceNodeRef.current = source;
  };

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    ensureAudioGraph();
    if (audioCtxRef.current?.state === 'suspended') audioCtxRef.current.resume();
    if (isPlaying) {
      audio.pause();
    } else {
      audio.play().catch((e) => console.warn("Playback failed:", e));
    }
  };

  const handleDownload = () => {
    if (!currentAudioUrl) return;
    const a = document.createElement('a');
    a.href = currentAudioUrl;
    a.download = `${(title || 'dream_master').replace(/[^a-z0-9]/gi, '_').toLowerCase()}.mp3`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const seekTo = (fraction) => {
    const audio = audioRef.current;
    if (!audio || !duration) return;
    audio.currentTime = Math.max(0, Math.min(1, fraction)) * duration;
  };

  const handleProgressClick = (e) => {
    if (!progressBarRef.current) return;
    const rect = progressBarRef.current.getBoundingClientRect();
    seekTo((e.clientX - rect.left) / rect.width);
  };

  const skip = (deltaSeconds) => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = Math.max(0, Math.min(duration || 0, audio.currentTime + deltaSeconds));
  };

  if (!currentAudioUrl) {
    return (
      <div className="relative overflow-hidden rounded-2xl bg-[#0a0816] border border-white/10 shadow-2xl p-6 flex items-center space-x-4">
        <div className="p-3.5 bg-amber-500/10 rounded-2xl border border-amber-500/30 shrink-0">
          <AlertCircle className="w-6 h-6 text-amber-400" />
        </div>
        <div>
          <h4 className="text-white text-lg font-serif font-bold tracking-wide">{title}</h4>
          <p className="text-slate-400 text-xs mt-1">No rendered audio for this memory yet — synthesize it again to generate a real master.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden group rounded-2xl bg-[#0a0816] border border-white/10 shadow-2xl transition-all duration-500 hover:border-indigo-500/40 hover:shadow-[0_10px_40px_-10px_rgba(79,70,229,0.3)]">
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 via-transparent to-fuchsia-600/10 pointer-events-none opacity-50 group-hover:opacity-100 transition-opacity duration-700 ease-out" />

      <audio
        ref={audioRef}
        src={currentAudioUrl}
        preload="metadata"
        onError={handleAudioError}
        onPlay={() => { setIsPlaying(true); setStatusLabel('NOW PLAYING'); }}
        onPause={() => setIsPlaying(false)}
        onEnded={() => { setIsPlaying(false); setStatusLabel('PLAYBACK COMPLETE'); }}
        onLoadedMetadata={(e) => setDuration(e.currentTarget.duration || 0)}
        onTimeUpdate={(e) => {
          const t = e.currentTarget.currentTime;
          setCurrentTime(t);
          if (duration > 0) setProgress((t / duration) * 100);
        }}
      />

      <div className="p-6 relative z-10">
        <div className="flex justify-between items-start mb-6">
          <div className="flex items-center space-x-4">
            <div className="p-3.5 bg-gradient-to-br from-indigo-500/20 to-fuchsia-500/20 rounded-2xl border border-indigo-500/30 backdrop-blur-md transition-transform duration-500 group-hover:scale-105 shadow-[0_0_20px_rgba(79,70,229,0.2)]">
              <Waves className="w-6 h-6 text-indigo-400 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-bold uppercase tracking-widest bg-indigo-500/20 text-indigo-300 px-2.5 py-0.5 rounded-full border border-indigo-500/30">Qwen3-TTS Voices</span>
                <span className="text-[10px] font-bold uppercase tracking-widest bg-fuchsia-500/20 text-fuchsia-300 px-2.5 py-0.5 rounded-full border border-fuchsia-500/30">Stable Audio Score</span>
              </div>
              <h4 className="text-white text-lg sm:text-xl font-serif font-bold tracking-wide truncate max-w-sm sm:max-w-md md:max-w-lg mt-1">{title}</h4>
              <p className="text-slate-400 text-xs font-mono mt-1 flex items-center">
                <Activity className="w-3 h-3 mr-1.5 text-emerald-400" /> Real generated master — voices, SFX, and score mixed server-side
              </p>
            </div>
          </div>
          <button onClick={handleDownload} title="Download Audio Master" className="p-2.5 text-slate-400 hover:text-white hover:bg-white/10 border border-transparent hover:border-white/10 rounded-xl transition-all duration-300 hover:scale-105 active:scale-95 cursor-pointer flex items-center space-x-1.5 text-xs font-semibold">
            <Download className="w-4 h-4 text-indigo-400" />
            <span className="hidden sm:inline">Export</span>
          </button>
        </div>

        <div className="flex items-center space-x-4 sm:space-x-5 bg-black/40 p-4 rounded-2xl border border-white/5">
          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={() => skip(-15)}
              title="Rewind 15s"
              className="w-10 h-10 flex items-center justify-center rounded-xl bg-white/5 hover:bg-white/15 text-slate-300 hover:text-white transition-all duration-300 cursor-pointer hover:scale-105 active:scale-95"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={togglePlay}
              className="w-14 h-14 shrink-0 flex items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-fuchsia-600 hover:from-indigo-400 hover:to-fuchsia-500 text-white shadow-[0_0_25px_rgba(79,70,229,0.5)] hover:shadow-[0_0_35px_rgba(232,121,249,0.7)] transition-all duration-300 transform hover:scale-105 active:scale-95 cursor-pointer"
            >
              {isPlaying ? <Pause className="w-6 h-6 fill-current transition-all duration-300" /> : <Play className="w-6 h-6 fill-current ml-1 transition-all duration-300" />}
            </button>
            <button
              onClick={() => skip(15)}
              title="Fast Forward 15s"
              className="w-10 h-10 flex items-center justify-center rounded-xl bg-white/5 hover:bg-white/15 text-slate-300 hover:text-white transition-all duration-300 cursor-pointer hover:scale-105 active:scale-95"
            >
              <RotateCw className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 min-w-0">
            <FauxWaveform isPlaying={isPlaying} />
            <div
              ref={progressBarRef}
              onClick={handleProgressClick}
              className="h-2 w-full bg-white/10 rounded-full cursor-pointer relative overflow-hidden mt-3 group/bar"
            >
              <div
                className="absolute top-0 left-0 h-full bg-gradient-to-r from-indigo-400 via-fuchsia-400 to-emerald-400 transition-all duration-300 ease-out group-hover/bar:brightness-125 shadow-[0_0_10px_rgba(232,121,249,0.5)]"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex justify-between text-[11px] text-slate-400 mt-2 font-mono">
              <span className="text-indigo-300 font-semibold">{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>
        </div>

        <div className="mt-5 p-4 bg-gradient-to-r from-indigo-900/20 via-fuchsia-900/10 to-transparent border border-indigo-500/20 rounded-2xl text-xs flex items-center space-x-3 animate-in fade-in duration-300 shadow-inner">
          <div className="w-8 h-8 rounded-xl bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center shrink-0">
            <Waves className="w-4 h-4 text-indigo-400 animate-pulse" />
          </div>
          <div className="flex-1 min-w-0">
            <span className="font-bold font-mono text-indigo-300 mr-2 uppercase tracking-wider">{statusLabel}:</span>
            <span className="text-slate-200 italic font-medium">
              {storyData?.qa_report
                ? `Quality check: ${storyData.qa_report.consistency_score}/100${storyData.qa_report.issues?.length ? ` — ${storyData.qa_report.issues.length} note(s)` : ''}`
                : 'Press play to hear the real generated master.'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export { CinematicAudioPlayer };
