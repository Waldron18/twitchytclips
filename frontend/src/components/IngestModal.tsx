import React, { useState } from 'react';
import { Sparkles, Video, Tv, UploadCloud, Link as LinkIcon, HardDrive, X, Loader2 } from 'lucide-react';
import { api } from '../services/api';

interface IngestModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultStorageSaver: boolean;
  onProjectCreated: (projectId: string, jobId: string) => void;
}

export const IngestModal: React.FC<IngestModalProps> = ({
  isOpen,
  onClose,
  defaultStorageSaver,
  onProjectCreated,
}) => {
  const [activeTab, setActiveTab] = useState<'url' | 'upload'>('url');
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [storageSaver, setStorageSaver] = useState<boolean>(defaultStorageSaver);
  const [targetClips, setTargetClips] = useState<number>(5);
  const [liveCaptureSeconds, setLiveCaptureSeconds] = useState<number>(45);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const isLiveStreamUrl = (str: string) => {
    const s = str.toLowerCase();
    // e.g. twitch.tv/username without /videos/ or /clip/
    if (s.includes('twitch.tv/') && !s.includes('/videos/') && !s.includes('/clip/')) return true;
    if (s.includes('kick.com/') && !s.includes('/video/')) return true;
    if (s.includes('/live')) return true;
    return false;
  };

  const isLive = isLiveStreamUrl(url);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (activeTab === 'url') {
        if (!url.trim()) {
          throw new Error('Please enter a valid video stream URL');
        }
        const liveMinutes = Math.max(1, Math.ceil(liveCaptureSeconds / 60));
        const res = await api.createProject(
          url.trim(),
          storageSaver,
          targetClips,
          liveMinutes,
          isLive ? liveCaptureSeconds : undefined
        );
        onProjectCreated(res.project_id, res.job_id);
      } else {
        if (!file) {
          throw new Error('Please select a local video file to upload');
        }
        const res = await api.uploadFile(file);
        onProjectCreated(res.project_id, res.job_id);
      }
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to submit project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-xl p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-zinc-400 hover:text-white transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-5">
          <div className="p-2.5 rounded-xl bg-gradient-to-tr from-brand-600 to-purple-600 text-white shadow-md shadow-brand-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Create Video Clipping Job</h3>
            <p className="text-xs text-zinc-400">Ingest from YouTube, Twitch, Kick, or local files</p>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-zinc-800 mb-5">
          <button
            type="button"
            onClick={() => setActiveTab('url')}
            className={`flex items-center space-x-2 pb-3 px-4 text-sm font-semibold border-b-2 transition ${
              activeTab === 'url'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <LinkIcon className="w-4 h-4" />
            <span>Stream / Video URL</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('upload')}
            className={`flex items-center space-x-2 pb-3 px-4 text-sm font-semibold border-b-2 transition ${
              activeTab === 'upload'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Local File</span>
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {activeTab === 'url' ? (
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                Video or Stream URL
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=... or Twitch / Kick URL"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-brand-500 transition"
                  autoFocus
                />
              </div>
              <div className="flex items-center space-x-2 mt-2 text-[11px] text-zinc-500">
                <span>Supported:</span>
                <span className="flex items-center space-x-1 text-zinc-400"><Video className="w-3 h-3 text-red-400" /> YouTube VODs</span>
                <span>•</span>
                <span className="flex items-center space-x-1 text-zinc-400"><Tv className="w-3 h-3 text-purple-400" /> Twitch (Live & VODs)</span>
                <span>•</span>
                <span className="text-zinc-400">Kick Streams</span>
              </div>

              {/* Twitch Live Stream Mode Banner & Duration Selector */}
              {isLive && (
                <div className="mt-3 p-3.5 bg-purple-950/40 border border-purple-800/50 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-purple-300 flex items-center space-x-1.5">
                      <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                      <span>Live Stream Detected</span>
                    </span>
                    <span className="text-[10px] text-zinc-400 font-mono">⚡ High-Speed Clip</span>
                  </div>
                  <p className="text-[11px] text-zinc-300">
                    Live streams record in real-time. Choose your capture window to extract viral 9:16 short clips:
                  </p>
                  <div className="flex items-center space-x-2 pt-1">
                    {[
                      { sec: 30, label: '30s (Ultra)' },
                      { sec: 45, label: '45s (Fast)' },
                      { sec: 60, label: '1m (Standard)' },
                      { sec: 120, label: '2m' },
                      { sec: 300, label: '5m' }
                    ].map(({ sec, label }) => (
                      <button
                        key={sec}
                        type="button"
                        onClick={() => setLiveCaptureSeconds(sec)}
                        className={`flex-1 py-1 text-xs font-bold rounded-lg border transition ${
                          liveCaptureSeconds === sec
                            ? 'bg-purple-600 border-purple-400 text-white shadow-sm'
                            : 'bg-zinc-900 border-zinc-700 text-zinc-400 hover:text-white'
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <div className="text-[10px] text-zinc-400 italic pt-0.5">
                    💡 Tip: For past stream moments without waiting, paste the VOD URL from <span className="text-purple-300 font-mono">twitch.tv/channel/videos</span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">
                Select Local Video File (.mp4, .mkv, .mov, .ts)
              </label>
              <div className="border-2 border-dashed border-zinc-800 hover:border-zinc-700 rounded-xl p-6 text-center bg-zinc-950/50 cursor-pointer">
                <input
                  type="file"
                  accept="video/*"
                  onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
                  className="hidden"
                  id="video-upload"
                />
                <label htmlFor="video-upload" className="cursor-pointer">
                  <UploadCloud className="w-8 h-8 text-zinc-400 mx-auto mb-2" />
                  <span className="text-xs text-zinc-300 font-medium block">
                    {file ? file.name : 'Click to browse or drag and drop video'}
                  </span>
                  <span className="text-[11px] text-zinc-500 mt-1 block">
                    Direct local parsing without uploading to the cloud
                  </span>
                </label>
              </div>
            </div>
          )}

          {/* Options Row */}
          <div className="bg-zinc-950/70 p-4 rounded-xl border border-zinc-800/80 space-y-3">
            {/* Storage Saver Mode Switch */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <HardDrive className="w-4 h-4 text-emerald-400" />
                <div>
                  <span className="text-xs font-semibold text-zinc-200 block">Storage Saver Mode</span>
                  <span className="text-[11px] text-zinc-400 block">
                    Extracts audio first. Downloads 60s video slices only for accepted clips.
                  </span>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={storageSaver}
                  onChange={(e) => setStorageSaver(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-zinc-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-500"></div>
              </label>
            </div>

            {/* Target Clips Count */}
            <div className="flex items-center justify-between pt-2 border-t border-zinc-800/60">
              <span className="text-xs text-zinc-300 font-medium">Clips to Extract</span>
              <div className="flex items-center space-x-2">
                {[3, 5, 8].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setTargetClips(n)}
                    className={`px-2.5 py-1 text-xs rounded-lg font-semibold border transition ${
                      targetClips === n
                        ? 'bg-brand-600 border-brand-500 text-white'
                        : 'bg-zinc-800/60 border-zinc-700/60 text-zinc-400 hover:text-white'
                    }`}
                  >
                    {n} Clips
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-zinc-400 hover:text-white transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-brand-500/20 transition disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Start AI Clipping</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
