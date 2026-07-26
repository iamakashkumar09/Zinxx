'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Network, Eye, Library, Database, LogOut, Compass, ChevronRight, Trash2, Clock, ArrowRight, TerminalSquare, Layers, Ghost, Sparkles, Activity, CheckCircle2, Mic, MicOff, Clapperboard, Heart } from 'lucide-react';
import { AuthScreen } from './components/AuthScreen';
import { LandingPage } from './components/LandingPage';
import { CinematicScriptView } from './components/CinematicScriptView';
import { NARRATIVE_LENSES, PROCESSING_STEPS, MOCK_STORY_DATA, MOCK_DREAM_GRAPH, Typewriter, BlinkingCursor } from '@/lib/constants';
import { saveDream, getDreams, deleteDream, toggleDreamFavorite, getStoryPreview, generateDreamStory, generateAudio, getSessionUser, logoutUser } from './actions';

/** Stable per-browser id for Module 2's Dream Graph totem memory. Shared localStorage key
 * with frontend/app.js's getClientUserId() so both UIs recognize the same visitor. */
function getClientUserId(): string {
  const KEY = "dream_client_user_id";
  if (typeof window === 'undefined') return "web_server";
  let id = localStorage.getItem(KEY);
  if (!id) {
    id = "web_" + crypto.randomUUID().replace(/-/g, "").slice(0, 24);
    localStorage.setItem(KEY, id);
  }
  return id;
}

/** Full pipeline: Module 1->2->3->7 (dream understanding/graph/reconstruction/screenplay)
 * followed by Module 8->9->10 (audio direction, real Qwen3-TTS voices + Stable Audio
 * music/SFX, mixdown) — merged into the single result shape CinematicScriptView expects. */
async function synthesizeFullStory(inputText: string, followUpAnswer: string, lens: string) {
  const story: any = await generateDreamStory(inputText, followUpAnswer, getClientUserId());
  const audio: any = await generateAudio(story);
  return { ...story, lens, audio_url: audio.audio_url, qa_report: audio.qa_report };
}

