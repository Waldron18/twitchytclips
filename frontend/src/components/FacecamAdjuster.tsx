import React from 'react';
import { FacecamRect } from '../types';
import { Camera, Layout, Sliders, Eye } from 'lucide-react';

interface FacecamAdjusterProps {
  hasFacecam: boolean;
  rect: FacecamRect | null;
  onToggleFacecam: (enabled: boolean) => void;
  onRectChange: (rect: FacecamRect) => void;
}

export const FacecamAdjuster: React.FC<FacecamAdjusterProps> = ({
  hasFacecam,
  rect,
  onToggleFacecam,
  onRectChange,
}) => {
  const currentRect = rect || { x: 0.05, y: 0.05, w: 0.35, h: 0.35 };

  const updateParam = (key: keyof FacecamRect, value: number) => {
    onRectChange({
      ...currentRect,
      [key]: value,
    });
  };

  return (
    <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-800 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Camera className="w-4 h-4 text-brand-400" />
          <h4 className="text-xs font-bold text-zinc-200">Facecam Split-Screen Framing</h4>
        </div>
        <button
          type="button"
          onClick={() => onToggleFacecam(!hasFacecam)}
          className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition ${
            hasFacecam
              ? 'bg-brand-500/10 border-brand-500/40 text-brand-400'
              : 'bg-zinc-800 border-zinc-700 text-zinc-400'
          }`}
        >
          {hasFacecam ? 'Split-Screen Active' : 'Single Crop / Blur Mode'}
        </button>
      </div>

      {hasFacecam ? (
        <div className="space-y-3">
          <p className="text-[11px] text-zinc-400">
            OpenCV auto-detects streamer webcams in the top corners. You can fine-tune the crop boundary below:
          </p>

          <div className="grid grid-cols-2 gap-3 text-xs">
            {/* Position X */}
            <div>
              <div className="flex justify-between text-zinc-400 mb-1">
                <span>X Offset</span>
                <span className="font-mono text-zinc-200">{Math.round(currentRect.x * 100)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="80"
                value={Math.round(currentRect.x * 100)}
                onChange={(e) => updateParam('x', Number(e.target.value) / 100)}
                className="w-full accent-brand-500 h-1.5 bg-zinc-800 rounded-lg cursor-pointer"
              />
            </div>

            {/* Position Y */}
            <div>
              <div className="flex justify-between text-zinc-400 mb-1">
                <span>Y Offset</span>
                <span className="font-mono text-zinc-200">{Math.round(currentRect.y * 100)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="80"
                value={Math.round(currentRect.y * 100)}
                onChange={(e) => updateParam('y', Number(e.target.value) / 100)}
                className="w-full accent-brand-500 h-1.5 bg-zinc-800 rounded-lg cursor-pointer"
              />
            </div>

            {/* Width */}
            <div>
              <div className="flex justify-between text-zinc-400 mb-1">
                <span>Box Width</span>
                <span className="font-mono text-zinc-200">{Math.round(currentRect.w * 100)}%</span>
              </div>
              <input
                type="range"
                min="15"
                max="60"
                value={Math.round(currentRect.w * 100)}
                onChange={(e) => updateParam('w', Number(e.target.value) / 100)}
                className="w-full accent-brand-500 h-1.5 bg-zinc-800 rounded-lg cursor-pointer"
              />
            </div>

            {/* Height */}
            <div>
              <div className="flex justify-between text-zinc-400 mb-1">
                <span>Box Height</span>
                <span className="font-mono text-zinc-200">{Math.round(currentRect.h * 100)}%</span>
              </div>
              <input
                type="range"
                min="15"
                max="60"
                value={Math.round(currentRect.h * 100)}
                onChange={(e) => updateParam('h', Number(e.target.value) / 100)}
                className="w-full accent-brand-500 h-1.5 bg-zinc-800 rounded-lg cursor-pointer"
              />
            </div>
          </div>

          {/* Quick Corner Presets */}
          <div className="pt-2 border-t border-zinc-800/80 flex items-center justify-between">
            <span className="text-[11px] text-zinc-400">Corner Presets:</span>
            <div className="flex space-x-1.5">
              <button
                type="button"
                onClick={() => onRectChange({ x: 0.03, y: 0.05, w: 0.35, h: 0.35 })}
                className="px-2 py-0.5 rounded text-[10px] bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
              >
                Top-Left
              </button>
              <button
                type="button"
                onClick={() => onRectChange({ x: 0.62, y: 0.05, w: 0.35, h: 0.35 })}
                className="px-2 py-0.5 rounded text-[10px] bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
              >
                Top-Right
              </button>
              <button
                type="button"
                onClick={() => onRectChange({ x: 0.03, y: 0.60, w: 0.35, h: 0.35 })}
                className="px-2 py-0.5 rounded text-[10px] bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
              >
                Bottom-Left
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-3 bg-zinc-900 rounded-lg text-xs text-zinc-400">
          Single-Crop mode enabled: Center 9:16 gameplay framing with blurred background fill.
        </div>
      )}
    </div>
  );
};
