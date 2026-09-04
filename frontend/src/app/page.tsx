import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6">
      <div className="max-w-3xl w-full text-center space-y-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-medium">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          Federated Environmental Intelligence Platform
        </div>

        <h1 className="text-5xl font-extrabold tracking-tight sm:text-6xl bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
          VayuNet
        </h1>

        <p className="text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed">
          India-scale hyper-local pollution detection fusing citizen evidence, ground sensors, satellite imagery, and weather data into verified, explainable action.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4">
          <Link
            href="/report"
            className="group relative flex flex-col items-start p-6 rounded-2xl bg-slate-900 border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-850 transition-all text-left shadow-lg"
          >
            <span className="text-2xl mb-2">📸</span>
            <h2 className="text-xl font-semibold text-white group-hover:text-emerald-400 transition-colors">
              Citizen Report PWA &rarr;
            </h2>
            <p className="text-sm text-slate-400 mt-2">
              Submit photo, voice, and localized reports of smoke, stubble burning, or industrial emissions.
            </p>
          </Link>

          <Link
            href="/dashboard"
            className="group relative flex flex-col items-start p-6 rounded-2xl bg-slate-900 border border-slate-800 hover:border-cyan-500/50 hover:bg-slate-850 transition-all text-left shadow-lg"
          >
            <span className="text-2xl mb-2">🛡️</span>
            <h2 className="text-xl font-semibold text-white group-hover:text-cyan-400 transition-colors">
              Authority Dashboard &rarr;
            </h2>
            <p className="text-sm text-slate-400 mt-2">
              Access real-time hotspot maps, fused evidence confidence, XGBoost forecasts, and dispatch alerts.
            </p>
          </Link>
        </div>

        <div className="pt-6 border-t border-slate-900 text-xs text-slate-500 flex justify-between items-center">
          <span>Locked Event Schema (§11)</span>
          <span>Status: 100% Free-Tier Architecture</span>
        </div>
      </div>
    </div>
  );
}
