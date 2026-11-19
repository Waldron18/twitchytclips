import React from 'react';
import { HardwareProfile, OllamaStatus, CleanupStats } from '../types';
import { Cpu, HardDrive, Sparkles, Terminal, ShieldCheck, RefreshCw, AlertTriangle } from 'lucide-react';

interface NavbarProps {
  hardware: HardwareProfile | null;
  ollama: OllamaStatus | null;
  cleanupStats: CleanupStats | null;
  onOpenHardwareModal: () => void;
  onOpenCleanupModal: () => void;
  onOpenNewProject: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  hardware,
  ollama,
  cleanupStats,
  onOpenHardwareModal,
  onOpenCleanupModal,
  onOpenNewProject,
}) => {
  const getTierColor = (tier?: string) => {
    switch (tier) {
      case 'HIGH':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'MID':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      default:
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    }
  };

  return (
    <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-40 px-4 lg:px-8 py-3.5 flex items-center justify-between">
      {/* Brand Logo */}
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-brand-500/20">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
              ClipForge
            </span>
            <span className="text-[10px] font-bold uppercase tracking-wider bg-zinc-800 text-zinc-300 px-1.5 py-0.5 rounded border border-zinc-700">
              LOCAL
            </span>
          </div>
          <p className="text-xs text-zinc-400 font-medium hidden sm:block">100% Free Open-Source AI Video Clipper</p>
        </div>
      </div>

      {/* Center Actions / Badges */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        {/* Hardware Tier Badge */}
        {hardware && (
          <button
            onClick={onOpenHardwareModal}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border text-xs font-semibold transition hover:brightness-110 ${getTierColor(
              hardware.tier
            )}`}
            title="Click to view hardware profiler & change tier"
          >
            <Cpu className="w-3.5 h-3.5" />
            <span className="hidden md:inline">{hardware.gpu_name}</span>
            <span className="uppercase px-1.5 py-0.5 rounded bg-black/40 text-[10px] font-bold">
              {hardware.tier}
            </span>
            <span className="text-[11px] opacity-80 hidden lg:inline">
              ({hardware.has_nvenc ? 'NVENC' : 'x264'})
            </span>
          </button>
        )}

        {/* Ollama Status Badge */}
        {ollama && (
          <div
            className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium ${
              ollama.online
                ? 'bg-emerald-950/40 border-emerald-800/40 text-emerald-300'
                : 'bg-amber-950/40 border-amber-800/40 text-amber-300'
            }`}
            title={ollama.online ? `Ollama Active (${ollama.recommended_model})` : 'Ollama Offline: Heuristic NLP Active'}
          >
            <span
              className={`w-2 h-2 rounded-full ${ollama.online ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}
            />
            <span className="hidden sm:inline">Ollama:</span>
            <span className="font-semibold">{ollama.online ? 'Online' : 'Offline (NLP)'}</span>
          </div>
        )}

        {/* Disk Space & Cleanup */}
        {cleanupStats && (
          <button
            onClick={onOpenCleanupModal}
            className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium transition ${
              cleanupStats.free_disk_gb < 12
                ? 'bg-red-500/10 text-red-400 border-red-500/30 hover:bg-red-500/20'
                : 'bg-zinc-900 border-zinc-800 text-zinc-300 hover:bg-zinc-800'
            }`}
            title="Manage disk usage and clean temporary files"
          >
            <HardDrive className="w-3.5 h-3.5" />
            <span>{cleanupStats.free_disk_gb} GB</span>
            {cleanupStats.temp_usage_mb > 0 && (
              <span className="text-[10px] text-zinc-400 hidden xl:inline">
                ({cleanupStats.temp_usage_mb}MB temp)
              </span>
            )}
          </button>
        )}

        {/* New Clip Project Button */}
        <button
          onClick={onOpenNewProject}
          className="flex items-center space-x-2 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-semibold text-xs sm:text-sm px-3.5 py-2 rounded-lg shadow-md shadow-brand-500/20 transition active:scale-95"
        >
          <Sparkles className="w-4 h-4" />
          <span>New Clip</span>
        </button>
      </div>
    </header>
  );
};
