import React from 'react';
import { WordToken } from '../types';
import { FileText, Scissors, RotateCcw, Volume2 } from 'lucide-react';

interface TranscriptEditorProps {
  words: WordToken[];
  currentTime?: number;
  onWordsChange: (words: WordToken[]) => void;
  onSeekTo?: (time: number) => void;
}

export const TranscriptEditor: React.FC<TranscriptEditorProps> = ({
  words,
  currentTime = 0,
  onWordsChange,
  onSeekTo,
}) => {
  const toggleWordDeleted = (index: number) => {
    const updated = [...words];
    updated[index] = {
      ...updated[index],
      deleted: !updated[index].deleted,
    };
    onWordsChange(updated);
  };

  const autoTrimFillers = () => {
    const FILLERS = new Set(['um', 'uh', 'er', 'ah', 'like', 'literally', 'basically']);
    const updated = words.map((w) => {
      const clean = w.word.toLowerCase().replace(/[^a-z]/g, '');
      if (FILLERS.has(clean)) {
        return { ...w, deleted: true };
      }
      return w;
    });
    onWordsChange(updated);
  };

  const resetAllWords = () => {
    const updated = words.map((w) => ({ ...w, deleted: false }));
    onWordsChange(updated);
  };

  const activeCount = words.filter((w) => !w.deleted).length;
  const deletedCount = words.length - activeCount;

  return (
    <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-800 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FileText className="w-4 h-4 text-brand-400" />
          <h4 className="text-xs font-bold text-zinc-200">Word-Level Transcript & Dead-Air Trimmer</h4>
        </div>
        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={autoTrimFillers}
            className="flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 transition"
            title="Auto-detect and delete filler words"
          >
            <Scissors className="w-3.5 h-3.5 text-amber-400" />
            <span>Trim Fillers</span>
          </button>
          {deletedCount > 0 && (
            <button
              type="button"
              onClick={resetAllWords}
              className="flex items-center space-x-1 px-2 py-1 rounded-lg text-xs text-zinc-400 hover:text-white"
              title="Reset all deleted words"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      <p className="text-[11px] text-zinc-400">
        Click any word to strike through and remove from video/captions. Double-click to jump to that timestamp:
      </p>

      {/* Words Container */}
      <div className="max-h-48 overflow-y-auto p-3 bg-zinc-900/60 rounded-xl border border-zinc-800/80 flex flex-wrap gap-1.5 leading-relaxed">
        {words.length === 0 ? (
          <span className="text-xs text-zinc-500 italic">No spoken words detected in this segment.</span>
        ) : (
          words.map((w, idx) => {
            const isPlaying = currentTime >= w.start && currentTime <= w.end;
            return (
              <span
                key={idx}
                onClick={() => toggleWordDeleted(idx)}
                onDoubleClick={() => onSeekTo && onSeekTo(w.start)}
                className={`text-xs px-1.5 py-0.5 rounded cursor-pointer select-none transition ${
                  w.deleted
                    ? 'line-through text-zinc-600 bg-zinc-950/40 opacity-60'
                    : isPlaying
                    ? 'bg-amber-400 text-black font-extrabold shadow-sm scale-105'
                    : 'text-zinc-200 hover:bg-zinc-800 hover:text-white'
                }`}
                title={`[${w.start.toFixed(2)}s - ${w.end.toFixed(2)}s] Click to delete, double-click to play`}
              >
                {w.word}
              </span>
            );
          })
        )}
      </div>

      <div className="flex justify-between items-center text-[11px] text-zinc-500 pt-1">
        <span>{activeCount} words active</span>
        {deletedCount > 0 && (
          <span className="text-amber-400 font-medium">{deletedCount} filler words trimmed</span>
        )}
      </div>
    </div>
  );
};
