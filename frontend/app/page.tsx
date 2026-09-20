import React from 'react';
import Link from 'next/link';
import {
  Activity,
  Shield,
  Radio,
  ArrowRight,
  Sparkles,
  Layers,
  Wind,
  Camera,
  TrendingUp,
  CheckCircle2,
  ShieldCheck,
  Send,
  UserCheck,
  RefreshCw,
  ShieldAlert,
  ChevronRight,
} from 'lucide-react';
import RiskBadge from '@/components/ui/RiskBadge';

const WORKFLOW_STEPS = [
  {
    step: '01',
    title: 'DETECT',
    desc: 'Citizen + sensor + satellite signals',
    icon: Radio,
  },
  {
    step: '02',
    title: 'VERIFY',
    desc: 'Corroborate evidence & reduce duplicates',
    icon: ShieldCheck,
  },
  {
    step: '03',
    title: 'FORECAST',
    desc: '6h / 24h / 72h prediction',
    icon: TrendingUp,
  },
  {
    step: '04',
    title: 'EXPLAIN',
    desc: 'AI explanation with cited evidence',
    icon: Sparkles,
  },
  {
    step: '05',
    title: 'ROUTE',
    desc: 'Send to the right authority',
    icon: Send,
  },
  {
    step: '06',
    title: 'HUMAN RESPONSE',
    desc: 'Acknowledge / confirm / investigate / dismiss',
    icon: UserCheck,
  },
  {
    step: '07',
    title: 'LEARN',
    desc: 'Outcome feeds future improvement',
    icon: RefreshCw,
  },
];

