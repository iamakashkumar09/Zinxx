import React, { useState, useEffect, useRef } from 'react';
import { Network, Eye, Library, Database, LogOut, Compass, ChevronRight, Trash2, Clock, ArrowRight, TerminalSquare, Layers, Ghost, Sparkles, Activity } from 'lucide-react';
import { AuthScreen } from './components/AuthScreen';
import { CinematicAudioPlayer } from './components/CinematicAudioPlayer';
import { CinematicScriptView } from './components/CinematicScriptView';
import { NARRATIVE_LENSES, PROCESSING_STEPS, MOCK_STORY_DATA, MOCK_DREAM_GRAPH } from './lib/constants';
import { saveDream, getDreams, deleteDream } from './actions';

export default function DreamToStoryApp() {
  const [user, setUser] = useState(null);
  const [view, setView] = useState('studio'); 
  const [savedDreams, setSavedDreams] = useState([]);
  
  const [inputText, setInputText] = useState("");
  const [selectedLens, setSelectedLens] = useState('psychological');
  const [status, setStatus] = useState("idle"); 
  const [activeStepIndex, setActiveStepIndex] = useState(-1);
  const [currentResult, setCurrentResult] = useState(null);
  const [isTransitioningView, setIsTransitioningView] = useState(false);
  const [followUpAnswer, setFollowUpAnswer] = useState("");
  
  const textareaRef = useRef(null);
  const followUpRef = useRef(null);

  const handleAuthSuccess = (loggedInUser) => {
    setUser(loggedInUser);
    loadDreamsFromDB(loggedInUser.id);
  };

  const handleLogout = () => {
    setUser(null);
    setSavedDreams([]);
    resetStudio();
  };

  const loadDreamsFromDB = async (userId) => {
    try {
      // Mocking Prisma DB Call. Replace with: const data = await getDreams(userId);
      console.log(`Fetching dreams for user: ${userId} from Neon`);
    } catch(err) {
      console.error(err);
    }
  };

  const handleViewChange = (newView) => {
    if (view === newView) return;
    setIsTransitioningView(true);
    setTimeout(() => {
      setView(newView);
      if (newView === 'studio') resetStudio();
      setIsTransitioningView(false);
    }, 500); 
  };

  const handleInput = (e, ref) => {
    if(ref.current) {
        ref.current.style.height = 'auto';
        ref.current.style.height = `${ref.current.scrollHeight}px`;
    }
  };

  const startExtraction = () => {
    if (!inputText.trim()) return;
    setStatus("extracting");
    setTimeout(() => {
      setStatus("conversational");
    }, 2500);
  };

  const startSynthesis = () => {
    setStatus("processing");
    setActiveStepIndex(0);
    setCurrentResult(null);
  };

  const handleSaveToVault = async (text, resultData, lens) => {
    if (!user) return;
    try {
      // Mocking Prisma DB Call. Replace with: await saveDream(user.id, text, resultData, lens);
      const newDream = { id: Date.now().toString(), userId: user.id, inputText: text, storyData: resultData, lens, createdAt: Date.now() };
      setSavedDreams(prev => [newDream, ...prev]);
    } catch (err) {
      console.error("Error saving to Prisma:", err);
    }
  };

  const handleDeleteDream = async (id) => {
    if (!user) return;
    try {
      // Mocking Prisma DB Call. Replace with: await deleteDream(id);
      setSavedDreams(prev => prev.filter(d => d.id !== id));
    } catch (err) {
      console.error("Error deleting from Prisma:", err);
    }
  };

  const resetStudio = () => {
    setStatus("idle");
    setInputText("");
    setFollowUpAnswer("");
    setActiveStepIndex(-1);
    setCurrentResult(null);
    if(textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const loadFromVault = (dream) => {
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
    if (status === "processing" && activeStepIndex >= 0 && activeStepIndex < PROCESSING_STEPS.length) {
      const step = PROCESSING_STEPS[activeStepIndex];
      const timer = setTimeout(() => {
        setActiveStepIndex(prev => prev + 1);
      }, step.duration);
      return () => clearTimeout(timer);
    } else if (status === "processing" && activeStepIndex === PROCESSING_STEPS.length) {
      const completeTimer = setTimeout(() => {
        const result = { ...MOCK_STORY_DATA, title: `The Dream of ${new Date().toLocaleDateString()}`, lens: selectedLens };
        setCurrentResult(result);
        setStatus("success");
        handleSaveToVault(inputText, result, selectedLens);
      }, 1000);
      return () => clearTimeout(completeTimer);
    }
  }, [status, activeStepIndex, inputText, user, selectedLens]);

  if (!user) {
    return <AuthScreen onAuthSuccess={handleAuthSuccess} />;
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
          <div className="flex items-center space-x-3 cursor-pointer group" onClick={() => handleViewChange('studio')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500/20 to-fuchsia-500/20 border border-white/10 flex items-center justify-center shadow-lg transition-all duration-700 group-hover:rotate-12 group-hover:scale-110 group-hover:border-indigo-400/50">
              <Network className="w-5 h-5 text-indigo-300" />
            </div>
            <h1 className="text-xl font-serif font-bold text-white tracking-tight hidden sm:block transition-colors group-hover:text-indigo-200">Dream Archaeology</h1>
          </div>
          
          <div className="flex items-center space-x-1 bg-white/[0.02] p-1.5 rounded-2xl border border-white/5 backdrop-blur-md">
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

        <main className={`flex-1 p-4 sm:p-6 lg:p-8 xl:p-12 overflow-y-auto transition-all duration-700 ease-in-out ${isTransitioningView ? 'opacity-0 scale-[0.98]' : 'opacity-100 scale-100'}`}>
          
          {/* Library Vault View */}
          {view === 'library' && (
            <div className="max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out">
              <div className="mb-12 flex items-end justify-between">
                <div>
                  <h2 className="text-4xl font-serif font-bold text-white mb-3 tracking-tight">Memory Vault</h2>
                  <p className="text-slate-400 text-sm">Archived narratives securely stored in Neon Postgres.</p>
                </div>
              </div>

              {savedDreams.length === 0 ? (
                <div className="text-center py-32 border border-dashed border-white/10 rounded-[2rem] bg-white/[0.01] backdrop-blur-sm">
                  <Compass className="w-12 h-12 text-slate-600 mx-auto mb-6 opacity-50" />
                  <h3 className="text-xl font-medium text-slate-300 mb-2">The vault is empty</h3>
                  <p className="text-sm text-slate-500 mb-8">No dream graphs have been synthesized yet.</p>
                  <button onClick={() => handleViewChange('studio')} className="text-indigo-400 hover:text-indigo-300 text-sm font-semibold flex items-center justify-center mx-auto transition-colors group">
                    Return to Studio <ChevronRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
                  {savedDreams.map((dream, idx) => {
                    const savedLens = NARRATIVE_LENSES.find(l => l.id === dream.storyData.lens) || NARRATIVE_LENSES[0];
                    const SavedIcon = savedLens.icon;
                    return (
                      <div key={dream.id} 
                           className="group relative bg-[#0a0812] border border-white/5 rounded-3xl p-6 hover:border-indigo-500/40 hover:bg-white/[0.03] hover:shadow-[0_20px_40px_-15px_rgba(79,70,229,0.3)] transition-all duration-700 ease-out flex flex-col h-full animate-in fade-in slide-in-from-bottom-4 fill-mode-both hover:-translate-y-1.5"
                           style={{ animationDelay: `${idx * 100}ms` }}>
                        <div className="flex justify-between items-start mb-5">
                          <div className={`p-3 rounded-2xl transition-colors duration-500 ${savedLens.bg} ${savedLens.color} border ${savedLens.border}`}>
                            <SavedIcon className="w-5 h-5" />
                          </div>
                          <button onClick={(e) => { e.stopPropagation(); handleDeleteDream(dream.id); }} className="text-slate-600 hover:text-red-400 p-2 rounded-full hover:bg-red-400/10 transition-all opacity-0 group-hover:opacity-100">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                        <h3 className="text-xl font-serif font-semibold text-white mb-3 line-clamp-1 group-hover:text-indigo-100 transition-colors">{dream.storyData.title}</h3>
                        <p className="text-sm text-slate-400 line-clamp-3 mb-8 flex-1 italic leading-relaxed">"{dream.inputText}"</p>
                        <div className="flex items-center justify-between text-xs font-mono text-slate-500 border-t border-white/10 pt-5 mt-auto">
                           <span className="flex items-center"><Clock className="w-3 h-3 mr-1.5 opacity-70" /> {new Date(dream.createdAt).toLocaleDateString()}</span>
                           <button 
                             onClick={() => loadFromVault(dream)}
                             className="text-indigo-400 font-semibold hover:text-indigo-300 flex items-center bg-indigo-500/10 hover:bg-indigo-500/20 px-3 py-1.5 rounded-lg transition-colors group-hover:bg-indigo-500/20"
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
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 max-w-[1400px] mx-auto h-full">
              
              <div className="lg:col-span-5 flex flex-col space-y-8 relative z-10">
                
                <div className={`transition-all duration-1000 ease-in-out ${status !== 'idle' && status !== 'success' ? 'opacity-40 grayscale-[30%] pointer-events-none scale-[0.98]' : 'opacity-100 scale-100'}`}>
                  <div className="flex items-center justify-between mb-4">
                    <label htmlFor="dream-input" className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center">
                      <TerminalSquare className="w-4 h-4 mr-2 text-indigo-400" />
                      Raw Memory Input
                    </label>
                    {status === 'success' && (
                      <button onClick={resetStudio} className="text-[10px] uppercase tracking-widest font-bold text-fuchsia-400 hover:text-fuchsia-300 transition-colors bg-fuchsia-500/10 hover:bg-fuchsia-500/20 px-3 py-1.5 rounded-md">
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
                      readOnly={status !== 'idle'}
                      placeholder="Describe the memory... e.g. 'I was in a house, but the doors kept changing colors...'"
                      className="relative w-full bg-[#0a0812]/90 backdrop-blur-3xl border border-white/10 rounded-[2rem] p-6 md:p-8 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500/50 resize-none min-h-[180px] text-lg leading-relaxed shadow-2xl transition-all duration-700 focus:shadow-[0_0_40px_rgba(79,70,229,0.15)]"
                      rows={4}
                    />
                  </div>

                  {/* Lens Selection */}
                  <div className="mb-8">
                     <label className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center mb-4">
                      <Layers className="w-4 h-4 mr-2 text-indigo-400" />
                      Narrative Lens
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      {NARRATIVE_LENSES.map(lens => {
                        const Icon = lens.icon;
                        const isSelected = selectedLens === lens.id;
                        return (
                          <button
                            key={lens.id}
                            onClick={() => setSelectedLens(lens.id)}
                            disabled={status !== 'idle'}
                            className={`flex items-center p-4 rounded-2xl border transition-all duration-500 ease-out ${
                              isSelected 
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
                  <div className="animate-in fade-in slide-in-from-bottom-8 duration-1000 ease-out fill-mode-both delay-700">
                    <div className="mb-4 flex items-center justify-between pl-1">
                      <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest flex items-center bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20 shadow-[0_0_15px_rgba(52,211,153,0.2)]">
                        <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" /> Render Complete
                      </span>
                    </div>
                    <CinematicAudioPlayer title={currentResult?.title} />
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
                        {MOCK_DREAM_GRAPH.nodes.map((node, i) => (
                          <div key={node.id} className="relative group/node animate-in fade-in zoom-in-95 duration-500 fill-mode-both" style={{animationDelay: `${i * 150}ms`}}>
                             <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500/30 to-fuchsia-500/30 rounded-xl blur opacity-0 group-hover/node:opacity-100 transition-opacity duration-500" />
                             <div className="relative px-4 py-2 bg-[#0d0a14] border border-white/10 rounded-xl flex items-center space-x-3 shadow-lg">
                               <div className={`w-2 h-2 rounded-full ${
                                 node.type === 'Character' ? 'bg-indigo-400 shadow-[0_0_8px_rgba(129,140,248,0.8)]' :
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
                               <p className="text-slate-200 leading-relaxed"><Typewriter text={MOCK_DREAM_GRAPH.followUp} delay={15} /></p>
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
                            className="w-full bg-white/[0.02] border border-white/10 rounded-2xl p-4 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-fuchsia-500/40 resize-none min-h-[80px] text-sm transition-all focus:bg-white/[0.04]"
                            rows={2}
                          />
                         </div>
                         <div className="flex justify-end mt-4">
                            <button
                              onClick={startSynthesis}
                              className="px-6 py-2.5 bg-white text-black font-semibold rounded-xl hover:bg-slate-200 transition-colors flex items-center text-sm group"
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

                      {PROCESSING_STEPS.map((step, idx) => {
                        const isActive = idx === activeStepIndex;
                        const isPast = idx < activeStepIndex;
                        const isFuture = idx > activeStepIndex;

                        return (
                          <div key={step.id} className={`flex items-start relative transition-all duration-1000 ease-out ${isFuture ? 'opacity-20 translate-y-4' : 'opacity-100 translate-y-0'}`}>
                            
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 mr-6 relative z-10 transition-all duration-1000 ease-in-out ${
                              isPast ? 'bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 shadow-[0_0_10px_rgba(99,102,241,0.1)] scale-90' : 
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
                                    <p className="animate-in fade-in slide-in-from-left-4 duration-500 delay-300 fill-mode-both flex items-center relative z-10"><span className="text-fuchsia-500 mr-2 opacity-70">{'>'}</span> establishing layer constraints...</p>
                                    <p className="animate-in fade-in slide-in-from-left-4 duration-500 delay-[1200ms] fill-mode-both flex items-center relative z-10"><span className="text-fuchsia-500 mr-2 opacity-70">{'>'}</span> resolving contradictory nodes...</p>
                                    <p className="animate-in fade-in slide-in-from-left-4 duration-500 delay-[2000ms] fill-mode-both flex items-center relative z-10"><span className="text-indigo-400 mr-2 opacity-70">{'>'}</span> queuing sub-module pipeline...</p>
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
          )}
          
        </main>
      </div>

      <style dangerouslySetInnerHTML={{__html: `
        @keyframes shimmer { 100% { transform: translateX(100%); } }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }
      `}} />
    </div>
  );
}