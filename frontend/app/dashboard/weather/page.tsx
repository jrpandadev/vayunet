'use client';

import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { getEvents, getApiStatus } from '@/lib/api';
import { PollutionEvent } from '@/lib/types';
import DashboardHeader from '@/components/layout/DashboardHeader';
import Card, { CardHeader, CardContent } from '@/components/ui/Card';
import StatCard from '@/components/ui/StatCard';
import RiskBadge from '@/components/ui/RiskBadge';
import { SceneFallback } from '@/components/3d/SceneFallback';
import {
  Wind,
  Droplets,
  ThermometerSun,
  Layers,
  ArrowRight,
  MapPin,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  Compass,
  Activity,
  Orbit,
  Clock,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';

// Isolated Client-Only 3D Component with SSR disabled
const AtmosphericColumn = dynamic(
  () => import('@/components/3d/AtmosphericColumn'),
  {
    ssr: false,
    loading: () => (
      <SceneFallback
        title="Vertical Atmospheric Stratification"
        description="Initializing atmospheric WebGL column..."
        reason="loading"
      />
    ),
  }
);

export default function WeatherDashboardPage() {
  const [events, setEvents] = useState<PollutionEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<PollutionEvent | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [apiStatus, setApiStatus] = useState(() => getApiStatus());

  useEffect(() => {
    let mounted = true;
    async function loadData() {
      setLoading(true);
      try {
        const data = await getEvents();
        if (mounted) {
          setEvents(data);
          if (data.length > 0) {
            setSelectedEvent(data[0]);
          }
        }
      } catch (err) {
        console.error('Failed to load events on weather page:', err);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadData();
    return () => {
      mounted = false;
    };
  }, []);

  const weather = selectedEvent?.evidence.weather;
  const sensor = selectedEvent?.evidence.sensor;
  const satellite = selectedEvent?.evidence.satellite;
  const forecast = selectedEvent?.forecast;

  const windSpeed = weather?.wind_speed_kmh;
  const humidity = weather?.humidity_percent;
  const hasInversion = selectedEvent?.explanation?.toLowerCase().includes('inversion') ?? false;

  // Dispersion classification based on real wind speed thresholds
  let ventilationStatus = 'UNAVAILABLE';
  let ventilationRisk: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL' = 'MODERATE';
  if (windSpeed != null) {
    if (windSpeed < 5) {
      ventilationStatus = 'Stagnant / Poor';
      ventilationRisk = 'CRITICAL';
    } else if (windSpeed < 12) {
      ventilationStatus = 'Moderate Mixing';
      ventilationRisk = 'MODERATE';
    } else {
      ventilationStatus = 'Active Dispersion';
      ventilationRisk = 'LOW';
    }
  }

  return (
    <div className="flex flex-col min-h-screen bg-[#03111F] text-[#E8F4FD]">
      <DashboardHeader
        title="Weather × Atmospheric Intelligence"
        subtitle="Synoptic meteorology, planetary boundary layer dynamics, and vertical dispersion coupling"
      />

      <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* City Selector & Telemetry State Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 p-3.5 rounded-lg bg-[rgba(6,24,39,0.85)] border border-[rgba(0,213,255,0.14)]">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-[#00E5FF]" />
            <span className="text-xs font-semibold uppercase tracking-wider text-[#7BA4BC]">
              Target Airshed:
            </span>
            <div className="flex gap-1.5">
              {events.map((e) => (
                <button
                  key={e.event_id}
                  onClick={() => setSelectedEvent(e)}
                  className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                    selectedEvent?.event_id === e.event_id
                      ? 'bg-[#00E5FF] text-[#03111F] font-bold shadow-[0_0_10px_rgba(0,229,255,0.3)]'
                      : 'bg-[rgba(255,255,255,0.04)] text-[#7BA4BC] hover:text-[#E8F4FD]'
                  }`}
                >
                  {e.location.city}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono">
            <span className="text-[#7BA4BC]">Data Feed:</span>
            <span
              className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                apiStatus.isConnected
                  ? 'bg-[rgba(39,224,195,0.10)] text-[#27E0C3] border border-[rgba(39,224,195,0.30)]'
                  : 'bg-[rgba(255,181,46,0.10)] text-[#FFB52E] border border-[rgba(255,181,46,0.30)]'
              }`}
            >
              {apiStatus.isConnected ? 'LIVE OPEN-METEO' : 'SIMULATION MODE'}
            </span>
          </div>
        </div>

        {/* Top Quantitative Telemetry Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Surface Wind Vector"
            value={windSpeed != null ? String(windSpeed) : 'UNAVAILABLE'}
            unit={windSpeed != null ? 'km/h' : undefined}
            subtitle={
              windSpeed != null
                ? windSpeed < 5
                  ? 'High stagnation risk'
                  : 'Active surface advection'
                : 'Sensor telemetry unavailable'
            }
            icon={<Wind className="w-4 h-4" />}
          />

          <StatCard
            title="Relative Humidity"
            value={humidity != null ? String(humidity) : 'UNAVAILABLE'}
            unit={humidity != null ? '%' : undefined}
            subtitle={
              humidity != null && humidity > 70
                ? 'Aerosol hygroscopic growth likely'
                : 'Dry ambient boundary layer'
            }
            icon={<Droplets className="w-4 h-4" />}
          />

          <StatCard
            title="Ventilation Factor"
            value={ventilationStatus}
            subtitle="Atmospheric dilution capacity"
            riskAccent={ventilationRisk}
            icon={<Layers className="w-4 h-4" />}
          />

          <StatCard
            title="Boundary Layer Cap"
            value={hasInversion ? 'Thermal Inversion' : 'Neutral Layer'}
            subtitle={hasInversion ? 'Mixing depth restricted (<900m)' : 'Standard diurnal expansion'}
            riskAccent={hasInversion ? 'HIGH' : 'LOW'}
            icon={<ThermometerSun className="w-4 h-4" />}
          />
        </div>

        {/* Core Operational Section: 3D Atmospheric Column + 2D Dispersion Couplings */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left: 3D Atmospheric Column (Explaining the vertical structure) */}
          <div className="lg:col-span-7 flex flex-col">
            <AtmosphericColumn
              windSpeedKmh={windSpeed}
              humidityPercent={humidity}
              inversionCeilingMeters={hasInversion ? 780 : 1250}
            />

            {/* Scientific Explanation Footer */}
            <div className="mt-3 p-3.5 rounded-lg bg-[rgba(6,24,39,0.70)] border border-[rgba(0,213,255,0.10)] text-xs text-[#7BA4BC] leading-relaxed">
              <span className="text-[#00E5FF] font-semibold block mb-1 flex items-center gap-1.5">
                <Compass className="w-3.5 h-3.5" />
                Physical Dispersion Mechanics:
              </span>
              The vertical column illustrates how synoptic wind velocity governs horizontal transport, while nighttime radiational cooling forms a thermal boundary layer cap. Under stagnant wind conditions (&lt;5 km/h), particulate matter remains compressed within the surface breathing zone.
            </div>
          </div>

          {/* Right: 2D Environmental Coupling Breakdown */}
          <div className="lg:col-span-5 flex flex-col gap-4">
            <Card className="h-full">
              <CardHeader
                title="Coupled Environmental Dynamics"
                subtitle="Meteorology-to-Pollutant Relationships"
              />
              <CardContent className="space-y-3.5">
                {/* Coupling Item 1: Wind */}
                <div className="p-3 rounded bg-[rgba(255,255,255,0.02)] border border-[rgba(0,213,255,0.08)]">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-[#E8F4FD] flex items-center gap-1.5">
                      <Wind className="w-3.5 h-3.5 text-[#00E5FF]" />
                      Advective Dilution
                    </span>
                    <span className="text-[11px] font-mono text-[#00E5FF]">
                      {windSpeed != null ? `${windSpeed} km/h` : 'UNAVAILABLE'}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#7BA4BC] leading-relaxed">
                    {windSpeed != null && windSpeed < 6
                      ? 'Critically low wind velocity traps locally emitted industrial & vehicular pollutants.'
                      : 'Wind velocity is sufficient to promote downwind dispersion away from urban core.'}
                  </p>
                </div>

                {/* Coupling Item 2: Temperature & Inversion */}
                <div className="p-3 rounded bg-[rgba(255,255,255,0.02)] border border-[rgba(0,213,255,0.08)]">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-[#E8F4FD] flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-[#FFB52E]" />
                      Thermal Stability & Inversion
                    </span>
                    <span className="text-[11px] font-mono text-[#FFB52E]">
                      {hasInversion ? 'INVERSION DETECTED' : 'UNRESTRICTED'}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#7BA4BC] leading-relaxed">
                    {selectedEvent?.explanation ||
                      'Inversion layer proxy derived from surface vs. 850hPa atmospheric temperature gradient.'}
                  </p>
                </div>

                {/* Coupling Item 3: Satellite Column Integration */}
                <div className="p-3 rounded bg-[rgba(255,255,255,0.02)] border border-[rgba(0,213,255,0.08)]">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-[#E8F4FD] flex items-center gap-1.5">
                      <Orbit className="w-3.5 h-3.5 text-[#27E0C3]" />
                      Sentinel-5P Tropospheric NO2
                    </span>
                    <span className="text-[11px] font-mono text-[#27E0C3]">
                      {satellite?.no2_index != null ? `${satellite.no2_index} μmol/m²` : 'TELEMETRY UNAVAILABLE'}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#7BA4BC] leading-relaxed">
                    Orbital column density corroborates ground sensor spikes against regional combustion plumes.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Ground Truth Sensor Verification Row */}
        <div className="p-4 rounded-xl bg-[rgba(6,24,39,0.80)] border border-[rgba(0,213,255,0.14)] shadow-lg shadow-black/20">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-[rgba(0,213,255,0.10)]">
            <span className="text-xs font-bold uppercase tracking-wider text-[#E8F4FD] flex items-center gap-2">
              <Activity className="w-4 h-4 text-[#00E5FF]" />
              Ground Truth & Predictive Correlation
            </span>
            <span className="text-[11px] text-[#7BA4BC]">
              Station: <strong className="text-[#E8F4FD] font-mono">{sensor?.station_id || 'UNAVAILABLE'}</strong>
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div className="p-3 rounded bg-[rgba(255,255,255,0.02)] border border-[rgba(0,213,255,0.08)]">
              <span className="text-[#7BA4BC] block mb-1 text-[11px]">Surface PM2.5 Measured</span>
              <span className="text-xl font-bold font-mono text-[#E8F4FD]">
                {sensor?.pm25 != null ? `${sensor.pm25} µg/m³` : 'UNAVAILABLE'}
              </span>
            </div>

            <div className="p-3 rounded bg-[rgba(255,255,255,0.02)] border border-[rgba(0,213,255,0.08)]">
              <span className="text-[#7BA4BC] block mb-1 text-[11px]">24-Hour Predictive Trajectory</span>
              <span className="text-xl font-bold font-mono text-[#00E5FF]">
                {forecast?.pm25_24h != null ? `${forecast.pm25_24h} µg/m³` : 'NOT MODELED'}
              </span>
            </div>

            <div className="p-3 rounded bg-[rgba(255,255,255,0.02)] border border-[rgba(0,213,255,0.08)]">
              <span className="text-[#7BA4BC] block mb-1 text-[11px]">Spike Risk Assessment</span>
              <span className="text-xl font-bold font-mono text-[#FFB52E]">
                {forecast?.spike_probability || 'UNAVAILABLE'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
