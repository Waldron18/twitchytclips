import React, { useState, useRef, useEffect } from 'react';
import { Clip, MusicTrack, FacecamRect, WordToken } from '../types';
import {
  Play, Pause, Download, Sparkles, Music, Type, CheckCircle,
  Film, AlertCircle, Share2, Layers, RefreshCw, Volume2, Loader2
} from 'lucide-react';
import { FacecamAdjuster } from './FacecamAdjuster';
import { TranscriptEditor } from './TranscriptEditor';
import { ViralMetadataCard } from './ViralMetadataCard';
import { api } from '../services/api';

interface ClipReviewEditorProps {
  clip: Clip;
  musicTracks: MusicTrack[];
  onUpdateClip: (updated: Clip) => void;
  onTriggerRender: (clipId: string) => void;
}

export const ClipReviewEditor: React.FC<ClipReviewEditorProps> = ({
  clip,
  musicTracks,
  onUpdateClip,
  onTriggerRender,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [saving, setSaving] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Auto-sync current time for word-highlighting
  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleSeek = (timeInSeconds: number) => {
    if (videoRef.current) {
      // Offset relative to clip start
      const relTime = Math.max(0, timeInSeconds - clip.start_time);
      videoRef.current.currentTime = relTime;
      setCurrentTime(relTime);
      if (!isPlaying) {
        videoRef.current.play();
        setIsPlaying(true);
      }
    }
  };

  const handleSaveParam = async (partial: Partial<Clip>) => {
    try {
      setSaving(true);
      const updated = await api.updateClip(clip.id, partial);
      onUpdateClip(updated);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-fadeIn">
      {/* Left Column: 9:16 Video Player & Canvas Preview */}
      <div className="lg:col-span-5 flex flex-col items-center">
        <div className="relative w-full max-w-[340px] aspect-[9/16] bg-black rounded-3xl overflow-hidden border-2 border-zinc-800 shadow-2xl flex flex-col items-center justify-center">
          {clip.rendered_video_path ? (
            <>
              <video
                ref={videoRef}
                src={clip.rendered_video_path}
                onTimeUpdate={handleTimeUpdate}
                onEnded={() => setIsPlaying(false)}
                className="w-full h-full object-cover"
                playsInline
                loop
              />
              {/* Play / Pause Overlay Button */}
              <button
                type="button"
                onClick={togglePlay}
                className="absolute inset-0 flex items-center justify-center bg-black/20 hover:bg-black/40 transition group"
              >
                {!isPlaying && (
                  <div className="w-14 h-14 rounded-full bg-brand-600/90 text-white flex items-center justify-center shadow-lg transform group-hover:scale-110 transition">
                    <Play className="w-6 h-6 ml-1" />
                  </div>
                )}
              </button>
            </>
          ) : (
            /* Unrendered Split-Screen Canvas Wireframe Preview */
            <div className="w-full h-full flex flex-col p-3 bg-gradient-to-b from-zinc-950 to-zinc-900 justify-between relative select-none">
              {/* Top 35% Facecam wireframe */}
              <div className="w-full h-[35%] rounded-2xl border-2 border-dashed border-brand-500/50 bg-brand-950/20 flex flex-col items-center justify-center p-4 text-center">
                <span className="text-xs font-bold text-brand-300 uppercase tracking-wide">
                  Top 35% Facecam Framing
                </span>
                <span className="text-[10px] text-zinc-400 mt-1">
                  {clip.has_facecam ? 'Auto-scaled to 1080x672' : 'Full blur mode'}
                </span>
              </div>

              {/* Center divider badge */}
              <div className="flex items-center justify-center -my-2 z-10">
                <span className="px-2 py-0.5 rounded-full bg-zinc-800 text-[10px] text-zinc-400 font-mono">
                  1080 x 1920 (9:16 Shorts)
                </span>
              </div>

              {/* Bottom 65% Gameplay wireframe */}
              <div className="w-full h-[62%] rounded-2xl border-2 border-dashed border-indigo-500/50 bg-indigo-950/20 flex flex-col items-center justify-center p-4 text-center">
                <span className="text-xs font-bold text-indigo-300 uppercase tracking-wide">
                  Bottom 65% Gameplay Screen
                </span>
                <span className="text-[10px] text-zinc-400 mt-1">
                  1080x1248 high-retention focus
                </span>
                {/* Subtitle preview mock */}
                <div className="mt-8 px-3 py-1.5 rounded-lg bg-black/60 border border-zinc-700/60 text-xs font-black uppercase text-amber-400">
                  {clip.hook_summary || 'VIRAL MOMENT READY'}
                </div>
              </div>
            </div>
          )}

          {/* Badge Overlay */}
          <div className="absolute top-3 left-3 bg-black/70 backdrop-blur-md px-2.5 py-1 rounded-full text-[11px] font-bold text-white border border-white/10 flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
            <span>Rank #{clip.viral_rank}</span>
            <span className="text-zinc-400">•</span>
            <span className="text-amber-400 font-mono">{clip.hype_score} Hype</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="w-full max-w-[340px] mt-4 flex space-x-2">
          {clip.rendered_video_path ? (
            <a
              href={clip.rendered_video_path}
              download
              className="flex-1 flex items-center justify-center space-x-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs py-3 rounded-xl shadow-lg shadow-emerald-500/20 transition active:scale-95"
            >
              <Download className="w-4 h-4" />
              <span>Download MP4</span>
            </a>
          ) : (
            <button
              type="button"
              disabled={clip.status === 'rendering'}
              onClick={() => onTriggerRender(clip.id)}
              className="flex-1 flex items-center justify-center space-x-2 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-bold text-xs py-3 rounded-xl shadow-lg shadow-brand-500/25 transition active:scale-95 disabled:opacity-50"
            >
              {clip.status === 'rendering' ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Rendering...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Render 9:16 Short</span>
                </>
              )}
            </button>
          )}

          {clip.rendered_video_path && (
            <button
              type="button"
              disabled={clip.status === 'rendering'}
              onClick={() => onTriggerRender(clip.id)}
              className="px-3 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl text-xs font-semibold border border-zinc-700 transition"
              title="Re-render with updated settings"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Right Column: Studio Customization Suite */}
      <div className="lg:col-span-7 space-y-4">
        {/* Viral Metadata (Title & Hashtags) */}
        <ViralMetadataCard
          title={clip.title}
          description={clip.description}
          hashtags={clip.hashtags}
          onTitleChange={(title) => handleSaveParam({ title })}
        />

        {/* Facecam Adjuster */}
        <FacecamAdjuster
          hasFacecam={clip.has_facecam}
          rect={clip.facecam_rect}
          onToggleFacecam={(has_facecam) => handleSaveParam({ has_facecam })}
          onRectChange={(facecam_rect) => handleSaveParam({ facecam_rect })}
        />

        {/* Word-level Transcript & Dead Air Trimmer */}
        <TranscriptEditor
          words={clip.words}
          currentTime={currentTime + clip.start_time}
          onWordsChange={(words) => handleSaveParam({ words })}
          onSeekTo={handleSeek}
        />

        {/* Audio & Subtitle Styling Preferences */}
        <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-800 space-y-3.5">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-brand-400" />
            <h4 className="text-xs font-bold text-zinc-200">Audio & Animated Captions Styling</h4>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            {/* Background Audio Selection */}
            <div>
              <label className="flex items-center space-x-1.5 text-zinc-400 mb-1 font-medium">
                <Music className="w-3.5 h-3.5 text-brand-400" />
                <span>Royalty-Free BGM (-14 LUFS)</span>
              </label>
              <select
                value={clip.bgm_track}
                onChange={(e) => handleSaveParam({ bgm_track: e.target.value })}
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500 cursor-pointer"
              >
                <option value="none">No Background Music (Isolated Speech Only)</option>
                {musicTracks.map((m) => (
                  <option key={m.filename} value={m.filename}>
                    {m.name} (-24 dB)
                  </option>
                ))}
              </select>
            </div>

            {/* Subtitle Animated Preset */}
            <div>
              <label className="flex items-center space-x-1.5 text-zinc-400 mb-1 font-medium">
                <Type className="w-3.5 h-3.5 text-amber-400" />
                <span>Karaoke Caption Preset</span>
              </label>
              <select
                value={clip.subtitle_style}
                onChange={(e) => handleSaveParam({ subtitle_style: e.target.value as any })}
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500 cursor-pointer"
              >
                <option value="karaoke_yellow">Karaoke Radiant Gold (Viral Standard)</option>
                <option value="neon_green">Neon Cyber Green (Gaming Hype)</option>
                <option value="clean_white">Minimalist Studio White</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
