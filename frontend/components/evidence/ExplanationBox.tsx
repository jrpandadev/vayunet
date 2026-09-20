import React from 'react';
import { Sparkles, Info } from 'lucide-react';

interface ExplanationBoxProps {
  explanation: string;
  className?: string;
}

function sanitizeExplanation(text: string): string {
  if (!text) return '';
  return text
    .replace(/satellite confirms elevated NO2/gi, 'satellite provides corroborating evidence of elevated NO₂')
    .replace(/satellite confirms elevated NO₂/gi, 'satellite provides corroborating evidence of elevated NO₂')
    .replace(/\bconfirms\b/gi, 'provides corroborating evidence of');
}

export const ExplanationBox: React.FC<ExplanationBoxProps> = ({
  explanation,
  className = '',
}) => {
  const sanitized = sanitizeExplanation(explanation);

  return (
    <div
      className={`rounded-lg border border-sky-200 bg-gradient-to-r from-sky-50/70 via-white to-sky-50/40 p-5 shadow-xs ${className}`}
    >
      <div className="flex items-center justify-between gap-2 pb-2.5 border-b border-sky-100">
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 rounded bg-sky-600 text-white flex items-center justify-center shadow-xs">
            <Sparkles className="w-3.5 h-3.5" />
          </div>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#0a2540]">
              Gemini AI Multimodal Synthesis & Evidence Reasoning
            </h3>
          </div>
        </div>
        <span className="text-[10px] font-mono font-medium text-sky-800 bg-sky-100/80 px-2 py-0.5 rounded border border-sky-200 uppercase">
          Synthesized Analysis
        </span>
      </div>

      <div className="mt-3">
        <p className="text-sm font-medium text-slate-800 leading-relaxed">
          &ldquo;{sanitized}&rdquo;
        </p>
      </div>

      <div className="mt-3 pt-2.5 border-t border-sky-100/60 flex items-center gap-1.5 text-[11px] text-[#64748b]">
        <Info className="w-3.5 h-3.5 text-sky-600 shrink-0" />
        <span>
          AI-generated situational interpretation synthesizing ground, satellite, and crowdsourced data. Probabilistic guidance intended for authority review, not definitive statutory finding.
        </span>
      </div>
    </div>
  );
};

export default ExplanationBox;
