"use client";

import { useRef } from "react";
import { motion, useReducedMotion } from "motion/react";
import Link from "next/link";

const NAV_LINKS = [
  { label: "How It Works", href: "/methodology" },
  { label: "Dashboard", href: "/dashboard" },
  { label: "Technology", href: "/methodology" },
  { label: "Team", href: "#" },
];

function WaveMark() {
  return (
    <svg width="32" height="28" viewBox="0 0 34 30" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="wave-nav-grad" x1="0" y1="0" x2="34" y2="30" gradientUnits="userSpaceOnUse">
          <stop stopColor="#4ee6f2" />
          <stop offset="1" stopColor="#0f8a9c" />
        </linearGradient>
      </defs>
      <path d="M2 8c3.2 0 4.8-3 8-3s4.8 3 8 3 4.8-3 8-3 4.8 3 6 3" stroke="url(#wave-nav-grad)" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M2 15c3.2 0 4.8-3 8-3s4.8 3 8 3 4.8-3 8-3 4.8 3 6 3" stroke="url(#wave-nav-grad)" strokeWidth="2.4" strokeLinecap="round" opacity="0.7" />
      <path d="M2 22c3.2 0 4.8-3 8-3s4.8 3 8 3 4.8-3 8-3 4.8 3 6 3" stroke="url(#wave-nav-grad)" strokeWidth="2.4" strokeLinecap="round" opacity="0.4" />
    </svg>
  );
}

export default function Navbar() {
  const shouldReduce = useReducedMotion();
  const hovered = useRef<string | null>(null);

  const spring = { type: "spring" as const, stiffness: 380, damping: 30 };

  return (
    <motion.header
      className="absolute inset-x-0 top-0 z-30"
      initial={shouldReduce ? false : { opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 0.7, 0.2, 1] }}
    >
      <div className="border-b border-white/[0.05] bg-abyss/50 backdrop-blur-lg">
        <nav className="mx-auto flex h-[64px] max-w-[1360px] items-center justify-between gap-6 px-6 lg:px-10">
          {/* Brand */}
          <Link href="/" className="group flex items-center gap-3">
            <motion.span
              whileHover={shouldReduce ? {} : { y: -2 }}
              transition={spring}
              className="inline-flex"
            >
              <WaveMark />
            </motion.span>
            <span className="font-display text-[20px] font-bold tracking-tight text-white">
              VayuNet
            </span>
          </Link>

          {/* Nav links — Watermelon-style shared layoutId underline */}
          <ul className="hidden items-center gap-7 lg:flex">
            {NAV_LINKS.map((link) => (
              <li key={link.label} className="relative">
                <Link
                  href={link.href}
                  className="relative py-1 text-[13.5px] font-medium text-slate-400 transition-colors duration-200 hover:text-slate-100"
                  onMouseEnter={() => { hovered.current = link.label; }}
                  onMouseLeave={() => { hovered.current = null; }}
                >
                  {link.label}

                  {/* Shared motion underline — Watermelon's signature nav interaction */}
                  <motion.span
                    className="absolute -bottom-[22px] left-0 h-px w-full bg-signal/50"
                    initial={{ scaleX: 0 }}
                    whileHover={{ scaleX: 1 }}
                    style={{ originX: 0 }}
                    transition={spring}
                  />
                </Link>
              </li>
            ))}
          </ul>

          {/* CTA pill */}
          <motion.div
            whileHover={shouldReduce ? {} : { scale: 1.03 }}
            whileTap={shouldReduce ? {} : { scale: 0.97 }}
            transition={spring}
          >
            <Link
              href="/dashboard/map"
              className="hidden items-center gap-2 rounded-full border border-signal/30 bg-signal/[0.06] px-4 py-2 text-[13px] font-semibold text-signal transition-colors duration-200 hover:border-signal/60 hover:bg-signal/[0.12] sm:flex focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/50"
            >
              Open Platform
            </Link>
          </motion.div>
        </nav>
      </div>
    </motion.header>
  );
}
