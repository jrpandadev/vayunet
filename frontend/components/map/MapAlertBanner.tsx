'use client';

import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  Flame,
  TrendingUp,
  Wind,
  Layers,
  MapPin,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  X,
  Radio,
  Clock,
  Sparkles,
  Maximize2,
} from 'lucide-react';
import { MapAlertItem, AlertSeverity, AlertType } from '@/lib/alerts';

export interface MapAlertBannerProps {
  alerts: MapAlertItem[];
  onInspect: (alert: MapAlertItem) => void;
  className?: string;
  selectedEventId?: string | null;
}

const SEVERITY_CONFIG: Record<
  AlertSeverity,
  {
    borderClass: string;
    badgeBg: string;
    badgeText: string;
    badgeBorder: string;
    badgeLabel: string;
    pulseBg: string;
  }
> = {
  CRITICAL: {
    borderClass: 'border-l-4 border-l-rose-600',
    badgeBg: 'bg-rose-50',
    badgeText: 'text-rose-800',
    badgeBorder: 'border-rose-200',
    badgeLabel: 'CRITICAL ALERT',
    pulseBg: 'bg-rose-600',
  },
  HIGH: {
    borderClass: 'border-l-4 border-l-orange-500',
    badgeBg: 'bg-orange-50',
    badgeText: 'text-orange-900',
    badgeBorder: 'border-orange-200',
    badgeLabel: 'HIGH SEVERITY',
    pulseBg: 'bg-orange-500',
  },
  MODERATE: {
    borderClass: 'border-l-4 border-l-amber-500',
    badgeBg: 'bg-amber-50',
    badgeText: 'text-amber-900',
    badgeBorder: 'border-amber-200',
    badgeLabel: 'MODERATE ALERT',
    pulseBg: 'bg-amber-500',
  },
  INFO: {
    borderClass: 'border-l-4 border-l-sky-500',
    badgeBg: 'bg-sky-50',
    badgeText: 'text-sky-800',
    badgeBorder: 'border-sky-200',
    badgeLabel: 'SURVEILLANCE NOTICE',
    pulseBg: 'bg-sky-500',
  },
};

const LAYER_LABELS: Record<string, string> = {
  riskZones: 'Risk Zones',
  hotspots: 'Emission Hotspots',
  fires: 'Fire Detections',
  observations: 'Citizen Evidence',
  events: 'Base Stations',
  wind: 'Wind Flow',
};

function getCategoryIcon(type: AlertType) {
  switch (type) {
    case 'FORECAST_WARNING':
      return TrendingUp;
    case 'RAPID_DETERIORATION':
      return AlertTriangle;
    case 'MAJOR_FIRE':
      return Flame;
    case 'EMISSION_HOTSPOT':
      return Wind;
    case 'HIGH_PM25':
    default:
      return Radio;
  }
}

