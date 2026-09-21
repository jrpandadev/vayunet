'use client';

import React from 'react';
import { Layers, Wind, AlertCircle } from 'lucide-react';

interface SceneFallbackProps {
  title: string;
  description: string;
  layers?: Array<{ name: string; altitude: string; status: string; detail: string }>;
  reason?: 'unsupported' | 'reduced-motion' | 'loading';
}

export const SceneFallback: React.FC<SceneFallbackProps> = ({
  title,
  description,
  layers,
  reason = 'unsupported',
}) => {
  return (
    <div
      role="region"
      aria-label={title}
      className="w-full h-full min-h-[320px] bg-[#061827] border border-[rgba(0,213,255,0.14)] rounded-xl p-5 flex flex-col justify-between"
    >
      <div>
        <div className="flex items-center justify-between border-b border-[rgba(0,213,255,0.10)] pb-3 mb-4">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-[#00E5FF]" />
            <span className="text-xs font-bold uppercase tracking-wider text-[#E8F4FD]">
              {title}
            </span>
          </div>
          <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[rgba(0,213,255,0.08)] text-[#00E5FF] border border-[rgba(0,213,255,0.20)]">
            2D Telemetry Fallback
          </span>
        </div>

        <p className="text-xs text-[#7BA4BC] mb-4 leading-relaxed">
          {description}
        </p>

        {layers && layers.length > 0 && (
          <div className="space-y-2.5">
            {layers.map((layer, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2.5 rounded bg-[rgba(255,255,255,0.02)] border border-[rgba(0,213,255,0.08)]"
              >
                <div>
                  <span className="text-xs font-semibold text-[#E8F4FD] block">
                    {layer.name}
                  </span>
                  <span className="text-[10px] text-[#7BA4BC]">{layer.detail}</span>
                </div>
                <div className="text-right">
                  <span className="text-xs font-mono text-[#00E5FF] block">
                    {layer.altitude}
                  </span>
                  <span className="text-[10px] font-mono text-[#27E0C3]">
                    {layer.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-[rgba(0,213,255,0.08)] flex items-center justify-between text-[11px] text-[#2E5470]">
        <div className="flex items-center gap-1.5">
          <Wind className="w-3.5 h-3.5 text-[#00E5FF]" />
          <span>
            {reason === 'reduced-motion'
              ? 'Static view active (reduced-motion preference detected)'
              : '2D analytical mode active'}
          </span>
        </div>
        <span className="font-mono text-[10px] uppercase tracking-wider">
          Scientific Mode
        </span>
      </div>
    </div>
  );
};

export default SceneFallback;