export default function HomePage() {
  return (
    <div className="w-full min-h-screen bg-[#f8fafc] text-[#0f172a] flex flex-col justify-between">
      {/* Global Command Header */}
      <header className="bg-[#0a2540] text-white border-b border-[#0f2a3f] px-4 sm:px-6 py-3.5 sticky top-0 z-30 shadow-md">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-3 sm:gap-4">
          <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
            <div className="h-9 w-9 sm:h-10 sm:w-10 rounded bg-sky-500/20 border border-sky-400/30 flex items-center justify-center text-sky-400 shrink-0 shadow-xs">
              <Activity className="w-4 h-4 sm:w-5 sm:h-5 text-sky-300" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-lg sm:text-xl font-bold tracking-tight text-white">
                  VayuNet
                </span>
                <span className="text-[10px] uppercase font-mono tracking-wider bg-sky-950 text-sky-300 border border-sky-800 px-2 py-0.5 rounded shrink-0">
                  PROTOTYPE
                </span>
              </div>
              <span className="text-xs text-slate-300 hidden sm:block font-normal truncate">
                Federated Environmental Intelligence Platform
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            <span className="hidden lg:inline-flex items-center gap-1.5 text-xs text-slate-300 bg-white/5 border border-white/10 px-3 py-1.5 rounded">
              <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
              <span>3-City Federated Pilot</span>
            </span>

            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 sm:px-3.5 sm:py-1.5 rounded bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold transition-colors shadow-xs"
            >
              <span>Authority View</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="bg-gradient-to-b from-[#0a2540] via-[#0d2e4d] to-[#f8fafc] text-white pt-10 sm:pt-14 pb-16 sm:pb-20 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto text-center space-y-4 sm:space-y-5">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/20 text-xs font-medium text-sky-200 max-w-full">
            <Sparkles className="w-3.5 h-3.5 text-sky-400 shrink-0" />
            <span className="truncate sm:text-clip">Beyond Simple AQI Numbers • The Pollution Event Paradigm</span>
          </div>

          <h1 className="text-2xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-white leading-tight break-words">
            Find hidden pollution events. Alert the right authority.
          </h1>

          <p className="max-w-3xl mx-auto text-xs sm:text-sm md:text-base text-slate-300 leading-relaxed">
            VayuNet fuses citizen reports, CPCB sensors, Sentinel-5P satellite data and weather to detect local pollution events — then explains the evidence and routes a verified alert to the responsible authority.
          </p>

          <div className="pt-2 sm:pt-4 flex flex-wrap items-center justify-center gap-2 sm:gap-3">
            <RiskBadge level="LOW" size="sm" />
            <RiskBadge level="MODERATE" size="sm" />
            <RiskBadge level="HIGH" size="sm" />
            <RiskBadge level="CRITICAL" size="sm" />
          </div>
        </div>
      </section>

      {/* Main Content Area */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 -mt-8 sm:-mt-10 pb-10 sm:pb-12 w-full space-y-8 sm:space-y-10">
        {/* Dual Portal Gateway Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
          {/* Portal 1: Authority Intelligence Dashboard */}
          <div className="bg-white border-2 border-slate-200 hover:border-[#0a2540] rounded-xl p-5 sm:p-8 shadow-lg transition-all flex flex-col justify-between group">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="h-12 w-12 rounded-lg bg-[#0a2540] text-white flex items-center justify-center shadow-md">
                  <Shield className="w-6 h-6 text-sky-300" />
                </div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 bg-slate-100 px-2.5 py-1 rounded border border-slate-200">
                  Authority Portal
                </span>
              </div>

              <div>
                <h2 className="text-lg sm:text-xl font-bold text-[#0f172a] group-hover:text-[#0a2540] transition-colors">
                  Authority Intelligence Dashboard
                </h2>
                <p className="text-xs text-[#64748b] mt-1.5 leading-relaxed">
                  Engineered for Municipal Corporations, State Pollution Control Boards, and Environmental Officers. Monitor active incident feeds, inspect multi-sensor evidence breakdowns, evaluate 6h / 24h / 72h PM2.5 forecasts with uncertainty bands, and review evidence, acknowledge alerts, and confirm or dismiss events.
                </p>
              </div>

              <div className="space-y-2 pt-2 border-t border-slate-100 text-xs text-slate-700">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Geospatial Leaflet Hotspot Surveillance</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Gemini AI Multimodal Evidence Explanations</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>PM2.5 Forecasts vs NAAQS / WHO Thresholds</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Official Alert Routing & Investigation Dispatch</span>
                </div>
              </div>
            </div>

            <div className="pt-6 space-y-3">
              <Link
                href="/dashboard"
                className="w-full py-3 px-4 rounded-lg bg-[#0a2540] hover:bg-[#0f2a3f] text-white text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-colors shadow-sm"
              >
                <span>Launch Authority Dashboard</span>
                <ArrowRight className="w-4 h-4 text-sky-300" />
              </Link>

              <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-4 text-xs text-[#64748b] pt-1">
                <Link href="/dashboard/map" className="hover:text-[#0a2540] underline font-medium">
                  Hotspot Map
                </Link>
                <span>•</span>
                <Link href="/dashboard/forecast" className="hover:text-[#0a2540] underline font-medium">
                  Forecasts
                </Link>
                <span>•</span>
                <Link href="/dashboard/alerts" className="hover:text-[#0a2540] underline font-medium">
                  Alert Centre
                </Link>
              </div>
            </div>
          </div>

          {/* Portal 2: Citizen Pollution Reporter */}
          <div className="bg-white border-2 border-slate-200 hover:border-sky-600 rounded-xl p-5 sm:p-8 shadow-lg transition-all flex flex-col justify-between group">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="h-12 w-12 rounded-lg bg-sky-600 text-white flex items-center justify-center shadow-md">
                  <Camera className="w-6 h-6 text-white" />
                </div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-sky-800 bg-sky-50 px-2.5 py-1 rounded border border-sky-200">
                  Public Portal
                </span>
              </div>

              <div>
                <h2 className="text-lg sm:text-xl font-bold text-[#0f172a] group-hover:text-sky-700 transition-colors">
                  Citizen Pollution Reporter
                </h2>
                <p className="text-xs text-[#64748b] mt-1.5 leading-relaxed">
                  Mobile-first public interface for reporting local pollution observations. Capture smoke or illegal burning photos, dictate narratives using browser voice speech-to-text in English or Hindi, and pin GPS coordinates on an interactive mini-map.
                </p>
              </div>

              <div className="space-y-2 pt-2 border-t border-slate-100 text-xs text-slate-700">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Mobile Camera Capture & Gallery Upload</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Web Speech Voice Dictation (English & हिंदी)</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Automatic GPS Geolocation with Draggable Pin</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Animated 5-Stage Ingest & AI Fusion Pipeline</span>
                </div>
              </div>
            </div>

            <div className="pt-6 space-y-3">
              <Link
                href="/report"
                className="w-full py-3 px-4 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-colors shadow-sm"
              >
                <span>Open Citizen Reporter</span>
                <ArrowRight className="w-4 h-4 text-sky-200" />
              </Link>

              <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-4 text-xs text-[#64748b] pt-1">
                <span>Available in English & हिंदी</span>
                <span>•</span>
                <span>Camera & Mic Ready</span>
              </div>
            </div>
          </div>
        </div>

        {/* 7-Step Operational Lifecycle Workflow */}
        <section className="bg-white border border-slate-200 rounded-xl p-5 sm:p-7 shadow-xs">
          <div className="text-center max-w-2xl mx-auto mb-6">
            <span className="text-[11px] font-bold uppercase tracking-wider text-sky-700 font-mono">
              Operational Workflow
            </span>
            <h3 className="text-lg sm:text-xl font-bold text-[#0f172a] mt-1">
              7-Step End-to-End Decision Pipeline
            </h3>
            <p className="text-xs text-[#64748b] mt-1">
              How multimodal signals are verified, forecasted, explained, and converted into accountable municipal action.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-2.5">
            {WORKFLOW_STEPS.map((item, idx) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.title}
                  className="relative bg-slate-50 border border-slate-200/90 rounded-lg p-3 sm:p-3.5 flex flex-col justify-between hover:border-sky-300 transition-colors h-full min-h-[120px] sm:min-h-[130px]"
                >
                  <div>
                    <div className="flex items-center justify-between text-slate-400 mb-2.5">
                      <span className="text-[10px] font-mono font-bold text-sky-700 bg-sky-100/80 px-1.5 py-0.5 rounded">
                        {item.step}
                      </span>
                      <Icon className="w-4 h-4 text-slate-600" />
                    </div>
                    <div className="min-h-[28px] sm:min-h-[32px] flex items-start">
                      <h4 className="text-xs font-bold text-slate-900 tracking-wider uppercase leading-tight">
                        {item.title}
                      </h4>
                    </div>
                    <p className="text-[11px] text-slate-600 mt-1.5 leading-snug break-words">
                      {item.desc}
                    </p>
                  </div>

                  {idx < WORKFLOW_STEPS.length - 1 && (
                    <div className="hidden lg:block absolute -right-2 top-1/2 -translate-y-1/2 z-10 pointer-events-none">
                      <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Civic Guardrail Trust Statement */}
          <div className="mt-4 p-3 rounded-lg bg-sky-50 border border-sky-200 flex items-start gap-2.5 text-xs text-sky-900">
            <ShieldAlert className="w-4 h-4 text-sky-700 shrink-0 mt-0.5" />
            <p className="leading-relaxed break-words">
              <strong className="font-semibold text-sky-950">Civic Guardrail:</strong> Citizen reports alone can never trigger an alert — sensor or satellite corroboration is mandatory.
            </p>
          </div>
        </section>

        {/* Four Independent Evidence Sources */}
        <section className="bg-white border border-[#e2e8f0] rounded-xl p-5 sm:p-8 shadow-xs">
          <div className="text-center max-w-2xl mx-auto mb-6 sm:mb-8">
            <span className="text-[11px] font-bold uppercase tracking-wider text-sky-700 font-mono">
              Evidence Synthesis
            </span>
            <h3 className="text-lg sm:text-xl font-bold text-[#0f172a] mt-1">
              Four Independent Evidence Sources
            </h3>
            <p className="text-xs text-[#64748b] mt-1">
              Ground observations, citizen reports, satellite signals and weather data are combined to strengthen event confidence.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80">
              <div className="flex items-center gap-2 mb-2">
                <Camera className="w-4 h-4 text-sky-600" />
                <h4 className="text-xs font-bold text-[#0f172a] uppercase">
                  Citizen Observations
                </h4>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Photos, voice and text — interpreted by Gemini into event type, severity and confidence.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-4 h-4 text-[#0a2540]" />
                <h4 className="text-xs font-bold text-[#0f172a] uppercase">
                  CPCB Sensor Network
                </h4>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Hourly PM2.5, PM10 and NO₂ observations from public monitoring stations.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80">
              <div className="flex items-center gap-2 mb-2">
                <Layers className="w-4 h-4 text-sky-700" />
                <h4 className="text-xs font-bold text-[#0f172a] uppercase">
                  Sentinel-5P Satellite
                </h4>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                NO₂ and aerosol indicators provide independent corroboration from Sentinel-5P satellite observations.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80">
              <div className="flex items-center gap-2 mb-2">
                <Wind className="w-4 h-4 text-cyan-700" />
                <h4 className="text-xs font-bold text-[#0f172a] uppercase">
                  Weather (Open-Meteo)
                </h4>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Wind speed, humidity and other weather conditions help assess whether pollution may linger or disperse.
              </p>
            </div>
          </div>
        </section>

        {/* Powered-By Bar */}
        <div className="p-3 rounded-lg bg-white border border-slate-200 text-center shadow-2xs">
          <p className="text-[11px] sm:text-xs font-medium text-slate-600 break-words">
            Powered by <span className="text-slate-900 font-semibold">Gemini API</span> · <span className="text-slate-900 font-semibold">Google Earth Engine</span> · <span className="text-slate-900 font-semibold">Flower</span> · <span className="text-slate-900 font-semibold">Firebase</span>
          </p>
        </div>
      </main>

      {/* Professional Prototype Footer */}
      <footer className="w-full bg-white border-t border-slate-200 px-4 sm:px-6 py-6 text-xs text-slate-600">
        <div className="max-w-6xl mx-auto flex flex-col gap-2.5 text-center sm:text-left">
          <div className="flex flex-wrap items-center justify-center sm:justify-between gap-2">
            <p className="font-semibold text-slate-800">
              VayuNet <span className="font-normal text-slate-400">·</span> Prototype — some data may be simulated
            </p>
            <p className="text-[11px] text-slate-500">
              SIH 2024 Local Demo Edition
            </p>
          </div>
          <p className="text-[11px] text-slate-500 leading-relaxed break-words">
            Data: CPCB / data.gov.in <span className="text-slate-300">·</span> Copernicus Sentinel-5P <span className="text-slate-300">·</span> Open-Meteo <span className="text-slate-300">·</span> © OpenStreetMap contributors
          </p>
          <p className="text-[11px] text-slate-400 leading-relaxed break-words">
            Built with Gemini API <span className="text-slate-300">·</span> Google Earth Engine <span className="text-slate-300">·</span> Flower FL <span className="text-slate-300">·</span> Firebase
          </p>
        </div>
      </footer>
    </div>
  );
}