export const MapAlertBanner: React.FC<MapAlertBannerProps> = ({
  alerts,
  onInspect,
  className = '',
  selectedEventId,
}) => {
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [isDismissed, setIsDismissed] = useState<boolean>(false);

  // If active alerts change and index is out of bounds, reset index
  useEffect(() => {
    if (currentIndex >= alerts.length) {
      setCurrentIndex(0);
    }
  }, [alerts.length, currentIndex]);

  if (!alerts || alerts.length === 0) {
    return null;
  }

  const currentAlert = alerts[currentIndex] || alerts[0];
  const config = SEVERITY_CONFIG[currentAlert.severity] || SEVERITY_CONFIG.HIGH;
  const CategoryIcon = getCategoryIcon(currentAlert.type);
  const totalAlerts = alerts.length;

  const handlePrev = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : totalAlerts - 1));
  };

  const handleNext = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentIndex((prev) => (prev < totalAlerts - 1 ? prev + 1 : 0));
  };

  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsDismissed(true);
  };

  const handleReopen = () => {
    setIsDismissed(false);
  };

  const handleInspectClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onInspect(currentAlert);
  };

  // ---------------------------------------------------------------------------
  // MINIMIZED FLOATING PILL (When user clicks dismiss ✕)
  // ---------------------------------------------------------------------------
  if (isDismissed) {
    return (
      <div
        className={`absolute top-14 sm:top-3.5 left-1/2 -translate-x-1/2 z-[850] pointer-events-auto select-none transition-all duration-200 animate-in fade-in ${className}`}
      >
        <button
          type="button"
          onClick={handleReopen}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#0a2540] text-white text-xs font-semibold shadow-lg hover:bg-[#0f2a3f] active:scale-95 transition-all border border-white/20 cursor-pointer backdrop-blur-md"
          title="Expand active environmental alerts"
          aria-label={`Expand ${totalAlerts} environmental alerts`}
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75 motion-reduce:hidden" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500" />
          </span>
          <span>🚨 <strong>{totalAlerts}</strong> Active {totalAlerts === 1 ? 'Alert' : 'Alerts'}</span>
          <span className="text-slate-300">•</span>
          <span className="text-[11px] text-sky-300 font-mono flex items-center gap-1">
            <span>View</span>
            <Maximize2 className="w-3 h-3" />
          </span>
        </button>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // EXPANDED PROMINENT ALERT BANNER
  // ---------------------------------------------------------------------------
  return (
    <div
      role="alert"
      aria-live="polite"
      className={`absolute top-14 sm:top-3.5 left-1/2 -translate-x-1/2 z-[850] w-[calc(100%-1.5rem)] sm:w-auto sm:min-w-[480px] sm:max-w-xl md:max-w-2xl pointer-events-auto select-none animate-in fade-in slide-in-from-top-2 duration-200 ${className}`}
      onMouseDown={(e) => e.stopPropagation()}
      onClick={(e) => e.stopPropagation()}
      onDoubleClick={(e) => e.stopPropagation()}
    >
      <div
        className={`bg-white/95 backdrop-blur-md border border-slate-300/90 shadow-2xl rounded-xl p-3 sm:p-3.5 transition-all duration-200 ${config.borderClass}`}
      >
        {/* Top Header Row: Severity Chip + Headline + Multi-Alert Pagination + Dismiss */}
        <div className="flex items-center justify-between gap-2 pb-1.5 border-b border-slate-100">
          {/* Left: Category Badge & Pulse */}
          <div className="flex items-center gap-2 min-w-0">
            <span
              className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-mono font-bold uppercase tracking-wider border ${config.badgeBg} ${config.badgeText} ${config.badgeBorder}`}
            >
              <span className="relative flex h-2 w-2">
                {currentAlert.severity === 'CRITICAL' && (
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75 motion-reduce:hidden" />
                )}
                <span className={`relative inline-flex rounded-full h-2 w-2 ${config.pulseBg}`} />
              </span>
              <CategoryIcon className="w-3 h-3 shrink-0" />
              <span>{config.badgeLabel}</span>
            </span>

            {/* Target Layer Indicator */}
            <span className="hidden md:inline-flex items-center gap-1 font-mono text-[10px] text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
              <Layers className="w-2.5 h-2.5 text-slate-400" />
              <span>{LAYER_LABELS[currentAlert.targetLayer] || currentAlert.targetLayer}</span>
            </span>
          </div>

          {/* Right: Pagination Controls & Dismiss Button */}
          <div className="flex items-center gap-1.5 shrink-0">
            {totalAlerts > 1 && (
              <div className="inline-flex items-center rounded-md border border-slate-200 bg-slate-50 p-0.5 text-[11px] font-mono">
                <button
                  type="button"
                  onClick={handlePrev}
                  className="p-1 rounded hover:bg-slate-200/70 text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
                  aria-label="Previous alert"
                  title="Previous alert"
                >
                  <ChevronLeft className="w-3 h-3" />
                </button>
                <span className="px-1.5 text-[10px] font-semibold text-slate-700">
                  {currentIndex + 1} of {totalAlerts}
                </span>
                <button
                  type="button"
                  onClick={handleNext}
                  className="p-1 rounded hover:bg-slate-200/70 text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
                  aria-label="Next alert"
                  title="Next alert"
                >
                  <ChevronRight className="w-3 h-3" />
                </button>
              </div>
            )}

            {/* Dismiss / Minimize button */}
            <button
              type="button"
              onClick={handleDismiss}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 active:bg-slate-200 transition-colors cursor-pointer"
              aria-label="Dismiss alert banner"
              title="Minimize alert banner"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Middle Row: Headline & Location & Metrics */}
        <div className="pt-2 pb-2">
          <div className="flex flex-wrap items-center justify-between gap-1.5 mb-1">
            <h3 className="font-bold text-xs sm:text-sm text-slate-900 flex items-center gap-1.5">
              <span>{currentAlert.headline}</span>
            </h3>

            {/* Real Metric Badge (PM2.5, Burn Area, etc.) */}
            {currentAlert.metricValue && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-slate-900 text-white shadow-2xs">
                {currentAlert.metricLabel && (
                  <span className="text-[9px] text-slate-300 font-normal uppercase">
                    {currentAlert.metricLabel}:
                  </span>
                )}
                <span>{currentAlert.metricValue}</span>
              </span>
            )}
          </div>

          {/* Location with Pin */}
          <div className="flex items-center gap-1.5 text-xs text-slate-600 mb-1.5 font-medium">
            <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0" />
            <span className="truncate">{currentAlert.locationName}</span>
            {currentAlert.horizon && (
              <>
                <span className="text-slate-300">•</span>
                <span className="text-[11px] font-mono text-slate-500">{currentAlert.horizon}</span>
              </>
            )}
          </div>

          {/* Real Descriptive Summary */}
          <p className="text-[11px] sm:text-xs text-slate-700 leading-relaxed">
            {currentAlert.description}
          </p>
        </div>

        {/* Bottom Row: Call-to-Action Bar */}
        <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
          <div className="text-[10px] text-slate-400 font-mono hidden sm:inline-flex items-center gap-1">
            <span>Entity:</span>
            <strong className="text-slate-700">{currentAlert.targetEntityId}</strong>
          </div>

          {/* Inspect Event Button */}
          <button
            type="button"
            onClick={handleInspectClick}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-3.5 py-1.5 bg-[#0a2540] hover:bg-[#0f2a3f] active:scale-98 text-white text-xs font-semibold rounded-lg shadow-sm transition-all cursor-pointer min-h-[36px]"
            title={`Inspect ${currentAlert.locationName} in detail`}
          >
            <span>Inspect Event</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default MapAlertBanner;
