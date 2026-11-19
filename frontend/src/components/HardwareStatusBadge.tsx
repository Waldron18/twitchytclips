import React, { useState } from 'react';
import { HardwareProfile } from '../types';
import { Cpu, CheckCircle2, XCircle, Zap, HardDrive, ShieldCheck, X } from 'lucide-react';
import { api } from '../services/api';

interface HardwareModalProps {
  hardware: HardwareProfile;
  isOpen: boolean;
  onClose: () => void;
  onUpdateHardware: (updated: HardwareProfile) => void;
}

export const HardwareStatusBadge: React.FC<HardwareModalProps> = ({
  hardware,
  isOpen,
  onClose,
  onUpdateHardware,
}) => {
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleOverride = async (tier: string) => {
    try {
      setLoading(true);
      const updated = await api.overrideTier(tier);
      onUpdateHardware(updated);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-zinc-400 hover:text-white transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-4">
          <div className="p-2.5 rounded-xl bg-brand-500/10 text-brand-400 border border-brand-500/20">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Hardware Profiler</h3>
            <p className="text-xs text-zinc-400">Automatic capability detection & dynamic tier scaling</p>
          </div>
        </div>

        {/* Current Specs Grid */}
        <div className="grid grid-cols-2 gap-3 mb-5">
          <div className="bg-zinc-950/60 p-3 rounded-xl border border-zinc-800/80">
            <span className="text-[11px] text-zinc-400 block font-medium">GPU Detected</span>
            <span className="text-sm font-semibold text-zinc-200 truncate block mt-0.5">
              {hardware.gpu_name}
            </span>
          </div>

          <div className="bg-zinc-950/60 p-3 rounded-xl border border-zinc-800/80">
            <span className="text-[11px] text-zinc-400 block font-medium">VRAM / System RAM</span>
            <span className="text-sm font-semibold text-zinc-200 mt-0.5 block">
              {hardware.vram_gb} GB VRAM / {hardware.ram_gb} GB RAM
            </span>
          </div>

          <div className="bg-zinc-950/60 p-3 rounded-xl border border-zinc-800/80">
            <span className="text-[11px] text-zinc-400 block font-medium">NVENC Hardware Encoder</span>
            <div className="flex items-center space-x-1.5 mt-0.5">
              {hardware.has_nvenc ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-semibold text-emerald-400">Active (Pascal/Ampere)</span>
                </>
              ) : (
                <>
                  <XCircle className="w-4 h-4 text-amber-400" />
                  <span className="text-xs font-semibold text-amber-400">Unavailable (libx264 veryfast)</span>
                </>
              )}
            </div>
          </div>

          <div className="bg-zinc-950/60 p-3 rounded-xl border border-zinc-800/80">
            <span className="text-[11px] text-zinc-400 block font-medium">Free Storage Space</span>
            <div className="flex items-center space-x-1.5 mt-0.5">
              <HardDrive className="w-4 h-4 text-zinc-400" />
              <span className="text-xs font-semibold text-zinc-200">{hardware.free_disk_gb} GB free</span>
            </div>
          </div>
        </div>

        {/* Dynamic Pipeline Assigned */}
        <div className="bg-zinc-950/90 rounded-xl p-4 border border-zinc-800 mb-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-zinc-300">Active Pipeline Assignment</span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-brand-500/20 text-brand-300 border border-brand-500/30 uppercase">
              Tier: {hardware.tier}
            </span>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between text-zinc-400">
              <span>Whisper Speech Model:</span>
              <span className="font-mono text-zinc-200 font-semibold">{hardware.whisper_model} ({hardware.whisper_compute_type})</span>
            </div>
            <div className="flex justify-between text-zinc-400">
              <span>Local LLM Brain:</span>
              <span className="font-mono text-zinc-200 font-semibold">{hardware.ollama_model}</span>
            </div>
            <div className="flex justify-between text-zinc-400">
              <span>Video Encoder:</span>
              <span className="font-mono text-zinc-200 font-semibold">{hardware.ffmpeg_video_encoder}</span>
            </div>
            <div className="flex justify-between text-zinc-400">
              <span>Storage Saver Mode:</span>
              <span className={`font-semibold ${hardware.storage_saver_mode ? 'text-emerald-400' : 'text-zinc-300'}`}>
                {hardware.storage_saver_mode ? 'Enabled (Audio-First)' : 'Standard (Full-Res)'}
              </span>
            </div>
          </div>
        </div>

        {/* Tier Override Buttons */}
        <div>
          <span className="text-xs text-zinc-400 block mb-2 font-medium">Manual Tier Override</span>
          <div className="grid grid-cols-3 gap-2">
            {(['LOW', 'MID', 'HIGH'] as const).map((t) => (
              <button
                key={t}
                disabled={loading}
                onClick={() => handleOverride(t)}
                className={`py-2 px-3 rounded-lg text-xs font-bold border transition ${
                  hardware.tier === t
                    ? 'bg-brand-600 border-brand-500 text-white shadow-md shadow-brand-500/25'
                    : 'bg-zinc-800/60 border-zinc-700/60 text-zinc-300 hover:bg-zinc-800'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Recommendations */}
        {hardware.recommendations.length > 0 && (
          <div className="mt-4 pt-3 border-t border-zinc-800 text-[11px] text-zinc-400 space-y-1">
            {hardware.recommendations.map((rec, i) => (
              <p key={i} className="flex items-start space-x-1.5">
                <span className="text-brand-400">•</span>
                <span>{rec}</span>
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
