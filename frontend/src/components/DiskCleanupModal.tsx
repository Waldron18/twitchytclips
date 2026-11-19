import React, { useState } from 'react';
import { CleanupStats } from '../types';
import { HardDrive, Trash2, ShieldCheck, AlertCircle, X, Loader2 } from 'lucide-react';
import { api } from '../services/api';

interface DiskCleanupModalProps {
  isOpen: boolean;
  onClose: () => void;
  stats: CleanupStats | null;
  onCleanupComplete: (newStats: CleanupStats) => void;
}

export const DiskCleanupModal: React.FC<DiskCleanupModalProps> = ({
  isOpen,
  onClose,
  stats,
  onCleanupComplete,
}) => {
  const [cleaning, setCleaning] = useState(false);
  const [cleanedResult, setCleanedResult] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleCleanup = async () => {
    try {
      setCleaning(true);
      const res = await api.executeCleanup();
      setCleanedResult(`Freed ${res.freed_mb} MB of disk space.`);
      const updated = await api.getCleanupStats();
      onCleanupComplete(updated);
    } catch (err) {
      console.error(err);
    } finally {
      setCleaning(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-zinc-400 hover:text-white transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-4">
          <div className="p-2.5 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20">
            <HardDrive className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Disk Storage & Cleanup</h3>
            <p className="text-xs text-zinc-400">Manage low disk space on laptops & workstations</p>
          </div>
        </div>

        {stats && (
          <div className="space-y-3 mb-5">
            <div className="bg-zinc-950 p-3.5 rounded-xl border border-zinc-800">
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs text-zinc-400">Available Drive Space:</span>
                <span className="text-sm font-bold text-zinc-100 font-mono">
                  {stats.free_disk_gb} GB Free
                </span>
              </div>
              <div className="flex justify-between items-center mb-1 text-xs">
                <span className="text-zinc-400">Temporary Raw Segments Cache:</span>
                <span className="font-semibold text-amber-400 font-mono">
                  {stats.temp_usage_mb} MB
                </span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-zinc-400">Finished Exported Clips:</span>
                <span className="font-semibold text-emerald-400 font-mono">
                  {stats.exports_usage_mb} MB
                </span>
              </div>
            </div>

            <div className="p-3 bg-zinc-950/80 rounded-xl border border-zinc-800/80 text-xs text-zinc-400 flex items-start space-x-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span>
                <strong>Safe Cleanup:</strong> Only deletes temporary unrendered video/audio segments and cached frames. Your final exported 9:16 clips will remain 100% safe.
              </span>
            </div>
          </div>
        )}

        {cleanedResult && (
          <div className="mb-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs text-emerald-400 font-medium">
            {cleanedResult}
          </div>
        )}

        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-zinc-400 hover:text-white transition"
          >
            Close
          </button>
          <button
            type="button"
            disabled={cleaning || (stats?.temp_usage_mb === 0)}
            onClick={handleCleanup}
            className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold shadow-lg shadow-red-500/20 transition disabled:opacity-50"
          >
            {cleaning ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Cleaning...</span>
              </>
            ) : (
              <>
                <Trash2 className="w-4 h-4" />
                <span>Purge Temp Cache</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
