'use client';

import React from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import {
  ShieldCheck,
  Activity,
  BrainCircuit,
  Orbit,
  Database,
  ArrowLeft,
  Wind,
  Cpu,
  Compass,
  FileCheck2,
  Send,
  RefreshCw,
} from 'lucide-react';
import { SceneFallback } from '@/components/3d/SceneFallback';

// Isolated Client-Only 3D Component with SSR disabled
const MethodologyPipeline3D = dynamic(
  () => import('@/components/3d/MethodologyPipeline3D'),
  {
    ssr: false,
    loading: () => (
      <SceneFallback
        title="Federated Intelligence Assimilation Architecture"
        description="Initializing 3D assimilation pipeline..."
        reason="loading"
      />
    ),
  }
);

export default function MethodologyPage() {
  const lifecycleStages = [
    {
      num: '01',
      title: 'OBSERVE',
      tagline: 'Multi-Modal Ingestion Grid',
      desc: 'Continuous real-time data harvesting across certified CAAQMS/CPCB ground sensors, NASA FIRMS thermal anomaly hotspots, and Copernicus Sentinel-5P TROPOMI tropospheric columns.',
      icon: <Database className="w-5 h-5 text-[#00E5FF]" />,
    },
    {
      num: '02',
      title: 'FUSE & ASSIMILATE',
      tagline: 'Multi-Source Evidence Alignment',
      desc: 'Harmonization of spatial-temporal coordinates, eliminating redundant crowdsourced sightings, and cross-validating localized sensor spikes against satellite aerosol optical depth.',
      icon: <Orbit className="w-5 h-5 text-[#27E0C3]" />,
    },
    {
      num: '03',
      title: 'COUPLED ATMOSPHERE',
      tagline: 'Synoptic & Boundary Layer Dynamics',
      desc: 'Integration with Open-Meteo synoptic fields to calculate ventilation factors, wind advection vectors, and nocturnal thermal inversion cap altitudes.',
      icon: <Wind className="w-5 h-5 text-[#00E5FF]" />,
    },
    {
      num: '04',
      title: 'AI/ML INTELLIGENCE',
      tagline: 'Vision Validation & Trajectory Modeling',
      desc: 'Fine-tuned Gemini multimodal vision models classify citizen hazard imagery while trained XGBoost regression models generate 6h, 24h, and 72h predictive concentration horizons.',
      icon: <BrainCircuit className="w-5 h-5 text-[#FFB52E]" />,
    },
    {
      num: '05',
      title: 'ENVIRONMENTAL INTELLIGENCE',
      tagline: 'Anomaly Corroboration & Scoring',
      desc: 'Synthesizing evidence into structured event dossiers with deterministic confidence scores, identifying source hypotheses (crop stubble, industrial stack, biomass).',
      icon: <Cpu className="w-5 h-5 text-[#27E0C3]" />,
    },
    {
      num: '06',
      title: 'EVIDENCE VERIFICATION',
      tagline: 'Contradiction & Sensor Drift Checks',
      desc: 'Rigorous cross-validation matrices identify false positives by checking for sensor baseline drift, calibration anomalies, or contradicting satellite clear-sky telemetry.',
      icon: <FileCheck2 className="w-5 h-5 text-[#00E5FF]" />,
    },
    {
      num: '07',
      title: 'ACTION',
      tagline: 'Civic Alerts & Authority Dispatch',
      desc: 'Actionable intelligence dossiers are routed to state pollution boards (DPCC/CPCB) and field investigation teams with precise coordinates and predictive spread cones.',
      icon: <Send className="w-5 h-5 text-[#2ECC71]" />,
    },
    {
      num: '08',
      title: 'VALIDATE & IMPROVE',
      tagline: 'Human-in-the-Loop Feedback Engine',
      desc: 'Ground truth field investigation outcomes (confirmed, false alarm, resolved) are fed back into model weights to continuously calibrate regional detection thresholds.',
      icon: <RefreshCw className="w-5 h-5 text-[#00E5FF]" />,
    },
  ];

  return (
    <div className="min-h-screen bg-[#03111F] text-[#E8F4FD] font-sans selection:bg-[#00E5FF] selection:text-[#03111F]">
      {/* Navbar */}
      <nav className="border-b border-[rgba(0,213,255,0.15)] bg-[rgba(6,24,39,0.85)] backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 bg-gradient-to-br from-[#00E5FF] to-[#0077EE] rounded flex items-center justify-center shadow-[0_0_10px_rgba(0,229,255,0.3)]">
              <Activity className="text-[#03111F] w-5 h-5" />
            </div>
            <span className="text-xl font-bold tracking-tight">
              Vayu<span className="text-[#00E5FF]">Net</span>
            </span>
          </div>
          <Link
            href="/"
            className="text-sm font-semibold text-[#7BA4BC] hover:text-[#00E5FF] transition-colors flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Return to Home
          </Link>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-16">
        {/* Header */}
        <div className="text-center mb-12">
          <span className="text-[11px] font-mono uppercase px-3 py-1 rounded bg-[rgba(0,213,255,0.08)] text-[#00E5FF] border border-[rgba(0,213,255,0.20)] inline-block mb-4">
            Scientific Architecture Specification
          </span>
          <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight mb-4">
            Coupled Environmental{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00E5FF] to-[#27E0C3]">
              Intelligence Architecture
            </span>
          </h1>
          <p className="text-base text-[#7BA4BC] max-w-2xl mx-auto leading-relaxed">
            How VayuNet assimilates heterogeneous observation streams into deterministic, corroborated environmental response dossiers.
          </p>
        </div>

        {/* 3D Visual Conceptual Pipeline */}
        <div className="mb-16">
          <MethodologyPipeline3D />
          <p className="text-center text-[11px] text-[#2E5470] mt-2 font-mono">
            * 3D schematic illustrates multi-tier data convergence into the AI multimodal core.
          </p>
        </div>

        {/* The 8-Stage Environmental Intelligence Lifecycle (Authoritative 2D Representation) */}
        <div className="mb-16">
          <div className="flex items-center justify-between mb-8 pb-3 border-b border-[rgba(0,213,255,0.12)]">
            <div>
              <h2 className="text-xl font-bold text-[#E8F4FD]">
                The 8-Stage Environmental Intelligence Lifecycle
              </h2>
              <p className="text-xs text-[#7BA4BC]">
                End-to-end auditability from initial physical observation to field validation.
              </p>
            </div>
            <span className="text-[10px] font-mono text-[#00E5FF] uppercase px-2 py-1 rounded bg-[rgba(0,213,255,0.06)] border border-[rgba(0,213,255,0.12)]">
              Operational Standard
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {lifecycleStages.map((stage) => (
              <div
                key={stage.num}
                className="bg-[rgba(6,24,39,0.80)] border border-[rgba(0,213,255,0.14)] p-5 rounded-xl flex flex-col justify-between shadow-lg shadow-black/20 hover:border-[rgba(0,213,255,0.30)] transition-colors"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-mono font-bold text-[#00E5FF]">
                      {stage.num}
                    </span>
                    <div className="p-2 rounded-md bg-[rgba(0,213,255,0.06)] border border-[rgba(0,213,255,0.12)]">
                      {stage.icon}
                    </div>
                  </div>
                  <h3 className="text-sm font-bold text-[#E8F4FD] mb-1">
                    {stage.title}
                  </h3>
                  <p className="text-[11px] font-mono text-[#27E0C3] mb-2">
                    {stage.tagline}
                  </p>
                  <p className="text-xs text-[#7BA4BC] leading-relaxed">
                    {stage.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Zero Fabrication Commitment Callout */}
        <div className="bg-[rgba(6,24,39,0.85)] border border-[rgba(0,213,255,0.18)] p-6 md:p-8 rounded-xl shadow-xl">
          <div className="flex items-start gap-4">
            <div className="p-2.5 rounded-lg bg-[rgba(0,213,255,0.08)] border border-[rgba(0,213,255,0.20)] text-[#00E5FF] shrink-0">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-[#E8F4FD] mb-1">
                Data Provenance & Scientific Truth Assurance
              </h3>
              <p className="text-xs text-[#7BA4BC] leading-relaxed mb-3">
                VayuNet strictly adheres to data integrity principles: missing environmental observations are never coerced to zero or populated with fabricated synthetic values. If telemetry is not reported by ground sensors or orbital instruments, the platform renders explicit <span className="font-mono text-[#FFB52E]">UNAVAILABLE</span> states.
              </p>
              <div className="flex flex-wrap gap-4 text-xs font-mono text-[#00E5FF]">
                <span>• CAAQMS / CPCB Certified Baselines</span>
                <span>• Copernicus Sentinel-5P Column Corroboration</span>
                <span>• Deterministic Uncertainty Intervals</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <footer className="border-t border-[rgba(0,213,255,0.1)] py-8 text-center text-xs text-[#2E5470]">
        VayuNet Environmental Intelligence Platform © {new Date().getFullYear()}
      </footer>
    </div>
  );
}
