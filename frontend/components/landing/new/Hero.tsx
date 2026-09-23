"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Play, UserRound, ShieldCheck } from "lucide-react";
import Link from "next/link";
import {
  motion,
  useMotionTemplate,
  useMotionValue,
  useReducedMotion,
} from "motion/react";
import IntelligencePanel from "./IntelligencePanel";
import ParticleField from "./ParticleField";

/* ── Subtle Mouse Parallax Hook ── */
function useParallax() {
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const isMobile = window.matchMedia("(max-width: 768px)").matches;

    if (reduced || isMobile) return;

    let rafId = 0;
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      targetX = (e.clientX / window.innerWidth) * 2 - 1;
      targetY = (e.clientY / window.innerHeight) * 2 - 1;
    };

    const animate = () => {
      currentX += (targetX - currentX) * 0.05;
      currentY += (targetY - currentY) * 0.05;
      setOffset({ x: currentX, y: currentY });
      rafId = requestAnimationFrame(animate);
    };

    window.addEventListener("mousemove", handleMouseMove);
    rafId = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      cancelAnimationFrame(rafId);
    };
  }, []);

  return offset;
}

/* ── Watermelon-style stagger container ── */
const heroVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.09, delayChildren: 0.05 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", stiffness: 280, damping: 26 },
  },
};

const panelVariants = {
  hidden: { opacity: 0, x: 32, scale: 0.985 },
  visible: {
    opacity: 1,
    x: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 220, damping: 28, delay: 0.18 },
  },
};

/* ── Primary CTA Button ── */
function PrimaryButton() {
  const mouseX = useMotionValue(0);
  const shimmerLeft = useMotionTemplate`${mouseX}px`;
  const shouldReduce = useReducedMotion();

  return (
    <motion.div
      className="relative overflow-hidden rounded-full"
      whileHover={shouldReduce ? {} : { y: -2 }}
      whileTap={shouldReduce ? {} : { scale: 0.97 }}
      transition={{ type: "spring", stiffness: 380, damping: 30 }}
      onMouseMove={(e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        mouseX.set(e.clientX - rect.left);
      }}
    >
      <Link
        href="/dashboard/map"
        className="group relative inline-flex items-center gap-2 rounded-full bg-signal px-6 py-3.5 text-[14px] font-semibold text-[#03272c] shadow-[0_0_24px_-8px_rgba(53,219,232,0.55)] transition-shadow duration-300 hover:shadow-[0_0_36px_-6px_rgba(53,219,232,0.75)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/50"
      >
        {!shouldReduce && (
          <motion.span
            className="pointer-events-none absolute inset-0 rounded-full"
            style={{
              background: useMotionTemplate`radial-gradient(180px circle at ${shimmerLeft} 50%, rgba(255,255,255,0.25), transparent 70%)`,
            }}
          />
        )}

        <span className="relative flex items-center gap-2">
          Explore Live Intelligence
          <motion.span
            whileHover={{ x: 3 }}
            transition={{ type: "spring", stiffness: 400, damping: 28 }}
            className="inline-flex"
          >
            <ArrowRight className="h-3.5 w-3.5" strokeWidth={2.6} />
          </motion.span>
        </span>
      </Link>
    </motion.div>
  );
}

/* ── Secondary CTA Button ── */
function SecondaryButton() {
  const shouldReduce = useReducedMotion();
  return (
    <motion.div
      whileHover={shouldReduce ? {} : { y: -2 }}
      whileTap={shouldReduce ? {} : { scale: 0.97 }}
      transition={{ type: "spring", stiffness: 380, damping: 30 }}
    >
      <Link
        href="/methodology"
        className="group inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-6 py-3.5 text-[14px] font-medium text-slate-300 backdrop-blur-sm transition-colors duration-200 hover:border-white/20 hover:bg-white/[0.06] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/20"
      >
        <motion.span
          whileHover={{ scale: 1.15 }}
          transition={{ type: "spring", stiffness: 400, damping: 24 }}
          className="inline-flex text-signal"
        >
          <Play className="h-3 w-3" strokeWidth={0} fill="currentColor" />
        </motion.span>
        How It Works
      </Link>
    </motion.div>
  );
}

