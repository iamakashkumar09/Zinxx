'use client';

import React, { useEffect, useState } from 'react';
import { 
  Play, ArrowRight, Fingerprint, Waves, Sparkles, 
  BrainCircuit, Mic, Layers, Cpu, Music, Network 
} from 'lucide-react';

// --- High-End Visual Components (Harmonized with Studio Palette) ---

const FilmGrain = () => (
  <div 
    className="fixed inset-0 z-50 pointer-events-none opacity-[0.04] mix-blend-overlay"
    style={{ 
      backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` 
    }} 
  />
);

const DreamCore = () => (
  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] pointer-events-none opacity-60">
    {/* Deep Studio Glow Triad: Indigo, Fuchsia, Emerald */}
    <div className="absolute inset-0 bg-gradient-to-tr from-indigo-600/30 via-fuchsia-500/20 to-emerald-400/20 rounded-full blur-[100px] animate-pulse-slow" />
    
    {/* Concentric Rotating Rings (Mathematical & Elegant) */}
    <div className="absolute inset-4 border-[1px] border-indigo-500/10 rounded-full animate-spin-slow" />
    <div className="absolute inset-12 border-[1px] border-dashed border-fuchsia-500/15 rounded-full animate-spin-slow-reverse" style={{ borderDasharray: '4 12' }} />
    <div className="absolute inset-24 border-[1px] border-indigo-400/10 rounded-full animate-spin-slow" style={{ animationDuration: '30s' }} />
    
    {/* Inner Core */}
    <div className="absolute inset-[140px] rounded-full bg-gradient-to-tr from-indigo-500/20 to-fuchsia-500/20 backdrop-blur-3xl border border-white/10 shadow-[inset_0_0_80px_rgba(79,70,229,0.15)]" />
  </div>
);

const PremiumButton = ({ children, primary, onClick }) => (
  <button 
    onClick={onClick}
    className={`
      relative group overflow-hidden rounded-full font-medium tracking-wide transition-all duration-500 ease-[cubic-bezier(0.23,1,0.32,1)] cursor-pointer
      ${primary 
        ? 'bg-gradient-to-r from-indigo-500 via-indigo-600 to-fuchsia-600 text-white px-8 py-3.5 hover:scale-105 hover:shadow-[0_0_40px_rgba(79,70,229,0.5)] border border-indigo-400/30 font-semibold' 
        : 'bg-[#0a0816]/80 text-slate-200 px-8 py-3.5 border border-white/10 hover:bg-[#120e2a] hover:border-indigo-500/40 hover:text-white hover:shadow-[0_0_25px_rgba(79,70,229,0.2)]'}
    `}
  >
    {primary && (
      <span className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/30 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]" />
    )}
    <span className="relative flex items-center justify-center">
      {children}
    </span>
  </button>
);

const BentoCard = ({ title, desc, icon: Icon, span, delay }) => (
  <div 
    className={`group relative overflow-hidden rounded-3xl bg-[#0a0816] border border-white/10 p-8 transition-all duration-700 hover:border-indigo-500/40 hover:bg-[#0f0c22] hover:shadow-[0_10px_40px_-10px_rgba(79,70,229,0.3)] animate-in fade-in slide-in-from-bottom-8 fill-mode-both ${span}`}
    style={{ animationDelay: delay }}
  >
    {/* Interactive Hover Glow */}
    <div className="absolute -inset-px bg-gradient-to-br from-indigo-500/20 via-fuchsia-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 blur-sm" />
    
    <div className="relative z-10 flex flex-col h-full">
      <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-fuchsia-500/20 border border-white/10 flex items-center justify-center mb-6 text-indigo-400 group-hover:text-indigo-300 group-hover:scale-110 group-hover:border-indigo-400/50 transition-all duration-500 shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]">
        <Icon className="w-5 h-5" />
      </div>
      <h3 className="text-xl font-semibold text-slate-100 mb-3 tracking-tight group-hover:text-white">{title}</h3>
      <p className="text-slate-400 leading-relaxed font-light mt-auto group-hover:text-slate-300">{desc}</p>
    </div>
  </div>
);

// --- Main Landing Page Component ---

export function LandingPage({ onEnterStudio, onOpenVault, onSignIn, user }) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-[#05040a] text-slate-200 font-sans selection:bg-indigo-500/30 overflow-x-hidden relative flex flex-col font-medium">
      <FilmGrain />

      {/* Studio Cinematic Ambient Background Orbs */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-indigo-900/15 rounded-full blur-[150px] mix-blend-screen animate-[pulse_14s_ease-in-out_infinite]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] bg-fuchsia-900/15 rounded-full blur-[180px] mix-blend-screen animate-[pulse_16s_ease-in-out_infinite_2s]" />
        <div className="absolute top-[20%] right-[20%] w-[40%] h-[40%] bg-emerald-900/10 rounded-full blur-[120px] mix-blend-screen animate-[pulse_20s_ease-in-out_infinite_4s]" />
      </div>

      {/* Ambient Top Light */}
      <div className="absolute top-0 left-0 w-full h-[500px] bg-gradient-to-b from-indigo-900/30 via-transparent to-transparent pointer-events-none" />

      {/* --- Elegant Navigation (Harmonized with Studio Navbar) --- */}
      <nav className={`fixed top-0 w-full z-40 transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] ${scrolled ? 'pt-4' : 'pt-6'}`}>
        <div className={`max-w-5xl mx-auto px-6 flex items-center justify-between transition-all duration-700 ${scrolled ? 'bg-[#05040a]/70 backdrop-blur-3xl border border-white/10 py-3 rounded-full shadow-[0_4px_40px_rgba(0,0,0,0.6)]' : 'py-3'}`}>
          
          {/* Studio Brand Logo */}
          <div className="flex items-center space-x-3 cursor-pointer group pl-2" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500/20 to-fuchsia-500/20 border border-white/10 flex items-center justify-center shadow-lg transition-all duration-700 group-hover:rotate-12 group-hover:scale-110 group-hover:border-indigo-400/50">
              <Network className="w-4 h-4 text-indigo-300" />
            </div>
            <span className="font-serif font-bold tracking-tight text-lg text-white group-hover:text-indigo-200 transition-colors">Dream Archaeology</span>
          </div>
          
          <div className="hidden md:flex items-center space-x-8 text-xs tracking-widest uppercase text-slate-400 font-semibold">
            <a href="#architecture" className="hover:text-indigo-300 transition-colors">Architecture</a>
            <button onClick={onOpenVault} className="hover:text-indigo-300 transition-colors uppercase tracking-widest cursor-pointer">Vault</button>
          </div>
          
          <button 
            onClick={user ? onEnterStudio : onSignIn} 
            className="text-xs font-bold tracking-wide text-white bg-gradient-to-r from-indigo-500/20 to-fuchsia-500/20 border border-white/15 px-5 py-2 rounded-full hover:bg-indigo-500/30 hover:border-indigo-400/50 transition-all cursor-pointer shadow-md hover:scale-105"
          >
            {user ? 'Enter Studio' : 'Sign In'}
          </button>
        </div>
      </nav>

      {/* --- Hero Section --- */}
      <section className="relative z-10 pt-48 pb-32 px-6 flex flex-col items-center text-center min-h-[100vh] justify-center overflow-hidden">
        <DreamCore />
        
        <div className="relative z-20 animate-in fade-in slide-in-from-bottom-12 duration-1000 ease-[cubic-bezier(0.16,1,0.3,1)] fill-mode-both">
          
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-[10px] font-bold uppercase tracking-widest text-indigo-300 mb-10 shadow-[0_0_20px_rgba(79,70,229,0.2)] backdrop-blur-md">
            <Fingerprint className="w-3.5 h-3.5 mr-1 text-indigo-400 animate-pulse" />
            <span>Neural Synthesis Engine v2.0</span>
          </div>
          
          <h1 className="text-6xl md:text-8xl lg:text-[8.5rem] leading-[0.95] font-serif font-medium tracking-[-0.04em] mb-8 max-w-6xl mx-auto text-white">
            Listen to <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-300 via-white to-fuchsia-300 italic pr-4">
              your dreams.
            </span>
          </h1>
          
          <p className="text-lg md:text-xl text-slate-300 max-w-2xl mx-auto leading-relaxed mb-12 font-light tracking-wide">
            Transform fragmented memories into cinematic audio reality. 
            A sophisticated pipeline mapping language to emotion, voices, and sound design in seconds.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <PremiumButton primary onClick={onEnterStudio}>
              Initialize Pipeline <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
            </PremiumButton>
            <PremiumButton onClick={onEnterStudio}>
              <Play className="w-4 h-4 mr-2 text-indigo-400" /> Audition Output
            </PremiumButton>
          </div>
        </div>

        {/* --- The Player Mockup (Apple/Dieter Rams + Studio Aesthetic) --- */}
        <div onClick={onEnterStudio} className="mt-32 w-full max-w-4xl mx-auto relative z-20 animate-in fade-in slide-in-from-bottom-24 duration-1000 delay-500 ease-[cubic-bezier(0.16,1,0.3,1)] fill-mode-both group cursor-pointer" title="Click to launch Interactive Audio Studio">
          
          {/* Intense Colorful Aura matching Studio Triad */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[85%] h-[55%] bg-gradient-to-r from-indigo-600 via-fuchsia-500 to-emerald-500 rounded-full blur-[120px] opacity-25 group-hover:opacity-45 transition-opacity duration-1000" />
          
          <div className="relative rounded-[2rem] bg-[#070512]/90 backdrop-blur-3xl border border-white/10 p-2 shadow-[0_0_100px_rgba(0,0,0,1),inset_0_1px_0_rgba(255,255,255,0.1)] transition-all duration-500 group-hover:border-indigo-500/40">
            <div className="bg-[#0a0816] rounded-[1.5rem] border border-white/5 p-6 md:p-8 flex flex-col md:flex-row items-center gap-8 relative overflow-hidden">
              
              {/* Subtle glass reflection */}
              <div className="absolute top-0 left-0 w-full h-1/2 bg-gradient-to-b from-white/[0.03] to-transparent pointer-events-none" />

              <div className="flex-1 w-full relative z-10 text-left">
                <div className="flex justify-between items-start mb-8">
                  <div>
                    <p className="text-[10px] font-mono text-indigo-400 uppercase tracking-widest mb-2 flex items-center">
                      <Sparkles className="w-3 h-3 mr-1" /> Artifact #042 // Rendered
                    </p>
                    <h3 className="text-2xl text-white font-medium tracking-tight">The House That Kept Changing</h3>
                  </div>
                  <div className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center shadow-[0_0_15px_rgba(16,185,129,0.15)]">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-2 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-ping" />
                    <span className="text-[10px] uppercase tracking-widest font-bold text-emerald-300">44.1kHz WAV</span>
                  </div>
                </div>
                
                {/* Minimalist Waveform with Indigo Accent */}
                <div className="h-12 w-full flex items-end space-x-1 opacity-85 group-hover:opacity-100 transition-opacity duration-700 mb-2">
                  {[...Array(64)].map((_, i) => {
                    const height = 10 + Math.random() * 90;
                    const isPlayed = i < 28;
                    return (
                      <div 
                        key={i} 
                        className={`flex-1 rounded-t-sm transition-all duration-500 ${isPlayed ? 'bg-gradient-to-t from-indigo-500 to-fuchsia-400 shadow-[0_0_10px_rgba(168,85,247,0.5)]' : 'bg-white/15'}`}
                        style={{ height: `${height}%` }}
                      />
                    );
                  })}
                </div>
                <div className="flex justify-between text-[10px] font-mono text-slate-400">
                  <span className="text-indigo-300 font-bold">00:24</span>
                  <span>01:45</span>
                </div>
              </div>

              <div className="shrink-0 relative z-10 flex items-center justify-center p-4">
                <button className="relative w-20 h-20 rounded-full flex items-center justify-center bg-gradient-to-tr from-indigo-500 to-fuchsia-500 text-white hover:scale-95 transition-transform duration-500 shadow-[0_0_40px_rgba(168,85,247,0.4)]">
                   <Play className="w-8 h-8 ml-1 fill-current" />
                </button>
              </div>

            </div>
          </div>
        </div>
      </section>

      {/* --- Bento Box Architecture Section --- */}
      <section id="architecture" className="py-32 px-6 relative z-10">
        <div className="max-w-6xl mx-auto">
          <div className="mb-20 max-w-2xl">
            <h2 className="text-sm font-mono text-indigo-400 uppercase tracking-widest mb-4 flex items-center">
              <Layers className="w-4 h-4 mr-2" /> System Architecture
            </h2>
            <p className="text-4xl md:text-5xl font-medium text-white tracking-tight leading-tight">
              A multi-modal pipeline engineered for cinematic scale.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <BentoCard 
              span="md:col-span-2"
              delay="0ms"
              icon={BrainCircuit}
              title="Dream Graph Extraction"
              desc="Raw text is parsed into a multi-layered topological graph. Characters, totems, and emotional states are isolated and mapped across conscious and subconscious layers."
            />
            <BentoCard 
              span="md:col-span-1"
              delay="100ms"
              icon={Cpu}
              title="Emotion Scoring"
              desc="Transformer-based analysis scores every generated line for emotional intensity, dictating pacing and tone."
            />
            <BentoCard 
              span="md:col-span-1"
              delay="200ms"
              icon={Mic}
              title="Voice Direction"
              desc="An autonomous director assigns distinct, steerable voices to cast members, instructing breath, hesitation, and pitch."
            />
            <BentoCard 
              span="md:col-span-2"
              delay="300ms"
              icon={Layers}
              title="Final DSP Assembly"
              desc="Dialogue, procedurally generated ambient beds, and timestamped one-shot foley are mixed. Automated ducking and EQ balance the final master track."
            />
          </div>
        </div>
      </section>

      {/* --- Elegant Footer CTA --- */}
      <section className="py-40 px-6 relative z-10 border-t border-white/5 bg-[#05040a]">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-px bg-gradient-to-r from-transparent via-indigo-500/40 to-transparent" />
        
        <div className="max-w-3xl mx-auto text-center relative z-10">
          <h2 className="text-5xl md:text-6xl font-serif font-medium text-white mb-8 tracking-[-0.02em]">The vault is waiting.</h2>
          <PremiumButton primary onClick={user ? onEnterStudio : onSignIn}>
            {user ? 'Enter Studio' : 'Initialize Your Profile'}
          </PremiumButton>
        </div>
      </section>

      {/* --- Global Styles --- */}
      <style dangerouslySetInnerHTML={{__html: `
        html { scroll-behavior: smooth; }
        
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin-slow { animation: spin-slow 20s linear infinite; }
        
        @keyframes spin-slow-reverse {
          from { transform: rotate(360deg); }
          to { transform: rotate(0deg); }
        }
        .animate-spin-slow-reverse { animation: spin-slow-reverse 25s linear infinite; }

        @keyframes pulse-slow {
          0%, 100% { opacity: 0.3; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(1.1); }
        }
        .animate-pulse-slow { animation: pulse-slow 8s ease-in-out infinite; }

        @keyframes shimmer { 
          100% { transform: translateX(100%); } 
        }
      `}} />
    </div>
  );
}
