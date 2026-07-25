'use client';

import React from 'react';
import { Clapperboard, User, Layers, Activity, MapPin, Music } from 'lucide-react';
import { NARRATIVE_LENSES } from '@/lib/constants';
import { CinematicAudioPlayer } from './CinematicAudioPlayer';

const CinematicScriptView = ({ data = {} }) => {
  const lensObj = NARRATIVE_LENSES.find(l => l.id === (data?.lens || 'psychological')) || NARRATIVE_LENSES[0];
  const LensIcon = lensObj.icon;

  return (
    <div className="space-y-12 animate-in fade-in slide-in-from-bottom-8 duration-1000 ease-out fill-mode-both">
      <div className="animate-in fade-in slide-in-from-bottom-6 duration-700 delay-400 fill-mode-both">
        <CinematicAudioPlayer title={data.title || "Master Cinematic Audio"} storyData={data} />
      </div>

      <div className="animate-in fade-in slide-in-from-bottom-6 duration-700 delay-500 fill-mode-both">
        <h3 className="text-xs uppercase tracking-widest text-slate-500 mb-5 font-semibold flex items-center">
          <User className="w-4 h-4 mr-2" /> Cast
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {data.characters.map((char, idx) => (
            <div key={char.id} 
                 className="group p-4 rounded-2xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.05] hover:border-indigo-500/40 transition-all duration-500 flex items-center space-x-4 animate-in fade-in slide-in-from-left-4 fill-mode-both hover:-translate-y-0.5 hover:shadow-lg hover:shadow-indigo-500/10"
                 style={{ animationDelay: `${600 + (idx * 100)}ms` }}>
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-900/40 to-fuchsia-900/40 border border-white/10 flex items-center justify-center shrink-0 group-hover:border-indigo-400/60 group-hover:scale-110 transition-all duration-500">
                <span className="font-serif text-indigo-200 text-lg group-hover:text-white transition-colors">{char.name.charAt(0)}</span>
              </div>
              <div className="overflow-hidden">
                <p className="text-slate-200 font-medium truncate group-hover:text-white transition-colors">{char.name}</p>
                <p className="text-slate-500 text-xs truncate capitalize mt-0.5 group-hover:text-indigo-300/70 transition-colors">{char.role}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-12 relative animate-in fade-in slide-in-from-bottom-8 duration-700 delay-[800ms] fill-mode-both">
        <div className="absolute left-[19px] top-4 bottom-0 w-px bg-gradient-to-b from-indigo-500/40 via-fuchsia-500/20 to-transparent" />
        {data.scenes.map((scene, idx) => (
          <div key={scene.id} className="relative pl-12 group/scene">
            <div className="absolute left-[15px] top-1.5 w-2.5 h-2.5 rounded-full bg-indigo-400 shadow-[0_0_15px_rgba(129,140,248,0.6)] ring-4 ring-[#0a0a14] group-hover/scene:scale-125 group-hover/scene:bg-fuchsia-400 group-hover/scene:shadow-[0_0_20px_rgba(232,121,249,0.6)] transition-all duration-500" />
            
            <div className="mb-5 flex flex-wrap items-center gap-3">
              <span className="px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-mono font-bold tracking-widest transition-colors group-hover/scene:bg-indigo-500/20 flex items-center">
                SCENE {idx + 1}
              </span>
              {scene.layer && (
                 <span className="text-[10px] font-bold uppercase tracking-widest text-fuchsia-300 bg-fuchsia-900/30 border border-fuchsia-500/20 px-2 py-1 rounded-md flex items-center">
                   <Layers className="w-3 h-3 mr-1" /> {scene.layer}
                 </span>
              )}
              <span className="text-slate-400 text-sm flex items-center bg-white/[0.02] px-3 py-1.5 rounded-full border border-white/5 transition-colors group-hover/scene:bg-white/[0.05]">
                <Activity className="w-3.5 h-3.5 mr-2 text-fuchsia-400 animate-pulse" />
                {scene.emotional_tone}
              </span>
            </div>

            <div className="p-6 md:p-8 rounded-[2rem] bg-gradient-to-br from-white/[0.04] to-transparent border border-white/5 backdrop-blur-md shadow-2xl transition-all duration-700 group-hover/scene:border-white/10 group-hover/scene:bg-white/[0.06] group-hover/scene:shadow-[0_15px_40px_-10px_rgba(79,70,229,0.15)]">
              <p className="text-slate-300 text-sm leading-relaxed mb-8 flex items-start bg-black/30 p-4 rounded-2xl border border-white/5">
                <MapPin className="w-4 h-4 mr-3 text-indigo-400 shrink-0 mt-0.5" />
                <span><strong className="uppercase tracking-widest text-slate-500 mr-2 text-xs">Setting:</strong> {scene.setting}</span>
              </p>

              <div className="space-y-8 mb-8 relative">
                <div className="absolute left-4 top-0 bottom-0 w-px bg-white/10 group-hover/scene:bg-indigo-500/30 transition-colors duration-700" />
                {scene.lines.map((line, i) => (
                  <div key={i} className="pl-10 relative">
                    <div className="absolute left-[-1px] top-3 w-4 h-px bg-white/20 group-hover/scene:bg-indigo-500/50 transition-colors duration-700" />
                    <p className="text-xs font-mono text-indigo-300 uppercase tracking-widest mb-2 flex items-center">
                      {line.speaker}
                    </p>
                    <p className="text-slate-100 font-serif text-xl leading-relaxed italic tracking-wide">"{line.text}"</p>
                  </div>
                ))}
              </div>

              {scene.sound_cues?.length > 0 && (
                <div className="pt-6 border-t border-white/10">
                  <h4 className="text-xs uppercase tracking-widest text-slate-500 mb-4 flex items-center font-semibold">
                    <Music className="w-4 h-4 mr-2" /> Audio Cues
                  </h4>
                  <div className="flex flex-wrap gap-2.5">
                    {scene.sound_cues.map((cue, i) => (
                      <div key={i} className="flex items-center px-3 py-1.5 rounded-xl bg-black/40 border border-white/5 text-xs text-slate-400 shadow-inner hover:bg-black/60 hover:border-white/10 transition-colors cursor-default">
                        <span className={`w-1.5 h-1.5 rounded-full mr-2.5 ${cue.type === 'ambient' ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.6)]'}`} />
                        <span className="capitalize text-slate-500 mr-2 font-medium">{cue.type}:</span> 
                        <span className="font-mono text-slate-300">{cue.prompt}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export { CinematicScriptView };
