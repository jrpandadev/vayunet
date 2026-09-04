"use client";

import Link from "next/link";
import { useState } from "react";

export default function AuthorityDashboardPage() {
  const [selectedCity, setSelectedCity] = useState("Delhi");

  const sampleEvent = {
    event_id: "EVT-2026-0904-001",
    location: { city: "Delhi", area: "Anand Vihar" },
    risk: "CRITICAL",
    confidence: 0.83,
    method: "weighted_fusion_v1",
    source_hypothesis: { category: "Biomass / Waste Burning", confidence: 0.71 },
    evidence: {
      sensor: { pm25: 180, pm10: 240, anomaly: 0.8 },
      satellite: { no2: 18.2, aerosol: 1.3 },
      weather: { wind_kmh: 2.0, humidity: 80 },
    },
    authority_class: "State Pollution Control Board",
    status: "acknowledged",
    explanation:
      "Risk is CRITICAL because PM2.5 has risen significantly above baseline, Sentinel-5P confirms elevated NO2, and stagnant wind speed (2 km/h) prevents dispersion.",
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between border-b border-slate-900 pb-4">
          <div>
            <Link href="/" className="text-xs text-cyan-400 hover:underline inline-flex items-center gap-1 mb-1">
              &larr; Back to VayuNet
            </Link>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <span>Authority Action & Hotspot Console</span>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-mono">
                {selectedCity}
              </span>
            </h1>
          </div>

          <div className="flex gap-2">
            {["Delhi", "Mumbai", "Bhubaneswar"].map((city) => (
              <button
                key={city}
                onClick={() => setSelectedCity(city)}
                className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition-colors ${
                  selectedCity === city
                    ? "bg-cyan-500 text-slate-950 border-cyan-400"
                    : "bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700"
                }`}
              >
                {city}
              </button>
            ))}
          </div>
        </div>

        {/* Active Critical Incident Banner */}
        <div className="bg-slate-900 border border-rose-500/30 rounded-2xl p-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 px-4 py-1.5 bg-rose-500/20 border-b border-l border-rose-500/30 text-rose-400 font-bold text-xs uppercase tracking-wider rounded-bl-xl">
            {sampleEvent.risk} RISK EVENT
          </div>

          <div className="space-y-4">
            <div>
              <div className="text-xs text-slate-500 font-mono">{sampleEvent.event_id}</div>
              <h2 className="text-xl font-bold text-white mt-1">
                Hyper-Local Incident: {sampleEvent.location.area}, {sampleEvent.location.city}
              </h2>
            </div>

            <p className="text-sm text-slate-300 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80 leading-relaxed">
              <span className="text-xs font-semibold text-cyan-400 block uppercase tracking-wider mb-1">
                Gemini Synthesized Incident Explanation
              </span>
              {sampleEvent.explanation}
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                <span className="text-xs text-slate-500 block">Fused Confidence</span>
                <span className="text-lg font-bold text-emerald-400 font-mono">
                  {(sampleEvent.confidence * 100).toFixed(0)}%
                </span>
                <span className="text-[10px] text-slate-600 block">{sampleEvent.method}</span>
              </div>

              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                <span className="text-xs text-slate-500 block">Ground PM2.5 / PM10</span>
                <span className="text-lg font-bold text-amber-400 font-mono">
                  {sampleEvent.evidence.sensor.pm25} / {sampleEvent.evidence.sensor.pm10}
                </span>
                <span className="text-[10px] text-slate-600 block">CPCB Anomaly 0.8</span>
              </div>

              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                <span className="text-xs text-slate-500 block">Sentinel-5P NO2</span>
                <span className="text-lg font-bold text-cyan-400 font-mono">
                  {sampleEvent.evidence.satellite.no2}
                </span>
                <span className="text-[10px] text-slate-600 block">Aerosol: {sampleEvent.evidence.satellite.aerosol}</span>
              </div>

              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                <span className="text-xs text-slate-500 block">Source Hypothesis</span>
                <span className="text-sm font-semibold text-purple-400 block truncate">
                  {sampleEvent.source_hypothesis.category}
                </span>
                <span className="text-[10px] text-slate-600 block">Conf: {(sampleEvent.source_hypothesis.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-800/80">
              <div className="text-xs text-slate-400">
                Routed to: <span className="text-white font-medium">{sampleEvent.authority_class}</span> (Status: <span className="text-emerald-400 uppercase font-mono">{sampleEvent.status}</span>)
              </div>
              <div className="flex gap-2">
                <button className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white transition-colors">
                  Dismiss False Alarm
                </button>
                <button className="px-3.5 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-xs font-semibold text-slate-950 transition-colors shadow-lg shadow-cyan-500/20">
                  Dispatch Field Inspection
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
