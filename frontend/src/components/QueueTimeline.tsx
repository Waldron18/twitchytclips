import React, { useState } from 'react';
import { Job } from '../types';
import { Loader2, Clock, Zap, X, Trash2 } from 'lucide-react';
import { api } from '../services/api';

interface QueueTimelineProps {
  jobs: Job[];
  onRefresh?: () => void;
}

export const QueueTimeline: React.FC<QueueTimelineProps> = ({ jobs, onRefresh }) => {
  const [clearing, setClearing] = useState(false);
  const activeJobs = jobs.filter((j) => j.status === 'running' || j.status === 'queued');

  if (activeJobs.length === 0) return null;

  const handleClearAll = async () => {
    try {
      setClearing(true);
      await api.clearJobs();
      if (onRefresh) onRefresh();
    } catch (e) {
      console.error('Failed to clear queue', e);
    } finally {
      setClearing(false);
    }
  };

  const handleCancelOne = async (jobId: string) => {
    try {
      await api.cancelJob(jobId);
      if (onRefresh) onRefresh();
    } catch (e) {
      console.error('Failed to cancel job', e);
    }
  };

  return (
    <div className="bg-zinc-900/90 border border-brand-500/30 rounded-2xl p-4 shadow-xl backdrop-blur-md mb-6 animate-fadeIn">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Zap className="w-4 h-4 text-brand-400 animate-pulse" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-200">
            Active Sequential Pipeline ({activeJobs.length} {activeJobs.length === 1 ? 'task' : 'tasks'})
          </h4>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleClearAll}
            disabled={clearing}
            className="flex items-center space-x-1 text-[11px] text-red-400 hover:text-red-300 bg-red-950/40 hover:bg-red-900/50 border border-red-800/40 px-2.5 py-0.5 rounded-lg transition"
            title="Cancel all stuck and queued jobs"
          >
            <Trash2 className="w-3 h-3" />
            <span>Reset Queue</span>
          </button>
          <span className="text-[11px] text-zinc-400 bg-zinc-800/80 px-2 py-0.5 rounded font-mono hidden sm:inline-block">
            VRAM Protection: 1 Task At A Time
          </span>
        </div>
      </div>

      <div className="space-y-3">
        {activeJobs.map((job) => {
          const isRunning = job.status === 'running';
          return (
            <div key={job.id} className="bg-zinc-950 p-3.5 rounded-xl border border-zinc-800/80 relative group">
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center space-x-2">
                  {isRunning ? (
                    <Loader2 className="w-4 h-4 text-brand-400 animate-spin" />
                  ) : (
                    <Clock className="w-4 h-4 text-zinc-500" />
                  )}
                  <span className="text-xs font-semibold text-zinc-200 capitalize">
                    {job.job_type === 'pipeline' ? 'Full Video Processing' : 'Rendering 9:16 Short'}
                  </span>
                </div>
                <div className="flex items-center space-x-3">
                  <span className="text-xs font-mono font-bold text-brand-400">
                    {job.progress}%
                  </span>
                  <button
                    onClick={() => handleCancelOne(job.id)}
                    className="text-zinc-500 hover:text-red-400 p-0.5 rounded hover:bg-zinc-800 transition"
                    title="Cancel this task"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-zinc-800 h-2 rounded-full overflow-hidden mb-2">
                <div
                  className="bg-gradient-to-r from-brand-500 to-indigo-500 h-full rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${Math.max(job.progress, 5)}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-[11px] text-zinc-400">
                <span className="truncate max-w-[80%] text-zinc-300">
                  {job.current_step || 'Processing...'}
                </span>
                <span className="capitalize px-1.5 py-0.2 rounded bg-zinc-800 text-[10px] text-zinc-400">
                  {job.status}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
