'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Waves, Activity, Download, Pause, Play, Mic } from 'lucide-react';
import { FauxWaveform } from '@/lib/constants';

const CinematicAudioPlayer = ({ title = "Final Master.wav", storyData = null }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentSpeaker, setCurrentSpeaker] = useState('');
  const [currentSpeechText, setCurrentSpeechText] = useState('');
  
  const progressBarRef = useRef(null);
  const audioCtxRef = useRef(null);
  const synthOscRefs = useRef([]);
  const speechQueueRef = useRef([]);
  const isPlayingRef = useRef(false);

  useEffect(() => {
    isPlayingRef.current = isPlaying;
  }, [isPlaying]);

  useEffect(() => {
    return () => {
      stopAllAudio();
    };
  }, []);

  const stopAllAudio = () => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    if (audioCtxRef.current) {
      try {
        audioCtxRef.current.close();
      } catch (e) {
        console.warn("AudioContext close error:", e);
      }
      audioCtxRef.current = null;
    }
    synthOscRefs.current = [];
  };

  const startAmbientScore = () => {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      if (ctx.state === 'suspended') {
        ctx.resume();
      }
      audioCtxRef.current = ctx;

      const masterGain = ctx.createGain();
      masterGain.gain.setValueAtTime(0.08, ctx.currentTime);
      masterGain.connect(ctx.destination);

      const osc1 = ctx.createOscillator();
      osc1.type = 'sawtooth';
      osc1.frequency.setValueAtTime(55.0, ctx.currentTime); // A1 root note drone

      const osc2 = ctx.createOscillator();
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(82.4, ctx.currentTime); // E2 fifth for tension

      const osc3 = ctx.createOscillator();
      osc3.type = 'triangle';
      osc3.frequency.setValueAtTime(27.5, ctx.currentTime); // A0 sub bass rumble

      const filter = ctx.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(220, ctx.currentTime);
      filter.Q.setValueAtTime(3, ctx.currentTime);

      const lfo = ctx.createOscillator();
      lfo.frequency.setValueAtTime(0.25, ctx.currentTime); // Breathing pulse
      const lfoGain = ctx.createGain();
      lfoGain.gain.setValueAtTime(80, ctx.currentTime);
      lfo.connect(lfoGain);
      lfoGain.connect(filter.frequency);

      osc1.connect(filter);
      osc2.connect(filter);
      osc3.connect(filter);
      filter.connect(masterGain);

      osc1.start();
      osc2.start();
      osc3.start();
      lfo.start();

      synthOscRefs.current = [osc1, osc2, osc3, lfo];
    } catch (e) {
      console.warn("Web Audio API not available:", e);
    }
  };

  const prepareSpeechQueue = () => {
    if (!storyData || !storyData.scenes || !Array.isArray(storyData.scenes)) {
      return [
        { speaker: "System", text: `Audio master ready for ${title}. Synthesizing multi-layer soundscape.` }
      ];
    }
    const queue = [];
    storyData.scenes.forEach((scene, idx) => {
      if (scene.setting) {
        queue.push({ speaker: "Scene Setting", text: `Scene ${idx + 1}. ${scene.setting}.` });
      }
      if (scene.lines && Array.isArray(scene.lines)) {
        scene.lines.forEach(line => {
          if (line && line.text) {
            queue.push({ speaker: line.speaker || "Narrator", text: line.text });
          }
        });
      }
    });
    return queue.length > 0 ? queue : [{ speaker: "System", text: "No spoken dialogue detected in this screenplay." }];
  };

  const speakNextInQueue = (index, total) => {
    if (!isPlayingRef.current) return;
    if (index >= speechQueueRef.current.length) {
      setIsPlaying(false);
      setProgress(100);
      setCurrentSpeaker('Playback Complete');
      setCurrentSpeechText('All dialogue and audio cues rendered.');
      stopAllAudio();
      return;
    }

    const currentItem = speechQueueRef.current[index];
    setCurrentSpeaker(currentItem.speaker.toUpperCase());
    setCurrentSpeechText(currentItem.text);
    setProgress(((index) / total) * 100);

    if (typeof window === 'undefined' || !window.speechSynthesis) {
      setTimeout(() => {
        if (isPlayingRef.current) speakNextInQueue(index + 1, total);
      }, 2500);
      return;
    }

    const utterance = new SpeechSynthesisUtterance(currentItem.text);
    const voices = window.speechSynthesis.getVoices();
    const englishVoices = voices.filter(v => v.lang.startsWith('en'));

    const spk = currentItem.speaker.toLowerCase();
    if (spk.includes('scene') || spk.includes('system') || spk.includes('setting')) {
      utterance.pitch = 0.8;
      utterance.rate = 1.0;
      if (englishVoices[0]) utterance.voice = englishVoices[0];
    } else if (spk.includes('narrator') || spk.includes('dreamer')) {
      utterance.pitch = 0.95;
      utterance.rate = 0.9;
      const maleVoice = englishVoices.find(v => v.name.toLowerCase().includes('male') || v.name.toLowerCase().includes('david') || v.name.toLowerCase().includes('google') || v.name.toLowerCase().includes('mark'));
      if (maleVoice) utterance.voice = maleVoice;
    } else {
      utterance.pitch = 1.15;
      utterance.rate = 0.95;
      const femaleVoice = englishVoices.find(v => v.name.toLowerCase().includes('female') || v.name.toLowerCase().includes('samantha') || v.name.toLowerCase().includes('zira') || v.name.toLowerCase().includes('victoria'));
      if (femaleVoice) utterance.voice = femaleVoice;
    }

    utterance.onend = () => {
      if (isPlayingRef.current) {
        speakNextInQueue(index + 1, total);
      }
    };
    utterance.onerror = (e) => {
      console.warn("Utterance error:", e);
      if (isPlayingRef.current) {
        speakNextInQueue(index + 1, total);
      }
    };

    window.speechSynthesis.speak(utterance);
  };

  const togglePlay = () => {
    if (isPlaying) {
      setIsPlaying(false);
      stopAllAudio();
      setCurrentSpeaker('Paused');
    } else {
      stopAllAudio();
      setIsPlaying(true);
      setProgress(0);
      speechQueueRef.current = prepareSpeechQueue();
      startAmbientScore();
      setTimeout(() => {
        if (typeof window !== 'undefined' && window.speechSynthesis && window.speechSynthesis.getVoices().length === 0) {
          window.speechSynthesis.onvoiceschanged = () => {
            speakNextInQueue(0, speechQueueRef.current.length);
          };
        } else {
          speakNextInQueue(0, speechQueueRef.current.length);
        }
      }, 100);
    }
  };

  const handleDownload = () => {
    const content = `DREAM ARCHAEOLOGY - AUDIO & SCREENPLAY MASTER\nTitle: ${title}\nFormat: 44.1kHz Stereo Mix\nTimestamp: ${new Date().toLocaleString()}\n\n[Audio Master Generated by Narrative Cortex]\n`;
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleProgressClick = (e) => {
    if (!progressBarRef.current) return;
    const rect = progressBarRef.current.getBoundingClientRect();
    setProgress(((e.clientX - rect.left) / rect.width) * 100);
  };

  return (
    <div className="relative overflow-hidden group rounded-2xl bg-[#0a0816] border border-white/10 shadow-2xl transition-all duration-500 hover:border-indigo-500/40 hover:shadow-[0_10px_40px_-10px_rgba(79,70,229,0.3)]">
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 via-transparent to-fuchsia-600/10 pointer-events-none opacity-50 group-hover:opacity-100 transition-opacity duration-700 ease-out" />
      
      <div className="p-6 relative z-10">
        <div className="flex justify-between items-start mb-6">
          <div className="flex items-center space-x-4">
            <div className="p-3.5 bg-gradient-to-br from-indigo-500/20 to-fuchsia-500/20 rounded-2xl border border-indigo-500/30 backdrop-blur-md transition-transform duration-500 group-hover:scale-105 shadow-[0_0_20px_rgba(79,70,229,0.2)]">
              <Waves className="w-6 h-6 text-indigo-400 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-bold uppercase tracking-widest bg-indigo-500/20 text-indigo-300 px-2.5 py-0.5 rounded-full border border-indigo-500/30">Live Synthesizer</span>
                <span className="text-[10px] font-bold uppercase tracking-widest bg-fuchsia-500/20 text-fuchsia-300 px-2.5 py-0.5 rounded-full border border-fuchsia-500/30">Voice Narrator</span>
              </div>
              <h4 className="text-white text-lg sm:text-xl font-serif font-bold tracking-wide truncate max-w-sm sm:max-w-md md:max-w-lg mt-1">{title}</h4>
              <p className="text-slate-400 text-xs font-mono mt-1 flex items-center">
                <Activity className="w-3 h-3 mr-1.5 text-emerald-400" /> 44.1kHz • Live Audio Master & Dialogue Narration
              </p>
            </div>
          </div>
          <button onClick={handleDownload} title="Download Master Script & Audio Log" className="p-2.5 text-slate-400 hover:text-white hover:bg-white/10 border border-transparent hover:border-white/10 rounded-xl transition-all duration-300 hover:scale-105 active:scale-95 cursor-pointer flex items-center space-x-1.5 text-xs font-semibold">
            <Download className="w-4 h-4 text-indigo-400" />
            <span className="hidden sm:inline">Export</span>
          </button>
        </div>

        <div className="flex items-center space-x-5 bg-black/40 p-4 rounded-2xl border border-white/5">
          <button 
            onClick={togglePlay}
            className="w-14 h-14 shrink-0 flex items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-fuchsia-600 hover:from-indigo-400 hover:to-fuchsia-500 text-white shadow-[0_0_25px_rgba(79,70,229,0.5)] hover:shadow-[0_0_35px_rgba(232,121,249,0.7)] transition-all duration-300 transform hover:scale-105 active:scale-95 cursor-pointer"
          >
            {isPlaying ? <Pause className="w-6 h-6 fill-current transition-all duration-300" /> : <Play className="w-6 h-6 fill-current ml-1 transition-all duration-300" />}
          </button>
          
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
              <span className="text-indigo-300 font-semibold">00:{(Math.floor(progress / 2)).toString().padStart(2, '0')}</span>
              <span>00:50</span>
            </div>
          </div>
        </div>

        <div className="mt-5 p-4 bg-gradient-to-r from-indigo-900/20 via-fuchsia-900/10 to-transparent border border-indigo-500/20 rounded-2xl text-xs flex items-center space-x-3 animate-in fade-in duration-300 shadow-inner">
          <div className="w-8 h-8 rounded-xl bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center shrink-0">
            <Mic className="w-4 h-4 text-indigo-400 animate-pulse" />
          </div>
          <div className="flex-1 min-w-0">
            <span className="font-bold font-mono text-indigo-300 mr-2 uppercase tracking-wider">{currentSpeaker || 'AI NARRATOR READY'}:</span>
            <span className="text-slate-200 italic font-medium">"{currentSpeechText || 'Press Play above to initialize live ambient soundtrack & voice narration.'}"</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export { CinematicAudioPlayer };
