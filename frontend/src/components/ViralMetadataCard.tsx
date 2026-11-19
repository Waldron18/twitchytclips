import React, { useState } from 'react';
import { Sparkles, Copy, Check, Hash, Video, Share2 } from 'lucide-react';

interface ViralMetadataCardProps {
  title: string;
  description: string | null;
  hashtags: string;
  onTitleChange: (newTitle: string) => void;
}

export const ViralMetadataCard: React.FC<ViralMetadataCardProps> = ({
  title,
  description,
  hashtags,
  onTitleChange,
}) => {
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  return (
    <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-800 space-y-3.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-purple-400" />
          <h4 className="text-xs font-bold text-zinc-200">AI Viral Metadata (YouTube Shorts & Reels)</h4>
        </div>
        <div className="flex items-center space-x-2 text-[11px] text-zinc-400">
          <span className="flex items-center space-x-1 text-red-400 font-semibold">
            <Video className="w-3.5 h-3.5" /> <span>Shorts</span>
          </span>
          <span>•</span>
          <span className="flex items-center space-x-1 text-pink-400 font-semibold">
            <Share2 className="w-3.5 h-3.5" /> <span>Reels</span>
          </span>
        </div>
      </div>

      {/* High-CTR Title */}
      <div>
        <div className="flex justify-between items-center text-xs text-zinc-400 mb-1">
          <span>High-CTR Title</span>
          <button
            type="button"
            onClick={() => copyToClipboard(title, 'title')}
            className="flex items-center space-x-1 text-zinc-400 hover:text-white transition"
          >
            {copiedField === 'title' ? (
              <>
                <Check className="w-3 h-3 text-emerald-400" />
                <span className="text-[10px] text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span className="text-[10px]">Copy</span>
              </>
            )}
          </button>
        </div>
        <input
          type="text"
          value={title}
          onChange={(e) => onTitleChange(e.target.value)}
          className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs font-semibold text-white focus:outline-none focus:border-brand-500 transition"
        />
      </div>

      {/* Description */}
      {description && (
        <div>
          <div className="flex justify-between items-center text-xs text-zinc-400 mb-1">
            <span>Caption / Description</span>
            <button
              type="button"
              onClick={() => copyToClipboard(description, 'desc')}
              className="flex items-center space-x-1 text-zinc-400 hover:text-white transition"
            >
              {copiedField === 'desc' ? (
                <>
                  <Check className="w-3 h-3 text-emerald-400" />
                  <span className="text-[10px] text-emerald-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span className="text-[10px]">Copy</span>
                </>
              )}
            </button>
          </div>
          <p className="bg-zinc-900/60 p-2.5 rounded-lg border border-zinc-800/80 text-xs text-zinc-300">
            {description}
          </p>
        </div>
      )}

      {/* Hashtags */}
      <div>
        <div className="flex justify-between items-center text-xs text-zinc-400 mb-1">
          <span>Viral Hashtags</span>
          <button
            type="button"
            onClick={() => copyToClipboard(hashtags, 'tags')}
            className="flex items-center space-x-1 text-zinc-400 hover:text-white transition"
          >
            {copiedField === 'tags' ? (
              <>
                <Check className="w-3 h-3 text-emerald-400" />
                <span className="text-[10px] text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span className="text-[10px]">Copy</span>
              </>
            )}
          </button>
        </div>
        <div className="bg-zinc-900/60 p-2 rounded-lg border border-zinc-800/80 text-xs font-mono text-brand-400">
          {hashtags}
        </div>
      </div>
    </div>
  );
};
