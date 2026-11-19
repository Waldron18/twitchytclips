import React, { useState, useEffect } from 'react';
import { HardwareProfile, Project, Clip, Job, MusicTrack, CleanupStats, OllamaStatus } from './types';
import { api } from './services/api';
import { Navbar } from './components/Navbar';
import { HardwareStatusBadge } from './components/HardwareStatusBadge';
import { IngestModal } from './components/IngestModal';
import { QueueTimeline } from './components/QueueTimeline';
import { ClipReviewEditor } from './components/ClipReviewEditor';
import { DiskCleanupModal } from './components/DiskCleanupModal';
import {
  Sparkles, Video, Play, Clock, Flame, ChevronRight, FolderOpen,
  PlusCircle, RefreshCw, Layers, ShieldAlert
} from 'lucide-react';

export const App: React.FC = () => {
  const [hardware, setHardware] = useState<HardwareProfile | null>(null);
  const [ollama, setOllama] = useState<OllamaStatus | null>(null);
  const [cleanupStats, setCleanupStats] = useState<CleanupStats | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [selectedClip, setSelectedClip] = useState<Clip | null>(null);
  const [musicTracks, setMusicTracks] = useState<MusicTrack[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);

  // Modals state
  const [isHardwareModalOpen, setIsHardwareModalOpen] = useState(false);
  const [isCleanupModalOpen, setIsCleanupModalOpen] = useState(false);
  const [isIngestModalOpen, setIsIngestModalOpen] = useState(false);

  // Initial data load
  const loadInitialData = async () => {
    try {
      const [hw, ol, cs, prjs, mus, jbs] = await Promise.all([
        api.getHardware().catch(() => null),
        api.getOllamaStatus().catch(() => null),
        api.getCleanupStats().catch(() => null),
        api.getProjects().catch(() => []),
        api.getMusicTracks().catch(() => []),
        api.getJobs().catch(() => [])
      ]);

      if (hw) setHardware(hw);
      if (ol) setOllama(ol);
      if (cs) setCleanupStats(cs);
      if (mus) setMusicTracks(mus);
      if (jbs) setJobs(jbs);

      if (prjs && prjs.length > 0) {
        setProjects(prjs);
        // Load latest project
        const latest = await api.getProject(prjs[0].id);
        setCurrentProject(latest);
        if (latest.clips && latest.clips.length > 0) {
          setSelectedClip(latest.clips[0]);
        }
      }
    } catch (e) {
      console.error('Failed to load initial state:', e);
    }
  };

  useEffect(() => {
    loadInitialData();

    // Setup SSE live stream
    const eventSource = new EventSource('/api/jobs/stream');
    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const { event: evtType, data } = payload;

        // Refresh jobs and projects on updates
        api.getJobs().then(setJobs).catch(() => {});

        if (evtType === 'project_updated') {
          api.getProjects().then(setProjects).catch(() => {});
          if (currentProject && currentProject.id === data.project_id) {
            setCurrentProject((prev) =>
              prev
                ? {
                    ...prev,
                    title: data.title,
                    duration: data.duration ?? prev.duration,
                    platform: data.platform ?? prev.platform,
                  }
                : null
            );
          }
        }

        if (evtType === 'job_completed') {
          api.getProjects().then(setProjects).catch(() => {});
          if (currentProject) {
            api.getProject(currentProject.id).then((p) => {
              setCurrentProject(p);
              if (p.clips && p.clips.length > 0) {
                // Keep selected or update
                setSelectedClip((prev) => {
                  if (!prev) return p.clips![0];
                  const match = p.clips!.find((c) => c.id === prev.id);
                  return match || p.clips![0];
                });
              }
            }).catch(() => {});
          }
          api.getCleanupStats().then(setCleanupStats).catch(() => {});
        }
      } catch (err) {
        console.error('SSE parse error:', err);
      }
    };

    // Polling interval fallback for active jobs & project title/status refresh
    const interval = setInterval(() => {
      api.getJobs().then(setJobs).catch(() => {});
      if (currentProject && (currentProject.status !== 'ready' && currentProject.status !== 'failed')) {
        api.getProject(currentProject.id).then((p) => {
          setCurrentProject(p);
          if (p.clips && p.clips.length > 0 && !selectedClip) {
            setSelectedClip(p.clips[0]);
          }
        }).catch(() => {});
        api.getProjects().then(setProjects).catch(() => {});
      }
    }, 2500);

    return () => {
      eventSource.close();
      clearInterval(interval);
    };
  }, [currentProject?.id]);

  const selectProject = async (projId: string) => {
    try {
      const p = await api.getProject(projId);
      setCurrentProject(p);
      if (p.clips && p.clips.length > 0) {
        setSelectedClip(p.clips[0]);
      } else {
        setSelectedClip(null);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleProjectCreated = async (projectId: string) => {
    await selectProject(projectId);
    const prjs = await api.getProjects();
    setProjects(prjs);
  };

  const handleUpdateClip = (updated: Clip) => {
    setSelectedClip(updated);
    if (currentProject && currentProject.clips) {
      const updatedClips = currentProject.clips.map((c) => (c.id === updated.id ? updated : c));
      setCurrentProject({ ...currentProject, clips: updatedClips });
    }
  };

  const handleTriggerRender = async (clipId: string) => {
    try {
      await api.renderClip(clipId);
      const jbs = await api.getJobs();
      setJobs(jbs);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-zinc-950 text-slate-100">
      {/* Top Navigation */}
      <Navbar
        hardware={hardware}
        ollama={ollama}
        cleanupStats={cleanupStats}
        onOpenHardwareModal={() => setIsHardwareModalOpen(true)}
        onOpenCleanupModal={() => setIsCleanupModalOpen(true)}
        onOpenNewProject={() => setIsIngestModalOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {/* Real-time Job Execution Queue */}
        <QueueTimeline jobs={jobs} onRefresh={() => api.getJobs().then(setJobs)} />

        {/* Hero Section if No Projects exist yet */}
        {projects.length === 0 && (
          <div className="my-12 text-center max-w-2xl mx-auto p-8 rounded-3xl bg-zinc-900/60 border border-zinc-800 shadow-2xl backdrop-blur-md">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-brand-600 via-indigo-600 to-purple-600 mx-auto flex items-center justify-center shadow-lg shadow-brand-500/25 mb-4">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-black tracking-tight text-white mb-2">
              Welcome to ClipForge Local
            </h2>
            <p className="text-sm text-zinc-400 mb-6 leading-relaxed">
              Your 100% free, local AI studio for turning long streams and gaming VODs into viral 9:16 vertical shorts for YouTube Shorts and Instagram Reels with facecam split-screen, karaoke captions, and -14 LUFS audio mastering.
            </p>
            <button
              onClick={() => setIsIngestModalOpen(true)}
              className="inline-flex items-center space-x-2 px-6 py-3 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-bold text-sm shadow-xl shadow-brand-500/30 transition active:scale-95"
            >
              <PlusCircle className="w-5 h-5" />
              <span>Import Your First Video / Stream</span>
            </button>
          </div>
        )}

        {/* Active Project View */}
        {currentProject && (
          <div className="space-y-6">
            {/* Project Header Bar & Switcher */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-2xl bg-zinc-900/80 border border-zinc-800">
              <div className="flex items-center space-x-3 truncate">
                <div className="p-2.5 rounded-xl bg-zinc-800 text-brand-400">
                  <Video className="w-5 h-5" />
                </div>
                <div className="truncate">
                  <h2 className="text-base font-bold text-white truncate">{currentProject.title}</h2>
                  <div className="flex items-center space-x-2 text-xs text-zinc-400 mt-0.5">
                    <span className="capitalize font-medium text-zinc-300">{currentProject.platform}</span>
                    <span>•</span>
                    <span>{Math.round(currentProject.duration)}s duration</span>
                    <span>•</span>
                    <span className="uppercase text-[10px] font-bold px-1.5 py-0.5 rounded bg-zinc-800 text-brand-400">
                      {currentProject.status}
                    </span>
                  </div>
                </div>
              </div>

              {/* Project Dropdown / Switcher */}
              <div className="flex items-center space-x-2">
                <select
                  value={currentProject.id}
                  onChange={(e) => selectProject(e.target.value)}
                  className="bg-zinc-950 border border-zinc-700 rounded-xl px-3 py-2 text-xs font-semibold text-zinc-200 focus:outline-none focus:border-brand-500 cursor-pointer"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.title.length > 35 ? p.title.slice(0, 35) + '...' : p.title} ({p.clip_count} clips)
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => setIsIngestModalOpen(true)}
                  className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-white text-xs font-semibold border border-zinc-700 transition"
                >
                  <PlusCircle className="w-4 h-4 text-brand-400" />
                  <span className="hidden sm:inline">New Video</span>
                </button>
              </div>
            </div>

            {/* Candidate Clips Shelf */}
            {currentProject.clips && currentProject.clips.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <Flame className="w-4 h-4 text-amber-400" />
                    <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-300">
                      Detected Viral Moments ({currentProject.clips.length} Candidates)
                    </h3>
                  </div>
                  <span className="text-xs text-zinc-400">
                    Snapped to word boundaries (18-55s)
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                  {currentProject.clips.map((clip) => {
                    const isSelected = selectedClip?.id === clip.id;
                    return (
                      <button
                        key={clip.id}
                        type="button"
                        onClick={() => setSelectedClip(clip)}
                        className={`text-left p-3 rounded-2xl border transition-all duration-200 relative flex flex-col justify-between ${
                          isSelected
                            ? 'bg-zinc-900 border-brand-500 shadow-lg shadow-brand-500/15 ring-1 ring-brand-500'
                            : 'bg-zinc-900/60 border-zinc-800 hover:border-zinc-700 hover:bg-zinc-900'
                        }`}
                      >
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-black/50 text-white">
                              #{clip.viral_rank}
                            </span>
                            <span className="text-[10px] font-mono font-bold text-amber-400 flex items-center space-x-0.5">
                              <span>{clip.hype_score}</span>
                              <span className="text-[9px] text-zinc-500">hype</span>
                            </span>
                          </div>

                          <h4 className="text-xs font-bold text-zinc-200 line-clamp-2 mb-1.5">
                            {clip.title}
                          </h4>

                          <p className="text-[11px] text-zinc-400 italic line-clamp-2">
                            "{clip.hook_summary || 'Exciting moment'}"
                          </p>
                        </div>

                        <div className="mt-3 pt-2 border-t border-zinc-800/80 flex items-center justify-between text-[10px] text-zinc-400">
                          <span className="flex items-center space-x-1">
                            <Clock className="w-3 h-3" />
                            <span>{Math.round(clip.duration)}s</span>
                          </span>
                          <span
                            className={`font-semibold ${
                              clip.has_rendered ? 'text-emerald-400' : 'text-zinc-500'
                            }`}
                          >
                            {clip.has_rendered ? 'Rendered' : 'Draft'}
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Selected Clip Studio / Editor */}
            {selectedClip && (
              <div className="mt-6 pt-6 border-t border-zinc-800">
                <ClipReviewEditor
                  clip={selectedClip}
                  musicTracks={musicTracks}
                  onUpdateClip={handleUpdateClip}
                  onTriggerRender={handleTriggerRender}
                />
              </div>
            )}
          </div>
        )}
      </main>

      {/* Modals */}
      {hardware && (
        <HardwareStatusBadge
          hardware={hardware}
          isOpen={isHardwareModalOpen}
          onClose={() => setIsHardwareModalOpen(false)}
          onUpdateHardware={(updated) => setHardware(updated)}
        />
      )}

      <IngestModal
        isOpen={isIngestModalOpen}
        onClose={() => setIsIngestModalOpen(false)}
        defaultStorageSaver={hardware?.storage_saver_mode ?? true}
        onProjectCreated={handleProjectCreated}
      />

      <DiskCleanupModal
        isOpen={isCleanupModalOpen}
        onClose={() => setIsCleanupModalOpen(false)}
        stats={cleanupStats}
        onCleanupComplete={(newStats) => setCleanupStats(newStats)}
      />
    </div>
  );
};

export default App;
