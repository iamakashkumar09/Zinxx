'use client';

import React, { useState } from 'react';
import { Moon, User, Mail, KeyRound, Activity, LogIn, UserPlus, Database } from 'lucide-react';
import { loginUser, registerUser, createJwtSession } from '../actions';
const AuthScreen = ({ onAuthSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      let user;
      try {
        user = isLogin ? await loginUser(email, password) : await registerUser(email, password, name);
        if (!user) throw new Error("Database unconfigured or unavailable");
      } catch (dbErr) {
        console.warn("DB Auth failed/unconfigured, falling back to demo auth:", dbErr.message);
        if (dbErr.message === "Invalid credentials" || dbErr.message === "Email already exists") {
          throw dbErr;
        }
        await new Promise(resolve => setTimeout(resolve, 600));
        if (email === 'demo@dream.arc') {
          user = { id: 'usr_demo', email: 'demo@dream.arc', name: 'Explorer' };
        } else {
          user = { id: 'usr_' + Math.random().toString(36).substring(2, 9), email, name: name || email.split('@')[0] || 'Explorer' };
        }
        const token = await createJwtSession(user);
        user = { ...user, token };
      }
      
      onAuthSuccess(user);
    } catch (err) {
      setError(err.message || "Authentication failed");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center relative overflow-hidden bg-[#030208] text-slate-200">
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[80vw] h-[80vw] max-w-[800px] max-h-[800px] bg-indigo-900/10 rounded-full blur-[120px] mix-blend-screen animate-[pulse_10s_ease-in-out_infinite]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60vw] h-[60vw] max-w-[600px] max-h-[600px] bg-fuchsia-900/10 rounded-full blur-[100px] mix-blend-screen animate-[pulse_12s_ease-in-out_infinite_1s]" />
      </div>
      
      <div className="relative z-10 w-full max-w-md p-8 animate-in fade-in zoom-in-95 duration-1000 ease-out flex flex-col items-center">
        
        <div className="w-20 h-20 mb-8 rounded-full border border-white/10 bg-white/[0.02] backdrop-blur-xl flex items-center justify-center relative shadow-[0_0_50px_rgba(79,70,229,0.15)] group">
          <div className="absolute inset-0 rounded-full border border-indigo-500/30 animate-[spin_6s_linear_infinite]" />
          <div className="absolute inset-2 rounded-full border border-fuchsia-500/20 animate-[spin_8s_linear_infinite_reverse]" />
          <Moon className="w-8 h-8 text-indigo-300 group-hover:scale-110 transition-transform duration-700 ease-out" />
        </div>
        
        <h1 className="text-4xl font-serif font-bold text-transparent bg-clip-text bg-gradient-to-b from-white via-indigo-100 to-slate-500 tracking-tight mb-2 text-center">
          Dream Archaeology
        </h1>
        <p className="text-slate-400 text-sm mb-10 text-center font-light">
          Authenticate via Neon Postgres to access the cortex.
        </p>

        <form onSubmit={handleSubmit} className="w-full bg-white/[0.02] border border-white/5 p-8 rounded-3xl backdrop-blur-md shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-fuchsia-500 to-emerald-500 opacity-50" />
          
          <div className="space-y-5">
            {!isLogin && (
              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 flex items-center">
                  <User className="w-3 h-3 mr-1.5" /> Subject Name
                </label>
                <input 
                  type="text" 
                  required 
                  value={name}
                  onChange={e => setName(e.target.value)}
                  className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all text-sm"
                  placeholder="e.g. Cobb"
                />
              </div>
            )}
            
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 flex items-center">
                <Mail className="w-3 h-3 mr-1.5" /> Cortex ID (Email)
              </label>
              <input 
                type="email" 
                required 
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all text-sm"
                placeholder="demo@dream.arc"
              />
            </div>

            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 flex items-center">
                <KeyRound className="w-3 h-3 mr-1.5" /> Passphrase
              </label>
              <input 
                type="password" 
                required 
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all text-sm"
                placeholder="••••••••"
              />
            </div>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs text-rose-300 flex items-center">
              <Activity className="w-4 h-4 mr-2" /> {error}
            </div>
          )}

          <div className="mt-8">
            <button
              type="submit"
              disabled={loading}
              className="relative w-full inline-flex items-center justify-center px-8 py-3.5 font-bold text-white transition-all duration-500 ease-out bg-indigo-600 hover:bg-indigo-500 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed group overflow-hidden shadow-[0_0_20px_rgba(79,70,229,0.2)] hover:shadow-[0_0_30px_rgba(79,70,229,0.4)] hover:-translate-y-0.5 active:translate-y-0"
            >
              <span className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:animate-[shimmer_2s_infinite]" />
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : isLogin ? (
                <>Enter Cortex <LogIn className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" /></>
              ) : (
                <>Initialize Profile <UserPlus className="w-4 h-4 ml-2 group-hover:scale-110 transition-transform" /></>
              )}
            </button>
          </div>

          <div className="mt-6 text-center">
            <button 
              type="button" 
              onClick={() => { setIsLogin(!isLogin); setError(''); }}
              className="text-xs text-slate-500 hover:text-indigo-400 transition-colors font-medium tracking-wide"
            >
              {isLogin ? "No profile detected? Initialize here." : "Existing profile? Enter cortex here."}
            </button>
          </div>
        </form>

        {isLogin && (
          <div className="mt-8 text-xs text-slate-600 font-mono flex items-center bg-white/[0.02] px-4 py-2 rounded-full border border-white/5">
             <Database className="w-3.5 h-3.5 mr-2" />
             Demo Login: demo@dream.arc
          </div>
        )}
      </div>
    </div>
  );
};

export { AuthScreen };