"use client";

import { useState } from "react";
import Link from "next/link";

export default function CitizenReportPage() {
  const [eventType, setEventType] = useState("smoke");
  const [description, setDescription] = useState("");
  const [city, setCity] = useState("delhi");
  const [status, setStatus] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("Report submitted! Ingesting evidence for multimodal Gemini analysis...");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6">
      <div className="max-w-xl mx-auto space-y-6">
        <Link href="/" className="text-sm text-emerald-400 hover:underline inline-flex items-center gap-1">
          &larr; Back to VayuNet
        </Link>

        <header className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight text-white">Report Pollution Incident</h1>
          <p className="text-sm text-slate-400">
            Submit photo, audio, or text evidence. VayuNet fuses citizen reports with sensor and satellite verification.
          </p>
        </header>

        <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-5">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Incident Category
            </label>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="smoke">Industrial Smoke / Factory Emission</option>
              <option value="biomass">Stubble / Biomass Burning</option>
              <option value="dust">Construction & Road Dust</option>
              <option value="traffic">Severe Traffic Exhaust</option>
              <option value="other">Other Abnormal Odor / Episode</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              City / Location
            </label>
            <select
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="delhi">Delhi (Anand Vihar / NCR)</option>
              <option value="mumbai">Mumbai (Bandra-Kurla)</option>
              <option value="bhubaneswar">Bhubaneswar (Patia)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Photo Evidence (Optional)
            </label>
            <div className="border-2 border-dashed border-slate-800 rounded-xl p-6 text-center hover:border-slate-700 cursor-pointer">
              <span className="text-3xl block mb-1">📷</span>
              <span className="text-sm text-slate-400">Upload or capture photo</span>
              <p className="text-xs text-slate-500 mt-1">Processed by Gemini Vision for plume density & source type</p>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Description (Multilingual / Hindi / English)
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. भारी धुआं है यहां or Dense black smoke visible near bypass road..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-200 focus:outline-none focus:border-emerald-500 text-sm"
            />
          </div>

          <button
            type="submit"
            className="w-full py-3 px-4 rounded-xl bg-emerald-500 hover:bg-emerald-400 font-semibold text-slate-950 transition-colors shadow-lg shadow-emerald-500/20"
          >
            Submit Verified Report
          </button>

          {status && (
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs">
              {status}
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