export default function Hero() {
  const shouldReduce = useReducedMotion();
  const parallax = useParallax();

  return (
    <section className="relative flex-1 flex items-center justify-center w-full min-h-[calc(100vh-140px)] py-8 lg:py-12">
      {/* ── Layer 0: VayuNet dark base background ── */}
      <div className="absolute inset-0 bg-abyss -z-10" aria-hidden="true" />

      {/* ── Layer 1: Static earth-atmosphere.png background (Full-bleed edge-to-edge) ── */}
      <div
        className="absolute -top-[64px] inset-x-0 bottom-0 overflow-hidden pointer-events-none z-[1]"
        aria-hidden="true"
      >
        <div
          className="relative w-full h-full transition-transform duration-100 ease-out"
          style={{
            transform: shouldReduce
              ? undefined
              : `translate3d(${parallax.x * -8}px, ${parallax.y * -8}px, 0) scale(1.03)`,
          }}
        >
          <img
            src="/images/earth-atmosphere.png"
            alt="Earth Atmosphere"
            className="w-full h-full object-cover object-center select-none"
          />
        </div>
      </div>

      {/* ── Layer 2: Subtle transparent readability scrim ── */}
      <div className="absolute -top-[64px] inset-x-0 bottom-0 pointer-events-none z-[2]" aria-hidden="true">
        {/* Left-to-right subtle gradient to ensure text readability without obscuring the earth */}
        <div className="absolute inset-0 bg-gradient-to-r from-abyss/85 via-abyss/50 to-abyss/20" />
        {/* Top & bottom subtle fade */}
        <div className="absolute inset-0 bg-gradient-to-b from-abyss/60 via-transparent to-abyss/70" />
        {/* Subtle data lines grid */}
        <div className="absolute inset-0 data-lines opacity-35" />
      </div>

      {/* ── Layer 3: Separate atmospheric animation layer ── */}
      <div
        className="absolute -top-[64px] inset-x-0 bottom-0 pointer-events-none z-[3]"
        style={{
          transform: shouldReduce ? undefined : `translate3d(${parallax.x * -3}px, ${parallax.y * -3}px, 0)`,
        }}
        aria-hidden="true"
      >
        <ParticleField />
      </div>

      {/* ── Hero UI Content ── */}
      <div className="relative mx-auto w-full max-w-[1360px] grid items-center gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,460px)] lg:gap-10">
        {/* Layer 10: Hero content */}
        <motion.div
          className="relative z-10 max-w-[600px]"
          variants={heroVariants}
          initial={shouldReduce ? false : "hidden"}
          animate="visible"
        >
          {/* Eyebrow */}
          <motion.div variants={itemVariants} className="mb-6 inline-flex items-center gap-2.5">
            <span className="flex items-center gap-1.5 font-mono text-[10.5px] font-medium tracking-[0.22em] text-signal/90">
              <span className="relative inline-block h-1.5 w-1.5 rounded-full bg-signal">
                <motion.span
                  className="absolute inset-0 rounded-full bg-signal"
                  animate={shouldReduce ? {} : { scale: [1, 2.6, 2.6], opacity: [0.7, 0, 0] }}
                  transition={{ duration: 2.4, repeat: Infinity, ease: "easeOut" }}
                />
              </span>
              EVIDENCE · FORECAST · ACTION
            </span>
          </motion.div>

          {/* Headline */}
          <motion.h1
            variants={itemVariants}
            className="font-display text-[42px] font-bold leading-[1.06] tracking-[-0.025em] text-white sm:text-[54px] lg:text-[62px]"
          >
            See Pollution Before
            <br />
            It Becomes a{" "}
            <span className="bg-gradient-to-r from-signal to-[#5ce8f4] bg-clip-text text-transparent">
              Crisis.
            </span>
          </motion.h1>

          {/* Tagline */}
          <motion.p
            variants={itemVariants}
            className="mt-4 text-[17px] font-light tracking-[0.01em] text-slate-300 lg:text-[18px]"
          >
            Cleaner Air.{" "}
            <span className="font-medium text-slate-100">Better Tomorrow.</span>
          </motion.p>

          {/* Description */}
          <motion.p
            variants={itemVariants}
            className="mt-5 max-w-[520px] text-[15px] leading-[1.7] text-slate-400"
          >
            VayuNet detects pollution events before they peak — combining ground
            sensors, satellite data, and weather models into a 72-hour forecast
            with human-reviewed evidence.
          </motion.p>

          {/* CTAs */}
          <motion.div
            variants={itemVariants}
            className="mt-8 flex flex-wrap items-center gap-3.5"
          >
            <PrimaryButton />
            <SecondaryButton />
          </motion.div>

          {/* Quick links: Citizen View & Authority Console */}
          <motion.div
            variants={itemVariants}
            className="mt-8 flex items-center gap-5 pt-2"
          >
            <Link
              href="/dashboard/map"
              className="group inline-flex items-center gap-2 text-sm text-slate-400 transition-colors duration-200 hover:text-signal"
            >
              <UserRound className="h-4 w-4" strokeWidth={2} />
              <span>Citizen View</span>
              <ArrowRight
                className="h-3.5 w-3.5 transition-transform duration-200 group-hover:translate-x-0.5"
                strokeWidth={2.2}
              />
            </Link>
            <span className="h-4 w-px bg-white/15" />
            <Link
              href="/authority"
              className="group inline-flex items-center gap-2 text-sm text-slate-400 transition-colors duration-200 hover:text-signal"
            >
              <ShieldCheck className="h-4 w-4" strokeWidth={2} />
              <span>Authority Console</span>
              <ArrowRight
                className="h-3.5 w-3.5 transition-transform duration-200 group-hover:translate-x-0.5"
                strokeWidth={2.2}
              />
            </Link>
          </motion.div>
        </motion.div>

        {/* Layer 20: Intelligence Panel */}
        <motion.div
          className="relative z-20 flex justify-center lg:justify-end"
          variants={panelVariants}
          initial={shouldReduce ? false : "hidden"}
          animate="visible"
        >
          <IntelligencePanel />
        </motion.div>
      </div>
    </section>
  );
}
