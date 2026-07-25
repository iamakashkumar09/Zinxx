const CinematicAudioPlayer = ({ title = "Final Master.wav" }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const progressBarRef = useRef(null);

  useEffect(() => {
    let interval;
    if (isPlaying) {
      interval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 100) {
            setIsPlaying(false);
            return 0;
          }
          return prev + 0.5;
        });
      }, 300);
    }
    return () => clearInterval(interval);
  }, [isPlaying]);

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
            <div className="p-3 bg-indigo-500/10 rounded-xl border border-indigo-500/20 backdrop-blur-md transition-transform duration-500 group-hover:scale-105 group-hover:bg-indigo-500/20">
              <Waves className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h4 className="text-slate-200 font-semibold tracking-wide truncate max-w-[200px] sm:max-w-xs transition-colors duration-300 group-hover:text-white">{title}</h4>
              <p className="text-slate-500 text-xs font-mono mt-1 flex items-center">
                <Activity className="w-3 h-3 mr-1" /> 44.1kHz • Stereo Mix
              </p>
            </div>
          </div>
          <button className="p-2 text-slate-400 hover:text-indigo-300 hover:bg-white/10 rounded-lg transition-all duration-300 hover:scale-110 active:scale-95">
            <Download className="w-5 h-5" />
          </button>
        </div>

        <div className="flex items-center space-x-4">
          <button 
            onClick={() => setIsPlaying(!isPlaying)}
            className="w-12 h-12 shrink-0 flex items-center justify-center rounded-full bg-slate-100 hover:bg-white text-[#090812] shadow-[0_0_20px_rgba(255,255,255,0.1)] hover:shadow-[0_0_30px_rgba(255,255,255,0.3)] transition-all duration-300 transform hover:scale-105 active:scale-95"
          >
            {isPlaying ? <Pause className="w-5 h-5 fill-current transition-all duration-300" /> : <Play className="w-5 h-5 fill-current ml-1 transition-all duration-300" />}
          </button>
          
          <div className="flex-1 min-w-0">
            <FauxWaveform isPlaying={isPlaying} />
            <div 
              ref={progressBarRef}
              onClick={handleProgressClick}
              className="h-1.5 w-full bg-white/5 rounded-full cursor-pointer relative overflow-hidden mt-3 group/bar"
            >
              <div 
                className="absolute top-0 left-0 h-full bg-gradient-to-r from-indigo-400 to-fuchsia-400 transition-all duration-300 ease-out group-hover/bar:brightness-110"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-slate-500 mt-2 font-mono">
              <span>00:{(Math.floor(progress / 2)).toString().padStart(2, '0')}</span>
              <span>00:50</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
