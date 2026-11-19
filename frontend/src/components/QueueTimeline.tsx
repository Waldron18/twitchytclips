import React from 'react';
import { Job } from '../types';
import { Loader2, CheckCircle2, AlertCircle, Clock, Zap } from 'lucide-react';

interface QueueTimelineProps {
  jobs: Job[];
}

export const QueueTimeline: React.FC<QueueTimelineProps> = ({ jobs }) => {
  const activeJobs = jobs.filter((j) => j.status === 'running' || j.status === 'queued');

  if (activeJobs.length === 0) return null;

  return (
    <div className="bg-zinc-900/90 border border-brand-500/30 rounded-2xl p-4 shadow-xl backdrop-blur-md mb-6 animate-fadeIn">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Zap className="w-4 h-4 text-brand-400 animate-pulse" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-200">
            Active Sequential Pipeline ({activeJobs.length} {activeJobs.length === 1 ? 'task' : 'tasks'})
          </h4>
        </div>
        <span className="text-[11px] text-zinc-400 bg-zinc-800/80 px-2 py-0.5 rounded font-mono">
          VRAM Protection: 1 Task At A Time
        </span>
      </div>

      <div className="space-y-3">
        {activeJobs.map((job) => {
          const isRunning = job.status === 'running';
          return (
            <div key={job.id} className="bg-zinc-950 p-3.5 rounded-xl border border-zinc-800/80">
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
                <span className="text-xs font-mono font-bold text-brand-400">
                  {job.progress}%
                </span>
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
