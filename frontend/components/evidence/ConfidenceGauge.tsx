import React from 'react';
import { EventDetection, EventForecast, SourceHypothesis } from '@/lib/types';
import { ShieldCheck, HelpCircle, Flame, AlertCircle } from 'lucide-react';

interface ConfidenceGaugeProps {
  detection: EventDetection;
  forecast: EventForecast;
  hypothesis: SourceHypothesis;
  className?: string;
}

const UNCERTAINTY_STYLES = {
  LOW: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  MEDIUM: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  HIGH: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
};

function formatCategory(category: string): string {
  return category
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export const ConfidenceGauge: React.FC<ConfidenceGaugeProps> = ({
  detection,
  forecast,
  hypothesis,
  className = '',
}) => {
  const percentage = Math.round(detection.confidence * 100);
  const hypothesisPct = Math.round(hypothesis.confidence * 100);
  const uncertainty = forecast.forecast_uncertainty;
  const uncertaintyStyle = UNCERTAINTY_STYLES[uncertainty] || UNCERTAINTY_STYLES.MEDIUM;

  return (
    <div className={`grid grid-cols-1 md:grid-cols-3 gap-4 ${className}`}>
      {/* 1. Detection Confidence Gauge */}
      <div className="bg-white border border-[#e2e8f0] rounded-lg p-4 shadow-xs flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-[#64748b]">
              Detection Confidence
            </span>
            <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
              {detection.method || 'multi_source_fusion'}
            </span>
          </div>

          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-[#0f172a] tabular-telemetry">
              {percentage}%
            </span>
            <span className="text-xs text-slate-500 font-mono">
              ({detection.confidence.toFixed(2)})
            </span>
          </div>

          {/* Progress gauge bar */}
          <div className="mt-2.5 h-2 w-full bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 rounded-full ${
                percentage >= 80
                  ? 'bg-[#0a2540]'
                  : percentage >= 50
                  ? 'bg-sky-600'
                  : 'bg-amber-500'
              }`}
              style={{ width: `${percentage}%` }}
              role="progressbar"
              aria-valuenow={percentage}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
        </div>

        <p className="mt-3 text-[11px] text-[#64748b] flex items-center gap-1 border-t border-slate-100 pt-2">
          <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
          <span>Calculated from multi-source cross-validation</span>
        </p>
      </div>

      {/* 2. Forecast Forward Uncertainty (Strictly Separate from Confidence) */}
      <div className="bg-white border border-[#e2e8f0] rounded-lg p-4 shadow-xs flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-[#64748b]">
              Forecast Uncertainty
            </span>
            <span
              className={`text-xs px-2 py-0.5 rounded font-bold uppercase tracking-wider border ${uncertaintyStyle.bg} ${uncertaintyStyle.text} ${uncertaintyStyle.border}`}
            >
              {uncertainty} UNCERTAINTY
            </span>
          </div>

          <div className="mt-3">
            <p className="text-sm font-semibold text-slate-800">
              Forecast Horizon
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Spike Probability:{' '}
              <strong className="text-slate-800 uppercase font-mono">
                {forecast.spike_probability}
              </strong>
            </p>
          </div>
        </div>

        <p className="mt-3 text-[11px] text-[#64748b] flex items-center gap-1 border-t border-slate-100 pt-2">
          <HelpCircle className="w-3.5 h-3.5 text-amber-500" />
          <span>Represents weather/model variability over the 72h forecast horizon, distinct from detection confidence.</span>
        </p>
      </div>

      {/* 3. Source Hypothesis (Probabilistic, not fact) */}
      <div className="bg-white border border-[#e2e8f0] rounded-lg p-4 shadow-xs flex flex-col justify-between border-l-4 border-l-sky-500">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-[#64748b]">
              Source Hypothesis
            </span>
            <span className="text-[10px] font-mono text-sky-800 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
              Probabilistic Estimate
            </span>
          </div>

          <div className="mt-3">
            <div className="flex items-center gap-2">
              <Flame className="w-5 h-5 text-orange-500" />
              <span className="text-base font-bold text-[#0f172a]">
                {formatCategory(hypothesis.category)}
              </span>
            </div>
            <p className="text-xs text-slate-600 mt-1">
              Hypothesis Model Confidence:{' '}
              <strong className="text-slate-900 font-mono tabular-telemetry">
                {hypothesisPct}%
              </strong>
            </p>
          </div>
        </div>

        <p className="mt-3 text-[11px] text-[#64748b] flex items-center gap-1 border-t border-slate-100 pt-2 italic">
          <AlertCircle className="w-3.5 h-3.5 text-sky-600 shrink-0" />
          <span>Probabilistic hypothesis subject to field confirmation.</span>
        </p>
      </div>
    </div>
  );
};

export default ConfidenceGauge;