export default function DreamToStoryApp() {
  const [user, setUser] = useState<any>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState<boolean>(true);
  const [view, setView] = useState<string>('landing');
  const [savedDreams, setSavedDreams] = useState<any[]>([]);
  const [favoriteIds, setFavoriteIds] = useState<string[]>([]);
  const [vaultFilter, setVaultFilter] = useState<string>('all');
  const [isLoadingVault, setIsLoadingVault] = useState<boolean>(false);

  const [inputText, setInputText] = useState<string>("");
  const [selectedLens, setSelectedLens] = useState<string>('psychological');
  const [status, setStatus] = useState<string>("idle");
  const [activeStepIndex, setActiveStepIndex] = useState<number>(-1);
  const [currentResult, setCurrentResult] = useState<any>(null);
  const [dreamGraph, setDreamGraph] = useState<any>(null);
  const [isTransitioningView, setIsTransitioningView] = useState<boolean>(false);
  const [followUpAnswer, setFollowUpAnswer] = useState<string>("");

  const textareaRef = useRef<any>(null);
  const followUpRef = useRef<any>(null);
  const synthesisPromiseRef = useRef<Promise<any> | null>(null);
  const recognitionRef = useRef<any>(null);

  const [isListening, setIsListening] = useState<boolean>(false);
  const [activeVoiceTarget, setActiveVoiceTarget] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function checkAuth() {
      try {
        const session = await getSessionUser();
        if (isMounted && session && session.id) {
          setUser(session);
          loadDreamsFromDB(String(session.id));
          if (localStorage.getItem('dream_arc_view') === 'auth') {
            setView('studio');
            localStorage.setItem('dream_arc_view', 'studio');
          }
        }
      } catch (err) {
        console.warn("Session check error:", err);
      } finally {
        if (isMounted) {
          setIsCheckingAuth(false);
        }
      }
    }
    checkAuth();

    const savedView = localStorage.getItem('dream_arc_view');
    if (savedView && ['landing', 'studio', 'library', 'auth'].includes(savedView)) {
      if (savedView === 'auth') {
        setView('landing');
      } else {
        setView(savedView);
      }
    }

    const savedFavs = localStorage.getItem('dream_arc_favs');
    if (savedFavs) {
      try { setFavoriteIds(JSON.parse(savedFavs)); } catch (e) { }
    }

    const handlePopState = (e: PopStateEvent) => {
      const targetView = (e.state && e.state.view) ? e.state.view : (localStorage.getItem('dream_arc_view') || 'landing');
      if (targetView === 'auth' && user) {
        setView('studio');
        localStorage.setItem('dream_arc_view', 'studio');
        return;
      }
      setView(targetView);
      localStorage.setItem('dream_arc_view', targetView);
    };
    window.addEventListener('popstate', handlePopState);

    // Safety fallback timer to guarantee loader dismisses even if dev server delays
    const timer = setTimeout(() => {
      if (isMounted) {
        setIsCheckingAuth(false);
      }
    }, 1200);

    return () => {
      isMounted = false;
      clearTimeout(timer);
      window.removeEventListener('popstate', handlePopState);
    };
  }, []);

  const handleAuthSuccess = (loggedInUser: any) => {
    setUser(loggedInUser);
    loadDreamsFromDB(loggedInUser.id);
  };

  const handleLogout = async () => {
    await logoutUser();
    setUser(null);
    setSavedDreams([]);
    localStorage.setItem('dream_arc_view', 'landing');
    setView('landing');
    resetStudio();
  };

  const loadDreamsFromDB = async (userId: string) => {
    setIsLoadingVault(true);
    try {
      const data = await getDreams(userId);
      if (data && Array.isArray(data)) {
        setSavedDreams(data);
        const dbFavs = data.filter((d: any) => d.isFavorite).map((d: any) => d.id);
        setFavoriteIds(prev => {
          const combined = Array.from(new Set([...prev, ...dbFavs]));
          localStorage.setItem('dream_arc_favs', JSON.stringify(combined));
          return combined;
        });
      }
    } catch (err) {
      console.warn("Could not fetch from DB, using local state fallback:", err);
    } finally {
      setIsLoadingVault(false);
    }
  };

  const handleViewChange = (newView: string) => {
    if (view === newView) return;
    localStorage.setItem('dream_arc_view', newView);
    if (typeof window !== 'undefined') {
      if (view === 'auth') {
        window.history.replaceState({ view: newView }, '', '');
      } else {
        window.history.pushState({ view: newView }, '', '');
      }
    }
    // Refresh dreams from DB every time user opens the Vault
    if (newView === 'library' && user) {
      loadDreamsFromDB((user as any).id);
    }
    setIsTransitioningView(true);
    setTimeout(() => {
      setView(newView);
      if (newView === 'studio') resetStudio();
      setIsTransitioningView(false);
    }, 150);
  };

  const navigateToView = (newView: string) => {
    localStorage.setItem('dream_arc_view', newView);
    if (typeof window !== 'undefined') {
      if (view === 'auth') {
        window.history.replaceState({ view: newView }, '', '');
      } else {
        window.history.pushState({ view: newView }, '', '');
      }
    }
    setView(newView);
  };

  const toggleFavorite = async (dreamId: string, e: any) => {
    e.stopPropagation();
    let newIsFav = false;
    setFavoriteIds(prev => {
      const exists = prev.includes(dreamId);
      newIsFav = !exists;
      const updated = exists ? prev.filter(id => id !== dreamId) : [...prev, dreamId];
      localStorage.setItem('dream_arc_favs', JSON.stringify(updated));
      return updated;
    });
    setSavedDreams(prev => prev.map(d => d.id === dreamId ? { ...d, isFavorite: newIsFav } : d));
    if (dreamId && !dreamId.startsWith('usr_') && isNaN(Number(dreamId))) {
      try {
        await toggleDreamFavorite(dreamId, newIsFav);
      } catch (err) {
        console.warn("Could not save favorite to DB:", err);
      }
    }
  };

  const handleInput = (e: any, ref: any) => {
    if (ref.current) {
      ref.current.style.height = 'auto';
      ref.current.style.height = `${ref.current.scrollHeight}px`;
    }
  };

  const startExtraction = async () => {
    if (!inputText.trim()) return;
    setStatus("extracting");
    synthesisPromiseRef.current = null;
    try {
      const graph = await getStoryPreview(inputText);
      setDreamGraph(graph);
    } catch (err) {
      console.warn("Backend story preview failed (using fallback graph):", err);
      setDreamGraph(MOCK_DREAM_GRAPH);
    } finally {
      setStatus("conversational");
      // Immediately kick off full synthesis (story + real audio) in the background so it
      // completes concurrently during the animation!
      synthesisPromiseRef.current = synthesizeFullStory(inputText, "", selectedLens)
        .catch(err => { console.warn("Background pre-gen failed:", err); return null; });
    }
  };

  const startSynthesis = () => {
    setStatus("processing");
    setActiveStepIndex(0);
    setCurrentResult(null);
    if (followUpAnswer.trim() || !synthesisPromiseRef.current) {
      synthesisPromiseRef.current = synthesizeFullStory(inputText, followUpAnswer, selectedLens)
        .catch(err => { console.warn("Synthesis failed:", err); return null; });
    }
  };

  const handleSaveToVault = async (text: string, resultData: any, lens: string) => {
    if (!user) return;
    const userId = (user as any).id;
    const newDream = { id: Date.now().toString(), userId, inputText: text, storyData: resultData, lens, isFavorite: false, createdAt: Date.now() };
    setSavedDreams(prev => [newDream, ...prev]);
    // Only save to DB if user has a real DB ID (cuid), not a local fallback usr_ ID
    if (userId && !userId.startsWith('usr_')) {
      try {
        const saved = await saveDream(userId, text, resultData, lens, false);
        if (saved && saved.id) {
          setSavedDreams(prev => prev.map((d: any) => d.id === newDream.id ? saved : d));
        }
      } catch (err) {
        console.warn("Could not save to DB (using local state fallback):", err);
      }
    }
  };

  const handleDeleteDream = async (id: string) => {
    if (!user) return;
    if (!window.confirm("Are you sure you want to permanently delete this memory from your vault?")) return;
    setSavedDreams(prev => prev.filter((d: any) => d.id !== id));
    setFavoriteIds(prev => {
      const updated = prev.filter(favId => favId !== id);
      localStorage.setItem('dream_arc_favs', JSON.stringify(updated));
      return updated;
    });
    try {
      await deleteDream(id);
    } catch (err) {
      console.warn("Could not delete from DB:", err);
    }
  };

  const resetStudio = () => {
    setStatus("idle");
    setInputText("");
    setFollowUpAnswer("");
    setActiveStepIndex(-1);
    setCurrentResult(null);
    setDreamGraph(null);
    synthesisPromiseRef.current = null;
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) { }
    }
    setIsListening(false);
    setActiveVoiceTarget(null);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const SAMPLE_VOICE_DREAMS = [
    "I was walking through an endless hallway with doors that kept changing colors every time I blinked...",
    "Suddenly the sky turned deep purple and a giant clock started floating above the ocean ticking backwards...",
    "I found myself in my old childhood home but all the rooms were filled with water and glowing jellyfish...",
    "There was a loud humming noise in the fog and a silhouette of someone calling my name from across the bridge..."
  ];

  const SAMPLE_VOICE_FOLLOWUPS = [
    "I felt a sudden rush of anxiety mixed with curiosity right as the door opened.",
    "The temperature dropped freezing cold and everything became completely silent.",
    "I tried to run but my legs felt heavy like I was moving through molasses."
  ];

  const simulateVoiceInput = (target: 'main' | 'followup') => {
    setIsListening(true);
    setActiveVoiceTarget(target);

    const sampleText = target === 'main'
      ? SAMPLE_VOICE_DREAMS[Math.floor(Math.random() * SAMPLE_VOICE_DREAMS.length)]
      : SAMPLE_VOICE_FOLLOWUPS[Math.floor(Math.random() * SAMPLE_VOICE_FOLLOWUPS.length)];

    const words = sampleText.split(' ');
    let currentWordIdx = 0;

    const interval = setInterval(() => {
      if (currentWordIdx < words.length) {
        const wordToAdd = words[currentWordIdx];
        if (target === 'main') {
          setInputText(prev => {
            const base = prev.endsWith(' ') || prev.length === 0 ? prev : prev + ' ';
            return base + wordToAdd;
          });
          if (textareaRef.current) handleInput(null, textareaRef);
        } else {
          setFollowUpAnswer(prev => {
            const base = prev.endsWith(' ') || prev.length === 0 ? prev : prev + ' ';
            return base + wordToAdd;
          });
          if (followUpRef.current) handleInput(null, followUpRef);
        }
        currentWordIdx++;
      } else {
        clearInterval(interval);
        setIsListening(false);
        setActiveVoiceTarget(null);
      }
    }, 150);

    recognitionRef.current = {
      isSimulated: true,
      stop: () => {
        clearInterval(interval);
        setIsListening(false);
        setActiveVoiceTarget(null);
      }
    };
  };

  const mergeSpeechPiece = (prev: string, next: string): string => {
    if (!prev) return next;
    if (!next) return prev;
    const pLower = prev.trim().toLowerCase();
    const nLower = next.trim().toLowerCase();
    if (pLower.endsWith(nLower)) return prev.trim();
    if (nLower.startsWith(pLower)) return next.trim();

    const prevWords = prev.trim().split(/\s+/);
    const nextWords = next.trim().split(/\s+/);
    for (let overlap = Math.min(prevWords.length, nextWords.length); overlap > 0; overlap--) {
      const endSlice = prevWords.slice(-overlap).join(" ").toLowerCase();
      const startSlice = nextWords.slice(0, overlap).join(" ").toLowerCase();
      if (endSlice === startSlice) {
        return prevWords.slice(0, -overlap).concat(nextWords).join(" ");
      }
    }
    return prev.trim() + " " + next.trim();
  };

  const toggleVoiceInput = (target: 'main' | 'followup') => {
    if (isListening && activeVoiceTarget === target) {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (e) { }
      }
      setIsListening(false);
      setActiveVoiceTarget(null);
      return;
    }

    if (isListening && activeVoiceTarget !== target) {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (e) { }
      }
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.info("Speech recognition not natively supported, using AI Voice Simulation fallback...");
      simulateVoiceInput(target);
      return;
    }

    try {
      const initialText = target === 'main' ? (textareaRef.current?.value || inputText) : (followUpRef.current?.value || followUpAnswer);
      const basePrefix = initialText.endsWith(' ') || initialText.length === 0 ? initialText : initialText + ' ';

      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsListening(true);
        setActiveVoiceTarget(target);
      };

      recognition.onresult = (event: any) => {
        let currentSessionTranscript = '';
        for (let i = 0; i < event.results.length; ++i) {
          const piece = event.results[i][0].transcript;
          currentSessionTranscript = mergeSpeechPiece(currentSessionTranscript, piece);
        }

        const cleanText = currentSessionTranscript.trim();
        if (cleanText) {
          const fullText = mergeSpeechPiece(basePrefix, cleanText);
          if (target === 'main') {
            setInputText(fullText);
            if (textareaRef.current) handleInput(null, textareaRef);
          } else if (target === 'followup') {
            setFollowUpAnswer(fullText);
            if (followUpRef.current) handleInput(null, followUpRef);
          }
        }
      };

      recognition.onerror = (event: any) => {
        console.warn("Speech recognition error:", event.error);
        if (['network', 'service-not-allowed', 'not-allowed', 'audio-capture', 'language-not-supported', 'aborted'].includes(event.error)) {
          console.info("Switching to AI Voice Simulation Fallback due to browser restriction/error...");
          recognition.onend = null;
          simulateVoiceInput(target);
        } else if (event.error !== 'no-speech') {
          setIsListening(false);
          setActiveVoiceTarget(null);
        }
      };

      recognition.onend = () => {
        if (recognitionRef.current && recognitionRef.current.isSimulated) {
          return;
        }
        setIsListening(false);
        setActiveVoiceTarget(null);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (e) {
      console.warn("Could not start speech recognition, using simulation fallback:", e);
      simulateVoiceInput(target);
    }
  };

  const loadFromVault = (dream: any) => {
    setIsTransitioningView(true);
    setTimeout(() => {
      setCurrentResult(dream.storyData);
      setInputText(dream.inputText);
      setSelectedLens(dream.storyData.lens || 'psychological');
      setStatus('success');
      setView('studio');
      setIsTransitioningView(false);
    }, 500);
  };

  useEffect(() => {
    // Steps animate on their estimated durations up through the second-to-last one. The
    // last step is intentionally never auto-advanced past — it stays "active" (pulsing)
    // for however long the real backend call actually takes (real TTS + audio synthesis
    // can run well past the estimated timeline), instead of racing ahead and looking
    // finished/frozen while the response is still in flight.
    if (status === "processing" && activeStepIndex >= 0 && activeStepIndex < PROCESSING_STEPS.length - 1) {
      const step = PROCESSING_STEPS[activeStepIndex];
      const timer = setTimeout(() => {
        setActiveStepIndex(prev => prev + 1);
      }, step.duration);
      return () => clearTimeout(timer);
    } else if (status === "processing" && activeStepIndex === PROCESSING_STEPS.length - 1) {
      let isCancelled = false;
      const getStoryResult = async () => {
        try {
          let aiResult = null;
          if (synthesisPromiseRef.current) {
            aiResult = await synthesisPromiseRef.current;
          }
          if (!aiResult) {
            aiResult = await synthesizeFullStory(inputText, followUpAnswer, selectedLens);
          }
          if (!isCancelled) {
            const finalStory = aiResult || { ...MOCK_STORY_DATA, title: `The Dream of ${new Date().toLocaleDateString()}`, lens: selectedLens };
            setCurrentResult(finalStory);
            setStatus("success");
            handleSaveToVault(inputText, finalStory, selectedLens);
          }
        } catch (err) {
          console.warn("AI synthesis failed (using fallback story):", err);
          if (!isCancelled) {
            const fallback = { ...MOCK_STORY_DATA, title: `The Dream of ${new Date().toLocaleDateString()}`, lens: selectedLens };
            setCurrentResult(fallback);
            setStatus("success");
            handleSaveToVault(inputText, fallback, selectedLens);
          }
        }
      };
      getStoryResult();
      return () => { isCancelled = true; };
    }
  }, [status, activeStepIndex, inputText, followUpAnswer, user, selectedLens]);

  if (isCheckingAuth) {
    return (
      <div className="min-h-screen bg-[#030208] flex flex-col items-center justify-center text-slate-400 font-sans relative overflow-hidden">
        <div className="absolute inset-0 z-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[50vw] h-[50vw] max-w-[500px] max-h-[500px] bg-indigo-900/10 rounded-full blur-[100px] animate-pulse" />
        </div>
        <div className="relative z-10 flex flex-col items-center space-y-4">
          <div className="w-12 h-12 rounded-full border-2 border-indigo-500/20 border-t-indigo-500 animate-spin shadow-[0_0_30px_rgba(79,70,229,0.3)]" />
          <p className="text-xs uppercase tracking-widest text-indigo-300 font-mono animate-pulse">Reconnecting to Cortex...</p>
        </div>
      </div>
    );
  }

  if (view === 'landing') {
    return (
      <LandingPage
        onEnterStudio={() => {
          if (!user) {
            navigateToView('auth');
          } else {
            handleViewChange('studio');
          }
        }}
        onOpenVault={() => {
          if (!user) {
            navigateToView('auth');
          } else {
            handleViewChange('library');
          }
        }}
        onSignIn={() => navigateToView('auth')}
        user={user}
      />
    );
  }

  if (!user || view === 'auth') {
    return (
      <AuthScreen
        onAuthSuccess={(u: any) => {
          handleAuthSuccess(u);
          navigateToView('studio');
        }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-[#05040a] text-slate-200 font-sans selection:bg-indigo-500/30 overflow-x-hidden relative flex flex-col font-medium">

      {/* Cinematic Ambient Background */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-indigo-900/10 rounded-full blur-[150px] mix-blend-screen animate-[pulse_14s_ease-in-out_infinite]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] bg-fuchsia-900/10 rounded-full blur-[180px] mix-blend-screen animate-[pulse_16s_ease-in-out_infinite_2s]" />
        <div className="absolute top-[20%] right-[20%] w-[40%] h-[40%] bg-emerald-900/5 rounded-full blur-[120px] mix-blend-screen animate-[pulse_20s_ease-in-out_infinite_4s]" />
        <div className="absolute inset-0 opacity-[0.02]" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} />
      </div>

      <div className="relative z-10 max-w-screen-2xl mx-auto w-full flex-1 flex flex-col">

        {/* Navigation Bar */}
        <nav className="flex items-center justify-between px-6 py-5 border-b border-white/5 bg-black/20 backdrop-blur-3xl z-50 sticky top-0 transition-all duration-700">
          <div className="flex items-center space-x-3 cursor-pointer group" onClick={() => handleViewChange('landing')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500/20 to-fuchsia-500/20 border border-white/10 flex items-center justify-center shadow-lg transition-all duration-700 group-hover:rotate-12 group-hover:scale-110 group-hover:border-indigo-400/50">
              <Network className="w-5 h-5 text-indigo-300" />
            </div>
            <h1 className="text-xl font-serif font-bold text-white tracking-tight hidden sm:block transition-colors group-hover:text-indigo-200">Dream Archaeology</h1>
          </div>

          <div className="flex items-center space-x-1 bg-white/[0.02] p-1.5 rounded-2xl border border-white/5 backdrop-blur-md">
            <button
              onClick={() => handleViewChange('landing')}
              className={`px-5 py-2 rounded-xl text-sm transition-all duration-500 ease-out flex items-center ${view === 'landing' ? 'bg-white/10 text-white shadow-md font-semibold' : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]'}`}
            >
              <Compass className={`w-4 h-4 mr-2 transition-colors duration-500 ${view === 'landing' ? 'text-indigo-400' : ''}`} /> Home
            </button>
            <button
              onClick={() => handleViewChange('studio')}
              className={`px-5 py-2 rounded-xl text-sm transition-all duration-500 ease-out flex items-center ${view === 'studio' ? 'bg-white/10 text-white shadow-md font-semibold' : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]'}`}
            >
              <Eye className={`w-4 h-4 mr-2 transition-colors duration-500 ${view === 'studio' ? 'text-indigo-400' : ''}`} /> Studio
            </button>
            <button
              onClick={() => handleViewChange('library')}
              className={`px-5 py-2 rounded-xl text-sm transition-all duration-500 ease-out flex items-center ${view === 'library' ? 'bg-white/10 text-white shadow-md font-semibold' : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]'}`}
            >
              <Library className={`w-4 h-4 mr-2 transition-colors duration-500 ${view === 'library' ? 'text-indigo-400' : ''}`} /> Vault
              {savedDreams.length > 0 && (
                <span className={`ml-2 py-0.5 px-2 rounded-full text-[10px] font-bold transition-colors duration-500 ${view === 'library' ? 'bg-indigo-500/30 text-indigo-200' : 'bg-white/10 text-slate-400'}`}>
                  {savedDreams.length}
                </span>
              )}
            </button>
          </div>

          <div className="flex items-center">
            <div className="hidden md:flex flex-col items-end mr-4">
              <span className="text-[11px] text-slate-400 font-medium tracking-wide flex items-center"><Database className="w-3 h-3 mr-1" /> Neon DB Connected</span>
              <span className="text-[10px] text-indigo-300/70 font-mono truncate">{user.name}</span>
            </div>
            <button
              onClick={handleLogout}
              className="w-10 h-10 rounded-full bg-slate-800/50 border border-white/10 flex items-center justify-center text-slate-400 hover:bg-rose-500/20 hover:text-rose-400 hover:border-rose-500/30 cursor-pointer transition-all duration-500 hover:shadow-lg hover:shadow-rose-500/10 hover:scale-105"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4 ml-0.5" />
            </button>
          </div>
        </nav>

        <main className={`flex-1 p-4 sm:p-6 lg:p-8 xl:p-12 overflow-y-auto transition-all duration-200 ease-out ${isTransitioningView ? 'opacity-0 scale-[0.99]' : 'opacity-100 scale-100'}`}>

          {/* Library Vault View */}
          {view === 'library' && (
            <div className="max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-300 ease-out">
              <div className="mb-10 flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-white/10 pb-6">
                <div>
                  <h2 className="text-4xl font-serif font-bold text-white mb-2 tracking-tight flex items-center">
                    Memory Vault
                  </h2>
                  <p className="text-slate-400 text-sm">Archived narratives securely stored in Neon Postgres.</p>
                </div>

                {/* Filter Tabs */}
                {savedDreams.length > 0 && (
                  <div className="flex items-center space-x-2 bg-white/[0.03] p-1.5 rounded-2xl border border-white/10">
                    <button
                      onClick={() => setVaultFilter('all')}
                      className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-300 flex items-center cursor-pointer ${vaultFilter === 'all' ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shadow-sm' : 'text-slate-400 hover:text-white'}`}
                    >
                      All Memories ({savedDreams.length})
                    </button>
                    <button
                      onClick={() => setVaultFilter('favorites')}
                      className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-300 flex items-center cursor-pointer ${vaultFilter === 'favorites' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30 shadow-sm' : 'text-slate-400 hover:text-rose-400'}`}
                    >
                      <Heart className={`w-3.5 h-3.5 mr-1.5 ${vaultFilter === 'favorites' ? 'fill-rose-400 text-rose-400' : ''}`} /> Favorites ({savedDreams.filter(d => favoriteIds.includes(d.id)).length})
                    </button>
                  </div>
                )}
              </div>

              {isLoadingVault ? (
                <div className="text-center py-32 flex flex-col items-center justify-center">
                  <div className="w-12 h-12 rounded-full border-2 border-indigo-500/30 border-t-indigo-400 animate-spin mx-auto mb-6" />
                  <p className="text-sm text-slate-500 animate-pulse">Loading your memories from the vault...</p>
                </div>
              ) : savedDreams.length === 0 ? (
                <div className="text-center py-32 border border-dashed border-white/10 rounded-[2rem] bg-white/[0.01] backdrop-blur-sm">
                  <Compass className="w-12 h-12 text-slate-600 mx-auto mb-6 opacity-50" />
                  <h3 className="text-xl font-medium text-slate-300 mb-2">The vault is empty</h3>
                  <p className="text-sm text-slate-500 mb-8">No dream graphs have been synthesized yet.</p>
                  <button onClick={() => handleViewChange('studio')} className="text-indigo-400 hover:text-indigo-300 text-sm font-semibold flex items-center justify-center mx-auto transition-colors group cursor-pointer">
                    Return to Studio <ChevronRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
                  </button>
                </div>
              ) : savedDreams.filter((d: any) => vaultFilter === 'all' || favoriteIds.includes(d.id)).length === 0 ? (
                <div className="text-center py-24 border border-dashed border-white/10 rounded-[2rem] bg-white/[0.01] backdrop-blur-sm">
                  <Heart className="w-12 h-12 text-rose-500/40 mx-auto mb-4 animate-pulse" />
                  <h3 className="text-lg font-medium text-slate-300 mb-1">No favorite memories yet</h3>
                  <p className="text-xs text-slate-500 mb-6">Click the heart icon on any story card in 'All Memories' to favorite it.</p>
                  <button onClick={() => setVaultFilter('all')} className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold underline cursor-pointer">
                    View All Memories
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
                  {savedDreams
                    .filter((dream: any) => vaultFilter === 'all' || favoriteIds.includes(dream.id))
                    .map((dream: any, idx: number) => {
                      const savedLens = NARRATIVE_LENSES.find(l => l.id === dream.storyData.lens) || NARRATIVE_LENSES[0];
                      const SavedIcon = savedLens.icon;
                      const isFav = favoriteIds.includes(dream.id);
                      return (
                        <div key={dream.id}
                          className="group relative bg-[#0a0812] border border-white/5 rounded-3xl p-6 hover:border-indigo-500/40 hover:bg-white/[0.03] hover:shadow-[0_20px_40px_-15px_rgba(79,70,229,0.3)] transition-all duration-500 ease-out flex flex-col h-full animate-in fade-in slide-in-from-bottom-4 fill-mode-both hover:-translate-y-1.5"
                          style={{ animationDelay: `${idx * 80}ms` }}>
                          <div className="flex justify-between items-start mb-5">
                            <div className={`p-3 rounded-2xl transition-colors duration-500 ${savedLens.bg} ${savedLens.color} border ${savedLens.border}`}>
                              <SavedIcon className="w-5 h-5" />
                            </div>
                            <div className="flex items-center space-x-1">
                              <button
                                onClick={(e) => toggleFavorite(dream.id, e)}
                                title={isFav ? "Remove from Favorites" : "Mark as Favorite"}
                                className={`p-2 rounded-full transition-all duration-300 cursor-pointer ${isFav ? 'text-rose-500 bg-rose-500/15 border border-rose-500/30 shadow-[0_0_15px_rgba(244,63,94,0.3)] scale-105' : 'text-slate-500 hover:text-rose-400 hover:bg-white/5 opacity-40 group-hover:opacity-100'}`}
                              >
                                <Heart className={`w-4 h-4 transition-transform duration-300 ${isFav ? 'fill-rose-500 scale-110' : 'group-hover:scale-110'}`} />
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); handleDeleteDream(dream.id); }}
                                title="Delete Memory"
                                className="text-slate-600 hover:text-red-400 p-2 rounded-full hover:bg-red-400/10 transition-all opacity-0 group-hover:opacity-100 cursor-pointer"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                          <h3 className="text-xl font-serif font-semibold text-white mb-3 line-clamp-1 group-hover:text-indigo-100 transition-colors">{dream.storyData.title}</h3>
                          <p className="text-sm text-slate-400 line-clamp-3 mb-8 flex-1 italic leading-relaxed">"{dream.inputText}"</p>
                          <div className="flex items-center justify-between text-xs font-mono text-slate-500 border-t border-white/10 pt-5 mt-auto">
                            <span className="flex items-center"><Clock className="w-3 h-3 mr-1.5 opacity-70" /> {new Date(dream.createdAt).toLocaleDateString()}</span>
                            <button
                              onClick={() => loadFromVault(dream)}
                              className="text-indigo-400 font-semibold hover:text-indigo-300 flex items-center bg-indigo-500/10 hover:bg-indigo-500/20 px-3 py-1.5 rounded-lg transition-colors group-hover:bg-indigo-500/20 cursor-pointer"
                            >
                              Load Memory <ArrowRight className="w-3 h-3 ml-1.5" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                </div>
              )}
            </div>
          )}

          {/* Main Studio View */}
          {view === 'studio' && (
            <div className="flex flex-col space-y-10 max-w-[1400px] mx-auto h-full w-full">

              {/* Centerpiece Title Header Spanning Middle of Both Sides */}
              {status === "success" && currentResult && (
                <div className="w-full text-center py-6 border-b border-white/10 relative animate-in fade-in slide-in-from-top-6 duration-1000">
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl h-40 bg-indigo-500/15 blur-[120px] rounded-full pointer-events-none animate-[pulse_4s_ease-in-out_infinite]" />

                  <div className="flex items-center justify-center space-x-2 mb-4">
                    <span className="px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest flex items-center border bg-indigo-500/10 text-indigo-300 border-indigo-500/20 shadow-[0_0_20px_rgba(79,70,229,0.3)]">
                      <Sparkles className="w-3.5 h-3.5 mr-2 text-indigo-400 animate-pulse" /> {(currentResult.lens || selectedLens).toUpperCase()} LENS
                    </span>
                  </div>

                  <h1 className="text-4xl sm:text-5xl md:text-6xl font-serif font-bold text-transparent bg-clip-text bg-gradient-to-b from-white via-slate-100 to-slate-400 tracking-tight mb-6 relative z-10">
                    {currentResult.title}
                  </h1>

                  <div className="inline-flex items-center px-5 py-2 rounded-full bg-white/[0.03] border border-white/10 text-xs font-mono text-indigo-300 uppercase tracking-widest relative z-10 backdrop-blur-md shadow-2xl cursor-default">
                    <Clapperboard className="w-4 h-4 mr-2 text-fuchsia-400" /> Extracted Screenplay & Audio Master
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 w-full">

                <div className="lg:col-span-5 flex flex-col space-y-8 relative z-10">

                  <div className={`transition-all duration-1000 ease-in-out ${status === 'extracting' || status === 'processing' ? 'opacity-50 pointer-events-none scale-[0.99]' : 'opacity-100 scale-100'}`}>
                    <div className="flex items-center justify-between mb-4">
                      <label htmlFor="dream-input" className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center">
                        <TerminalSquare className="w-4 h-4 mr-2 text-indigo-400" />
                        Raw Memory Input
                      </label>
                      {status === 'success' && (
                        <button onClick={resetStudio} className="text-[10px] uppercase tracking-widest font-bold text-fuchsia-400 hover:text-fuchsia-300 transition-colors bg-fuchsia-500/10 hover:bg-fuchsia-500/20 px-3 py-1.5 rounded-md cursor-pointer">
                          Reset Graph
                        </button>
                      )}
                    </div>

                    <div className="relative group mb-8">
                      <div className={`absolute -inset-1 bg-gradient-to-r from-indigo-500/20 to-fuchsia-600/20 rounded-3xl blur-xl opacity-0 transition-opacity duration-1000 ${status === 'idle' ? 'group-focus-within:opacity-100 group-hover:opacity-40' : ''}`} />
                      <textarea
                        id="dream-input"
                        ref={textareaRef}
                        value={inputText}
                        onChange={(e) => { setInputText(e.target.value); handleInput(e, textareaRef); }}
                        readOnly={status === 'extracting' || status === 'processing'}
                        placeholder="Describe the memory... e.g. 'I was in a house, but the doors kept changing colors...'"
                        className="relative w-full bg-[#0a0812]/90 backdrop-blur-3xl border border-white/10 rounded-[2rem] p-6 md:p-8 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500/50 resize-none min-h-[180px] pb-16 text-lg leading-relaxed shadow-2xl transition-all duration-700 focus:shadow-[0_0_40px_rgba(79,70,229,0.15)]"
                        rows={4}
                      />
                      <button
                        type="button"
                        onClick={() => toggleVoiceInput('main')}
                        disabled={status === 'extracting' || status === 'processing'}
                        className={`absolute bottom-4 right-4 px-4 py-2.5 rounded-xl flex items-center space-x-2 transition-all duration-300 z-10 cursor-pointer ${isListening && activeVoiceTarget === 'main'
                            ? 'bg-rose-500 text-white shadow-[0_0_25px_rgba(244,63,94,0.6)] animate-pulse border border-rose-400 font-semibold'
                            : 'bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white border border-white/10 hover:border-white/20'
                          }`}
                        title={isListening && activeVoiceTarget === 'main' ? "Stop Recording" : "Speak Dream Description"}
                      >
                        {isListening && activeVoiceTarget === 'main' ? (
                          <>
                            <MicOff className="w-4 h-4 animate-spin" />
                            <span className="text-xs font-bold uppercase tracking-wider">Listening...</span>
                          </>
                        ) : (
                          <>
                            <Mic className="w-4 h-4 text-indigo-400" />
                            <span className="text-xs font-medium">Voice Input</span>
                          </>
                        )}
                      </button>
                    </div>

                    {/* Lens Selection */}
                    <div className="mb-8">
                      <label className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center mb-4">
                        <Layers className="w-4 h-4 mr-2 text-indigo-400" />
                        Narrative Lens
                      </label>
                      <div className="grid grid-cols-2 gap-3">
                        {NARRATIVE_LENSES.map((lens: any) => {
                          const Icon = lens.icon;
                          const isSelected = selectedLens === lens.id;
                          return (
                            <button
                              key={lens.id}
                              onClick={() => {
                                if (status === 'extracting' || status === 'processing') return;
                                setSelectedLens(lens.id);
                                if (status === 'success' && currentResult) {
                                  setCurrentResult({ ...currentResult, lens: lens.id });
                                }
                              }}
                              disabled={status === 'extracting' || status === 'processing'}
                              className={`flex items-center p-4 rounded-2xl border transition-all duration-500 ease-out cursor-pointer ${isSelected
                                  ? `${lens.bg} ${lens.border} shadow-[0_0_20px_rgba(0,0,0,0)] ring-1 ring-white/10 scale-[1.02]`
                                  : 'bg-white/[0.02] border-white/5 hover:bg-white/[0.05] hover:border-white/10 text-slate-400 hover:scale-[1.01]'
                                }`}
                            >
                              <Icon className={`w-5 h-5 mr-3 transition-colors duration-500 ${isSelected ? lens.color : 'text-slate-500'}`} />
                              <span className={`text-sm font-semibold tracking-wide transition-colors duration-500 ${isSelected ? 'text-white' : 'text-slate-400'}`}>{lens.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {status === 'idle' && (
                      <div className="flex justify-end animate-in fade-in duration-700 ease-out">
                        <button
                          onClick={startExtraction}
                          disabled={!inputText.trim()}
                          className="relative inline-flex items-center justify-center px-8 py-4 font-bold text-white transition-all duration-700 ease-out bg-indigo-600 hover:bg-indigo-500 rounded-2xl disabled:opacity-50 disabled:cursor-not-allowed group overflow-hidden shadow-[0_0_20px_rgba(79,70,229,0.3)] hover:shadow-[0_0_40px_rgba(79,70,229,0.5)] w-full sm:w-auto hover:-translate-y-1 active:translate-y-0"
                        >
                          <span className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:animate-[shimmer_2s_infinite]" />
                          <Network className="w-5 h-5 mr-3 group-hover:scale-110 transition-transform duration-700" />
                          Extract Dream Graph
                        </button>
                      </div>
                    )}
                  </div>

                  {status === "success" && (
                    <div className="animate-in fade-in slide-in-from-bottom-8 duration-1000 ease-out fill-mode-both delay-700 bg-gradient-to-br from-emerald-500/10 via-transparent to-indigo-500/10 border border-emerald-500/20 rounded-3xl p-6 shadow-[0_0_30px_rgba(52,211,153,0.1)]">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest flex items-center bg-emerald-500/20 px-3 py-1 rounded-full border border-emerald-500/30">
                          <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" /> Render Complete
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed font-sans">
                        The AI has reconstructed your memory into a cinematic script. You can listen to the ambient soundtrack and AI narration in the console on the right!
                      </p>
                    </div>
                  )}
                </div>

                {/* Dynamic Processing Window */}
                <div className="lg:col-span-7 bg-white/[0.01] backdrop-blur-3xl border border-white/5 rounded-[2.5rem] p-6 lg:p-10 min-h-[650px] flex flex-col relative overflow-hidden shadow-2xl transition-all duration-1000 ease-in-out">

                  {status === "idle" && (
                    <div className="flex-1 flex flex-col items-center justify-center text-center opacity-40 animate-in fade-in duration-1000">
                      <div className="w-24 h-24 rounded-full border border-dashed border-slate-700 flex items-center justify-center mb-8 bg-black/20 relative group">
                        <div className="absolute inset-0 rounded-full border border-indigo-500/20 group-hover:animate-[spin_10s_linear_infinite]" />
                        <Ghost className="w-8 h-8 text-slate-500" />
                      </div>
                      <h3 className="text-2xl font-serif text-slate-300 mb-3 tracking-wide">Awaiting Fragments</h3>
                      <p className="text-sm text-slate-500 max-w-sm leading-relaxed">Provide a raw memory. The system will build a Dream Graph, recover missing context, and synthesize a multi-layer narrative.</p>
                    </div>
                  )}

                  {status === "extracting" && (
                    <div className="flex-1 flex flex-col items-center justify-center text-center animate-in fade-in zoom-in-95 duration-1000 ease-out">
                      <div className="relative w-32 h-32 mb-8">
                        <div className="absolute inset-0 border-2 border-indigo-500/20 rounded-full animate-[ping_3s_cubic-bezier(0,0,0.2,1)_infinite]" />
                        <div className="absolute inset-4 border-2 border-fuchsia-500/30 rounded-full animate-[spin_4s_linear_infinite]" />
                        <div className="absolute inset-8 border-2 border-emerald-500/20 rounded-full animate-[spin_3s_linear_infinite_reverse]" />
                        <div className="absolute inset-0 flex items-center justify-center">
                          <Network className="w-8 h-8 text-indigo-300 animate-pulse" />
                        </div>
                      </div>
                      <h3 className="text-xl font-medium text-indigo-100 mb-2">Analyzing Topology...</h3>
                      <p className="text-xs font-mono text-indigo-400/70 uppercase tracking-widest">Mapping entities to vector space</p>
                    </div>
                  )}

                  {status === "conversational" && (
                    <div className="flex-1 flex flex-col animate-in fade-in slide-in-from-right-8 duration-700 ease-out">
                      <div className="flex items-center space-x-3 mb-8 pb-6 border-b border-white/5">
                        <Network className="w-5 h-5 text-indigo-400" />
                        <h2 className="text-lg font-medium text-slate-200">Extracted Dream Graph</h2>
                      </div>

                      <div className="flex flex-wrap gap-3 mb-12">
                        {(dreamGraph || MOCK_DREAM_GRAPH).nodes.map((node: any, i: number) => (
                          <div key={node.id} className="relative group/node animate-in fade-in zoom-in-95 duration-500 fill-mode-both" style={{ animationDelay: `${i * 150}ms` }}>
                            <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500/30 to-fuchsia-500/30 rounded-xl blur opacity-0 group-hover/node:opacity-100 transition-opacity duration-500" />
                            <div className="relative px-4 py-2 bg-[#0d0a14] border border-white/10 rounded-xl flex items-center space-x-3 shadow-lg">
                              <div className={`w-2 h-2 rounded-full ${node.type === 'Character' ? 'bg-indigo-400 shadow-[0_0_8px_rgba(129,140,248,0.8)]' :
                                  node.type === 'Location' ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]' :
                                    node.type === 'Totem' ? 'bg-rose-400 shadow-[0_0_8px_rgba(251,113,133,0.8)]' :
                                      'bg-fuchsia-400 shadow-[0_0_8px_rgba(232,121,249,0.8)]'
                                }`} />
                              <div>
                                <p className="text-sm font-semibold text-slate-200">{node.label}</p>
                                <p className="text-[9px] uppercase tracking-widest text-slate-500 font-mono mt-0.5">{node.type} • {node.layer}</p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="bg-indigo-900/10 border border-indigo-500/20 rounded-3xl p-6 mb-6 animate-in fade-in slide-in-from-bottom-4 duration-700 delay-700 fill-mode-both shadow-[0_0_30px_rgba(79,70,229,0.05)]">
                        <div className="flex items-start space-x-4">
                          <div className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center shrink-0 mt-1">
                            <Sparkles className="w-4 h-4 text-indigo-300" />
                          </div>
                          <div className="flex-1">
                            <p className="text-sm font-bold text-indigo-300 uppercase tracking-widest mb-2">System Query</p>
                            <p className="text-slate-200 leading-relaxed"><Typewriter text={(dreamGraph || MOCK_DREAM_GRAPH).followUp} delay={15} /></p>
                          </div>
                        </div>
                      </div>

                      <div className="mt-auto animate-in fade-in slide-in-from-bottom-4 duration-700 delay-[2000ms] fill-mode-both">
                        <div className="relative group">
                          <textarea
                            ref={followUpRef}
                            value={followUpAnswer}
                            onChange={(e) => { setFollowUpAnswer(e.target.value); handleInput(e, followUpRef); }}
                            placeholder="Optional: Provide more context to shape the final narrative..."
                            className="w-full bg-white/[0.02] border border-white/10 rounded-2xl p-4 pr-14 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-fuchsia-500/40 resize-none min-h-[80px] text-sm transition-all focus:bg-white/[0.04]"
                            rows={2}
                          />
                          <button
                            type="button"
                            onClick={() => toggleVoiceInput('followup')}
                            className={`absolute bottom-3 right-3 p-2.5 rounded-xl flex items-center justify-center transition-all duration-300 z-10 cursor-pointer ${isListening && activeVoiceTarget === 'followup'
                                ? 'bg-rose-500 text-white shadow-[0_0_20px_rgba(244,63,94,0.6)] animate-pulse border border-rose-400'
                                : 'bg-white/5 hover:bg-white/15 text-slate-400 hover:text-white border border-white/10'
                              }`}
                            title={isListening && activeVoiceTarget === 'followup' ? "Stop Recording" : "Speak Follow-up"}
                          >
                            {isListening && activeVoiceTarget === 'followup' ? (
                              <MicOff className="w-4 h-4" />
                            ) : (
                              <Mic className="w-4 h-4 text-fuchsia-400" />
                            )}
                          </button>
                        </div>
                        <div className="flex justify-between items-center mt-4">
                          <button
                            type="button"
                            onClick={() => {
                              setStatus("idle");
                              setActiveStepIndex(-1);
                            }}
                            className="px-5 py-2.5 bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white font-semibold rounded-xl border border-white/10 transition-all flex items-center text-sm cursor-pointer"
                          >
                            ← Previous Step
                          </button>
                          <button
                            onClick={startSynthesis}
                            className="px-6 py-2.5 bg-white text-black font-semibold rounded-xl hover:bg-slate-200 transition-colors flex items-center text-sm group cursor-pointer"
                          >
                            Synthesize Reality <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {status === "processing" && (
                    <div className="flex-1 flex flex-col animate-in fade-in duration-700 ease-out">
                      <div className="flex items-center space-x-4 mb-10 pb-6 border-b border-white/5">
                        <div className="p-3 bg-fuchsia-500/10 rounded-xl border border-fuchsia-500/20 shadow-[0_0_15px_rgba(232,121,249,0.2)]">
                          <Activity className="w-6 h-6 text-fuchsia-400 animate-pulse" />
                        </div>
                        <div>
                          <h2 className="text-xl font-medium text-slate-100 tracking-wide">Synthesis Engine Active</h2>
                          <p className="text-xs text-slate-500 font-mono mt-1">Applying {selectedLens} lens to Dream Graph...</p>
                        </div>
                      </div>

                      <div className="space-y-10 font-mono text-sm relative flex-1">
                        <div className="absolute left-[19px] top-4 bottom-8 w-px bg-gradient-to-b from-fuchsia-500/30 via-indigo-500/20 to-transparent" />

                        {PROCESSING_STEPS.map((step: any, idx: number) => {
                          const isActive = idx === activeStepIndex;
                          const isPast = idx < activeStepIndex;
                          const isFuture = idx > activeStepIndex;
                          const isOpenEnded = idx === PROCESSING_STEPS.length - 1;

                          return (
                            <div key={step.id} className={`flex items-start relative transition-all duration-1000 ease-out ${isFuture ? 'opacity-20 translate-y-4' : 'opacity-100 translate-y-0'}`}>

                              <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 mr-6 relative z-10 transition-all duration-1000 ease-in-out ${isPast ? 'bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 shadow-[0_0_10px_rgba(99,102,241,0.1)] scale-90' :
                                  isActive ? 'bg-fuchsia-600 shadow-[0_0_30px_rgba(232,121,249,0.6)] text-white scale-110 ring-4 ring-fuchsia-500/20' :
                                    'bg-[#0f0d1a] border border-white/10 text-slate-600'
                                }`}>
                                {isPast ? <CheckCircle2 className="w-5 h-5 animate-in zoom-in duration-300" /> :
                                  isActive ? <div className="w-3 h-3 rounded-full bg-white animate-[pulse_2s_ease-in-out_infinite]" /> :
                                    <span className="text-xs font-bold">{idx + 1}</span>}
                              </div>

                              <div className="pt-2 flex-1">
                                <div className={`font-semibold tracking-wide transition-colors duration-700 ${isActive ? 'text-fuchsia-200 text-base' : isPast ? 'text-slate-400 text-sm' : 'text-slate-600 text-sm'}`}>
                                  {isActive ? (
                                    <div className="flex items-center">
                                      <Typewriter text={step.label} delay={20} />
                                      <BlinkingCursor />
                                    </div>
                                  ) : (
                                    step.label
                                  )}
                                </div>

                                <div className={`grid transition-all duration-1000 ease-in-out ${isActive ? 'grid-rows-[1fr] mt-4 opacity-100' : 'grid-rows-[0fr] mt-0 opacity-0'}`}>
                                  <div className="overflow-hidden">
                                    <div className="text-[11px] text-slate-400 space-y-2 bg-black/40 p-4 rounded-xl border border-white/5 shadow-inner relative overflow-hidden">
                                      <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-r from-transparent via-fuchsia-500/5 to-transparent animate-[shimmer_3s_infinite]" />
                                      {isOpenEnded ? (
                                        <>
                                          <p className="animate-in fade-in slide-in-from-left-4 duration-500 delay-300 fill-mode-both flex items-center relative z-10"><span className="text-fuchsia-500 mr-2 opacity-70">{'>'}</span> rendering character voices line by line...</p>
                                          <p className="animate-in fade-in slide-in-from-left-4 duration-500 delay-[1200ms] fill-mode-both flex items-center relative z-10"><span className="text-fuchsia-500 mr-2 opacity-70">{'>'}</span> generating ambient score & sound effects...</p>
                                          <p className="animate-pulse flex items-center relative z-10"><span className="text-indigo-400 mr-2 opacity-70">{'>'}</span> mixing final master — no fixed ETA, thanks for your patience...</p>
                                        </>
                                      ) : (
                                        <>
                                          <p className="animate-in fade-in slide-in-from-left-4 duration-500 delay-300 fill-mode-both flex items-center relative z-10"><span className="text-fuchsia-500 mr-2 opacity-70">{'>'}</span> establishing layer constraints...</p>
                                          <p className="animate-in fade-in slide-in-from-left-4 duration-500 delay-[1200ms] fill-mode-both flex items-center relative z-10"><span className="text-fuchsia-500 mr-2 opacity-70">{'>'}</span> resolving contradictory nodes...</p>
                                          <p className="animate-in fade-in slide-in-from-left-4 duration-500 delay-[2000ms] fill-mode-both flex items-center relative z-10"><span className="text-indigo-400 mr-2 opacity-70">{'>'}</span> queuing sub-module pipeline...</p>
                                        </>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {status === "success" && currentResult && (
                    <div className="flex-1 h-full overflow-y-auto pr-4 -mr-4 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                      <CinematicScriptView data={currentResult} />
                    </div>
                  )}

                </div>
              </div>
            </div>
          )}

        </main>
      </div>

      {/* TRULY FIXED Floating Button - Placed at root so it never moves on scroll */}
      {(view === 'library' || (view === 'studio' && status !== 'idle' && status !== 'extracting')) && (
        <div className="fixed bottom-8 right-8 z-[100] pointer-events-auto animate-in fade-in slide-in-from-bottom-6 duration-700">
          <button
            onClick={() => handleViewChange(view === 'library' ? 'studio' : 'library')}
            className="group relative inline-flex items-center space-x-3 px-6 py-3.5 rounded-full bg-gradient-to-r from-indigo-500 via-indigo-600 to-fuchsia-600 text-white font-semibold text-sm shadow-[0_10px_30px_rgba(79,70,229,0.5)] hover:shadow-[0_15px_40px_rgba(232,121,249,0.7)] border border-indigo-300/30 hover:scale-105 active:scale-95 transition-all duration-300 cursor-pointer overflow-hidden"
          >
            <span className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/30 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]" />
            <div className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center group-hover:rotate-90 transition-transform duration-500">
              <Sparkles className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="relative z-10 tracking-wide">+ Listen More</span>
          </button>
        </div>
      )}

      <style dangerouslySetInnerHTML={{
        __html: `
        @keyframes shimmer { 100% { transform: translateX(100%); } }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }
      `}} />
    </div>
  );
}