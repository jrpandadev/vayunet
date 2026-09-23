"use client";

import Navbar from "@/components/landing/new/Navbar";
import Hero from "@/components/landing/new/Hero";

export default function Home() {
  return (
    <div className="relative min-h-screen overflow-x-hidden bg-abyss">
      {/* ── Navigation (Layer 30) ── */}
      <Navbar />

      {/* ── Main content: Production Hero System ── */}
      <main className="relative flex min-h-screen w-full flex-col justify-between pt-[64px]">
        <Hero />

        {/* Minimal status bar */}
        <footer
          className="animate-fade-in relative z-10 mx-auto w-full max-w-[1360px] px-6 pb-6 lg:px-10"
          style={{ animationDelay: "0.7s" }}
        >
          <div className="flex flex-wrap items-center justify-between gap-4 border-t border-white/[0.06] pt-4">
            <p className="flex items-center gap-2 font-mono text-[10px] tracking-[0.18em] text-slate-500">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 opacity-70 animate-soft-pulse" />
              SYSTEMS NOMINAL · MULTI-SOURCE INTELLIGENCE
            </p>
            <p className="hidden font-mono text-[10px] tracking-[0.14em] text-slate-600 md:block">
              © 2026 VayuNet
            </p>
          </div>
        </footer>
      </main>
    </div>
  );
}
