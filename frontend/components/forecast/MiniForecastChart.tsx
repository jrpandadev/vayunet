'use client';

import React, { useState, useEffect } from 'react';
import { EventForecast } from '@/lib/types';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from 'recharts';
import { TrendingUp, AlertTriangle } from 'lucide-react';

interface MiniForecastChartProps {
  forecast: EventForecast;
  currentPm25?: number | null;
  className?: string;
}

export const MiniForecastChart: React.FC<MiniForecastChartProps> = ({
  forecast,
  currentPm25 = null,
  className = '',
}) => {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Use only data from existing schema fields, filter out unavailable horizons
  const rawData = [
    { horizon: 'Current', pm25: currentPm25, label: 'Observed' },
    { horizon: '+6 Hours', pm25: forecast.pm25_6h, label: '6h Projected' },
    { horizon: '+24 Hours', pm25: forecast.pm25_24h, label: '24h Projected' },
    { horizon: '+72 Hours', pm25: forecast.pm25_72h, label: '72h Projected' },
  ];

  const data = rawData.filter(d => d.pm25 != null);

  const maxVal = Math.max(
    ...data.map(d => d.pm25 as number),
    70
  );

  return (
    <div className={`bg-white border border-[#e2e8f0] rounded-lg p-5 shadow-xs ${className}`}>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-[#0a2540]" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-[#0f172a]">
              PM2.5 Forecast (6h / 24h / 72h)
            </h4>
          </div>
          <p className="text-[11px] text-[#64748b] mt-0.5">
            Multi-horizon PM2.5 forecast vs. WHO (15 µg/m³) & National NAAQS (60 µg/m³)
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded bg-orange-50 text-orange-800 border border-orange-200">
            <AlertTriangle className="w-3 h-3 text-orange-600" />
            Spike Risk: {forecast.spike_probability}
          </span>
        </div>
      </div>

      <div className="h-56 w-full">
        {isMounted ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 20, left: -10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis
                dataKey="horizon"
                tick={{ fontSize: 11, fill: '#64748b' }}
                axisLine={{ stroke: '#cbd5e1' }}
                tickLine={false}
              />
              <YAxis
                domain={[0, Math.ceil(maxVal * 1.15)]}
                tick={{ fontSize: 10, fill: '#64748b' }}
                axisLine={false}
                tickLine={false}
                unit=" µg"
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload;
                    return (
                      <div className="bg-slate-900 text-white text-xs p-2.5 rounded shadow-lg border border-slate-800 font-mono">
                        <div className="text-slate-400 text-[10px]">{d.label}</div>
                        <div className="text-base font-bold text-sky-300">
                          {d.pm25} µg/m³
                        </div>
                        <div className="text-[10px] text-slate-300 mt-1 border-t border-slate-700 pt-1">
                          WHO Limit: 15 | NAAQS: 60
                        </div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              {/* Reference Lines */}
              <ReferenceLine
                y={15}
                stroke="#22c55e"
                strokeDasharray="4 4"
                label={{
                  value: 'WHO Limit (15)',
                  position: 'insideTopLeft',
                  fill: '#15803d',
                  fontSize: 10,
                }}
              />
              <ReferenceLine
                y={60}
                stroke="#f97316"
                strokeDasharray="4 4"
                label={{
                  value: 'NAAQS Limit (60)',
                  position: 'insideTopLeft',
                  fill: '#c2410c',
                  fontSize: 10,
                }}
              />
              <Line
                type="monotone"
                dataKey="pm25"
                stroke="#0a2540"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#0a2540', stroke: '#ffffff', strokeWidth: 2 }}
                activeDot={{ r: 6, fill: '#0284c7' }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-xs text-slate-400">
            Rendering forecast telemetry...
          </div>
        )}
      </div>

      <div className="mt-3 pt-2.5 border-t border-slate-100 flex flex-wrap items-center justify-between text-[11px] text-[#64748b]">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-[#0a2540]" />
            <span>PM2.5 Forecast</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-[#f97316]" />
            <span>NAAQS (60 µg/m³)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-[#22c55e]" />
            <span>WHO (15 µg/m³)</span>
          </span>
        </div>
        <span className="font-mono text-slate-400 text-[10px]">
          Model: Local ML Gradient Boost
        </span>
      </div>
    </div>
  );
};

export default MiniForecastChart;
