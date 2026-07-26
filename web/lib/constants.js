'use client';

import React, { useState, useEffect } from 'react';
import { BrainCircuit, Zap, Search, Sparkles } from 'lucide-react';

export const NARRATIVE_LENSES = [
  { id: 'psychological', label: 'Psychological', icon: BrainCircuit, color: 'text-indigo-400', bg: 'bg-indigo-500/10', border: 'border-indigo-500/20' },
  { id: 'thriller', label: 'Thriller', icon: Zap, color: 'text-rose-400', bg: 'bg-rose-500/10', border: 'border-rose-500/20' },
  { id: 'mystery', label: 'Mystery', icon: Search, color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' },
  { id: 'fantasy', label: 'Fantasy', icon: Sparkles, color: 'text-fuchsia-400', bg: 'bg-fuchsia-500/10', border: 'border-fuchsia-500/20' }
];

export const MOCK_DREAM_GRAPH = {
  nodes: [
    { id: 'n1', type: 'Character', label: 'Narrator', layer: 'Conscious' },
    { id: 'n2', type: 'Character', label: 'Sister', layer: 'Memory' },
    { id: 'n3', type: 'Location', label: 'Shifting House', layer: 'Symbolic' },
    { id: 'n4', type: 'Totem', label: 'Red Door', layer: 'Fear' },
    { id: 'n5', type: 'Emotion', label: 'Confusion', layer: 'Subconscious' }
  ],
  followUp: "I noticed a gap in the memory: You mentioned opening the red doors, but not what was behind the final one. What did you feel right before waking up?"
};

export const MOCK_STORY_DATA = {
  "title": "The House That Kept Changing",
  "lens": "psychological",
  "characters": [
    {"id": "narrator", "name": "Narrator", "role": "first-person dreamer"},
    {"id": "sister", "name": "Sister", "role": "implied, searched for"}
  ],
  "scenes": [
    {
      "id": 1,
      "layer": "Subconscious Memory",
      "setting": "a house with shifting rooms, dim light",
      "emotional_tone": "confused, searching",
      "lines": [
        {"speaker": "narrator", "text": "I kept opening doors, but none of them led where they should."}
      ],
      "sound_cues": [
        {"type": "ambient", "prompt": "creaking wood, distant echo"},
        {"type": "one-shot", "prompt": "door creaks open", "position": "before line 1"}
      ]
    },
    {
      "id": 2,
      "layer": "Symbolic Truth",
      "setting": "the final corridor, absolute silence",
      "emotional_tone": "dread, realization",
      "lines": [
        {"speaker": "narrator", "text": "It wasn't a house at all. It was just... waiting."}
      ],
      "sound_cues": [
        {"type": "music", "prompt": "low synth drone, rising tension"},
        {"type": "one-shot", "prompt": "heartbeat pulsing, slowing down", "position": "during line 1"}
      ]
    }
  ]
};

export const PROCESSING_STEPS = [
  { id: 'reconstruct', label: 'Narrative Reconstruction & Layer Mapping', duration: 1000 },
  { id: 'screenplay', label: 'Screenplay Conversion (Dialogue & Cues)', duration: 800 },
  { id: 'direction', label: 'Audio Direction Engine (Emotion & Casting)', duration: 1000 },
  { id: 'voice', label: 'Synthesizing Voices (gpt-4o-mini-tts)', duration: 1200 },
  { id: 'mix', label: 'Composing Timeline (Ducking & SFX Mix)', duration: 1200 }
];

// Helper components used within views
export const BlinkingCursor = () => (
  <span className="inline-block w-2 h-4 ml-1 bg-indigo-400 animate-[pulse_1s_cubic-bezier(0.4,0,0.6,1)_infinite] align-middle shadow-[0_0_8px_rgba(129,140,248,0.8)] rounded-sm" />
);

export const Typewriter = ({ text, delay = 20, onComplete = () => {} }) => {
  const [currentText, setCurrentText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        setCurrentText(prev => prev + text[currentIndex]);
        setCurrentIndex(prev => prev + 1);
      }, delay);
      return () => clearTimeout(timeout);
    } else if (onComplete) {
      onComplete();
    }
  }, [currentIndex, delay, text, onComplete]);

  return <span className="transition-all duration-75">{currentText}</span>;
};

export const FauxWaveform = ({ isPlaying = false }) => (
  <div className="flex items-center space-x-1 h-8 px-4">
    {[...Array(32)].map((_, i) => (
      <div
        key={i}
        className={`w-1 rounded-full bg-indigo-500/60 transition-all duration-300 ease-in-out ${isPlaying ? 'shadow-[0_0_10px_rgba(99,102,241,0.5)]' : ''}`}
        style={{
          height: isPlaying ? `${Math.max(15, Math.random() * 100)}%` : `${15 + Math.sin(i * 0.4) * 15}%`,
          animationDelay: `${i * 0.05}s`
        }}
      />
    ))}
  </div>
);