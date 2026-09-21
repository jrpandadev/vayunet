'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { getEvents, getForecast } from '@/lib/api';
import { PollutionEvent, ForecastPoint } from '@/lib/types';
import DashboardHeader from '@/components/layout/DashboardHeader';
import Card, { CardHeader, CardContent } from '@/components/ui/Card';
import RiskBadge from '@/components/ui/RiskBadge';
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
import {
  TrendingUp,
  AlertTriangle,
  HelpCircle,
  Clock,
  Shield,
  MapPin,
  CheckCircle2,
  Calendar,
  Layers,
} from 'lucide-react';

export default function ForecastPage() {
  const [events, setEvents] = useState<PollutionEvent[]>([]);
  const [loadingEvents, setLoadingEvents] = useState<boolean>(true);
  const [selectedCity, setSelectedCity] = useState<string>('Delhi');
  const [selectedHorizon, setSelectedHorizon] = useState<6 | 24 | 72>(24);
  const [forecastPoints, setForecastPoints] = useState<ForecastPoint[]>([]);
  const [loadingForecast, setLoadingForecast] = useState<boolean>(true);
  const [apiError, setApiError] = useState<string | null>(null);
  const [eventsError, setEventsError] = useState<string | null>(null);

  // Load events to obtain monitored cities and active baseline data
  useEffect(() => {
    async function loadInitialData() {
      setLoadingEvents(true);
      setEventsError(null);
      try {
        const data = await getEvents();
        setEvents(data);
        if (data.length > 0) {
          setSelectedCity(data[0].location.city);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error('Failed to load events for forecast:', err);
        setEventsError(msg);
        setEvents([]);
      } finally {
        setLoadingEvents(false);
      }
    }
    loadInitialData();
  }, []);

  // Fetch forecast progression when city or horizon changes
  useEffect(() => {
    async function loadForecastData() {
      if (!selectedCity) return;
      setLoadingForecast(true);
      setApiError(null);
      try {
        const points = await getForecast(selectedCity, selectedHorizon);
        setForecastPoints(points);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error('Failed to load forecast data:', err);
        setApiError(msg);
        setForecastPoints([]);
      } finally {
        setLoadingForecast(false);
      }
    }
    loadForecastData();
  }, [selectedCity, selectedHorizon]);

  // Extract distinct cities
  const cities = useMemo(() => {
    const set = new Set<string>();
    events.forEach((e) => set.add(e.location.city));
    return Array.from(set).sort();
  }, [events]);

  // Find active event for selected city to retrieve schema forecast metadata
  const currentCityEvent = useMemo(() => {
    return (
      events.find(
        (e) => e.location.city.toLowerCase() === selectedCity.toLowerCase()
      ) || events[0]
    );
  }, [events, selectedCity]);

  const maxVal = useMemo(() => {
    if (forecastPoints.length === 0) return 200;
    const validPm25 = forecastPoints.map((p) => p.pm25).filter((val): val is number => val != null);
    if (validPm25.length === 0) return 200;
    const max = Math.max(...validPm25);
    return Math.max(max, 75);
  }, [forecastPoints]);

  return (
    <div className="flex flex-col min-h-screen bg-[#03111F]">
      {/* Header */}
      <DashboardHeader
        title="PM2.5 Forecast"
        subtitle="6h, 24h & 72h PM2.5 forecasts with uncertainty estimates"
      />

      <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* Horizon & Basin Control Bar */}
        <div className="bg-[#092337] border border-[rgba(0,213,255,0.12)] rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-4">
            {/* City Selector */}
            <div>
              <label
                htmlFor="forecast-city"
                className="block text-[10px] font-bold uppercase tracking-wider text-[#7BA4BC] mb-1"
              >
                Surveillance Air Basin
              </label>
              <div className="relative">
                <select
                  id="forecast-city"
                  value={selectedCity}
                  onChange={(e) => setSelectedCity(e.target.value)}
                  className="bg-[#03111F] border border-[rgba(0,213,255,0.20)] rounded px-3 py-1.5 text-xs text-[#E8F4FD] font-semibold focus:outline-hidden focus:border-[#00E5FF] pr-8 cursor-pointer"
                >
                  {cities.map((city) => (
                    <option key={city} value={city}>
                      {city} Air Basin
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Current Baseline Chip */}
            {currentCityEvent?.evidence?.sensor && (
              <div className="hidden sm:block pl-4 border-l border-slate-200">
                <span className="block text-[10px] font-bold uppercase tracking-wider text-[#7BA4BC] mb-0.5">
                  Current Sensor Baseline
                </span>
                <span className="text-sm font-bold text-[#E8F4FD] tabular-telemetry">
                  {currentCityEvent.evidence.sensor.pm25} µg/m³
                </span>
                <span className="text-[11px] text-[#7BA4BC] ml-1">
                  ({currentCityEvent.evidence.sensor.station_id})
                </span>
              </div>
            )}
          </div>

          {/* Horizon Selector Toggles */}
          <div>
            <span className="block text-[10px] font-bold uppercase tracking-wider text-[#7BA4BC] mb-1 text-right sm:text-left">
              Forecast Horizon
            </span>
            <div className="inline-flex bg-[rgba(0,213,255,0.06)] p-1 rounded-lg border border-[rgba(0,213,255,0.12)] text-xs">
              {([6, 24, 72] as const).map((hours) => (
                <button
                  key={hours}
                  type="button"
                  onClick={() => setSelectedHorizon(hours)}
                  className={`px-3.5 py-1.5 rounded font-semibold transition-all cursor-pointer ${
                    selectedHorizon === hours
                      ? 'bg-[rgba(0,229,255,0.15)] border border-[rgba(0,229,255,0.35)] text-[#00E5FF] shadow-xs'
                      : 'text-[#7BA4BC] hover:text-[#E8F4FD]'
                  }`}
                >
                  +{hours} Hours
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Main Forecast Chart Card */}
        <Card>
          <CardHeader
            title={
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-[#00E5FF]" />
                <span>
                  PM2.5 Forecast: {selectedCity} (+{selectedHorizon}h)
                </span>
              </div>
            }
            subtitle="Hourly PM2.5 forecast vs. WHO (15 µg/m³) and National NAAQS (60 µg/m³)"
            action={
              currentCityEvent && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[#7BA4BC]">Current Risk:</span>
                  <RiskBadge level={currentCityEvent.risk} size="sm" />
                </div>
              )
            }
          />

          <CardContent className="p-6">
            <div className="h-80 w-full">
              {loadingForecast ? (
                <div className="h-full flex flex-col items-center justify-center text-[#7BA4BC] text-xs">
                  <div className="h-7 w-7 border-2 border-[#00E5FF] border-t-transparent rounded-full animate-spin mb-2" />
                  <span>Computing PM2.5 forecast...</span>
                </div>
              ) : apiError ? (
                <div className="h-full flex flex-col items-center justify-center text-[#FF4444] text-xs bg-[rgba(255,68,68,0.06)] rounded-xl border border-[rgba(255,68,68,0.20)]">
                  <AlertTriangle className="w-8 h-8 mb-2" />
                  <span className="font-bold text-sm">Forecast Data Unavailable</span>
                  <span className="opacity-80 mt-1 max-w-md text-center">{apiError}</span>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={forecastPoints}
                    margin={{ top: 15, right: 30, left: 0, bottom: 10 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(0,213,255,0.08)"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="time"
                      tick={{ fontSize: 11, fill: '#7BA4BC' }}
                      axisLine={{ stroke: 'rgba(0,213,255,0.15)' }}
                      tickLine={false}
                    />
                    <YAxis
                      domain={[0, Math.ceil(maxVal * 1.15)]}
                      tick={{ fontSize: 11, fill: '#7BA4BC' }}
                      axisLine={false}
                      tickLine={false}
                      unit=" µg"
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const pt = payload[0].payload as ForecastPoint;
                          return (
                            <div className="bg-[#061827] text-[#E8F4FD] text-xs p-3 rounded-lg shadow-xl border border-[rgba(0,213,255,0.20)] font-mono">
                              <div className="text-[#7BA4BC] text-[10px] uppercase">
                                Horizon +{pt.hour}h ({pt.time})
                              </div>
                              <div className="text-lg font-bold text-[#00E5FF] mt-0.5">
                                {pt.pm25} µg/m³
                              </div>
                              <div className="mt-2 pt-2 border-t border-[rgba(0,213,255,0.15)] text-[10px] space-y-1 text-[#7BA4BC]">
                                <div className="flex justify-between gap-4">
                                  <span>WHO Limit (24h):</span>
                                  <strong className="text-[#27E0C3]">15 µg/m³</strong>
                                </div>
                                <div className="flex justify-between gap-4">
                                  <span>NAAQS Standard:</span>
                                  <strong className="text-[#FF9F1C]">60 µg/m³</strong>
                                </div>
                              </div>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />

                    {/* WHO Reference Line (15 µg/m³) */}
                    <ReferenceLine
                      y={15}
                      stroke="#22c55e"
                      strokeWidth={1.5}
                      strokeDasharray="4 4"
                      label={{
                        value: 'WHO Safe Standard (15 µg/m³)',
                        position: 'insideTopLeft',
                        fill: '#15803d',
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    />

                    {/* Indian NAAQS Reference Line (60 µg/m³) */}
                    <ReferenceLine
                      y={60}
                      stroke="#f97316"
                      strokeWidth={1.5}
                      strokeDasharray="4 4"
                      label={{
                        value: 'NAAQS National Standard (60 µg/m³)',
                        position: 'insideTopLeft',
                        fill: '#c2410c',
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    />

                    {/* Continuous Forecast Curve */}
                    <Line
                      type="monotone"
                      dataKey="pm25"
                      stroke="#00E5FF"
                      strokeWidth={2.5}
                      dot={{
                        r: 4,
                        fill: '#00E5FF',
                        stroke: '#03111F',
                        strokeWidth: 2,
                      }}
                      activeDot={{ r: 7, fill: '#27E0C3' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Threshold Legend Bar */}
            <div className="mt-4 pt-3 border-t border-[rgba(0,213,255,0.08)] flex flex-wrap items-center justify-between gap-3 text-xs text-[#7BA4BC]">
              <div className="flex items-center gap-5">
                <span className="flex items-center gap-1.5 font-medium">
                  <span className="h-2.5 w-2.5 rounded-full bg-[#00E5FF]" />
                  <span>PM2.5 Forecast</span>
                </span>
                <span className="flex items-center gap-1.5 font-medium">
                  <span className="h-2.5 w-2.5 rounded-full bg-[#22c55e]" />
                  <span>WHO Safe Baseline (15 µg/m³)</span>
                </span>
                <span className="flex items-center gap-1.5 font-medium">
                  <span className="h-2.5 w-2.5 rounded-full bg-[#f97316]" />
                  <span>NAAQS Permissible Ceiling (60 µg/m³)</span>
                </span>
              </div>

              <span className="text-[11px] font-mono text-[#2E5470]">
                Resolution: Hourly Forecast
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Forecast Reliability & Spike Risk Parameters */}
        {currentCityEvent && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* 1. Spike Probability */}
            <div className="bg-[#092337] border border-[rgba(0,213,255,0.12)] rounded-xl p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-[#7BA4BC]">
                    Spike Probability
                  </span>
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded font-bold uppercase ${
                      currentCityEvent.forecast.spike_probability === 'HIGH'
                        ? 'bg-[rgba(255,68,68,0.10)] text-[#FF4444] border border-[rgba(255,68,68,0.25)]'
                        : currentCityEvent.forecast.spike_probability === 'MEDIUM'
                        ? 'bg-[rgba(255,181,46,0.10)] text-[#FFB52E] border border-[rgba(255,181,46,0.25)]'
                        : 'bg-[rgba(39,224,195,0.10)] text-[#27E0C3] border border-[rgba(39,224,195,0.25)]'
                    }`}
                  >
                    {currentCityEvent.forecast.spike_probability} SPIKE RISK
                  </span>
                </div>

                <div className="mt-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-[#FFB52E]" />
                    <span className="text-base font-bold text-[#E8F4FD]">
                      Acute Surge Expectancy
                    </span>
                  </div>
                  <p className="text-xs text-[#7BA4BC] mt-1">
                    Indicates probability of sudden PM2.5 concentration spikes exceeding baseline within 24h.
                  </p>
                </div>
              </div>

              <p className="mt-3 pt-2.5 border-t border-[rgba(0,213,255,0.08)] text-[11px] text-[#7BA4BC] flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-[#2E5470]" />
                <span>Computed from wind stagnation & source telemetry</span>
              </p>
            </div>

            {/* 2. Forecast Uncertainty (Strictly Distinct from Confidence) */}
            <div className="bg-[#092337] border border-[rgba(0,213,255,0.12)] rounded-xl p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-[#7BA4BC]">
                    Forecast Uncertainty
                  </span>
                  <span className="text-xs px-2.5 py-0.5 rounded font-bold uppercase bg-[rgba(0,213,255,0.06)] text-[#7BA4BC] border border-[rgba(0,213,255,0.15)]">
                    {currentCityEvent.forecast.forecast_uncertainty}
                  </span>
                </div>

                <div className="mt-3">
                  <div className="flex items-center gap-2">
                    <HelpCircle className="w-5 h-5 text-[#3BAED4]" />
                    <span className="text-base font-bold text-[#E8F4FD]">
                      Forecast Uncertainty
                    </span>
                  </div>
                  <p className="text-xs text-[#7BA4BC] mt-1">
                    Represents forecast variability across the selected time horizon. Distinct from detection confidence.
                  </p>
                </div>
              </div>

              <p className="mt-3 pt-2.5 border-t border-[rgba(0,213,255,0.08)] text-[11px] text-[#7BA4BC] flex items-center gap-1">
                <Shield className="w-3.5 h-3.5 text-[#2E5470]" />
                <span>Evaluated against synoptic weather ensemble</span>
              </p>
            </div>

            {/* 3. Detection Confidence (For Explicit Contrast) */}
            <div className="bg-[#092337] border border-[rgba(0,213,255,0.12)] rounded-xl p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-[#7BA4BC]">
                    Detection Confidence
                  </span>
                  <span className="text-xs px-2.5 py-0.5 rounded font-bold uppercase bg-[rgba(0,229,255,0.08)] text-[#00E5FF] border border-[rgba(0,229,255,0.20)]">
                    {Math.round(currentCityEvent.detection.confidence * 100)}%
                  </span>
                </div>

                <div className="mt-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-[#27E0C3]" />
                    <span className="text-base font-bold text-[#E8F4FD]">
                      Detection Confidence
                    </span>
                  </div>
                  <p className="text-xs text-[#7BA4BC] mt-1">
                    Reflects current evidence corroboration (sensor + satellite + citizen), completely independent of forecast uncertainty.
                  </p>
                </div>
              </div>

              <p className="mt-3 pt-2.5 border-t border-[rgba(0,213,255,0.08)] text-[11px] text-[#7BA4BC] font-mono">
                Method: {currentCityEvent.detection.method || 'weighted_fusion_v1'}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
