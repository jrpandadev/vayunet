"use client";

import { useEffect, useRef, useState } from "react";
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  useReducedMotion,
  AnimatePresence,
} from "motion/react";
import NumberFlow from "@number-flow/react";
import { MapPin, TriangleAlert, Wind, ChevronRight, ArrowUp, ArrowDown } from "lucide-react";
import ForecastChart from "./ForecastChart";

import { getEvents } from "@/lib/api";

/* ── Tooltip-enhanced stat cell ── */
interface StatCellProps {
  label: string;
  children: React.ReactNode;
  tooltip?: string;
}

function StatCell({ label, children, tooltip }: StatCellProps) {
  const [hovered, setHovered] = useState(false);
  const shouldReduce = useReducedMotion();

  return (
    <motion.div
      className="relative cursor-default px-4 py-3.5"
      onHoverStart={() => setHovered(true)}
      onHoverEnd={() => setHovered(false)}
      whileHover={shouldReduce ? {} : { backgroundColor: "rgba(255,255,255,0.025)" }}
      transition={{ duration: 0.2 }}
    >
      <p className="font-mono text-[10px] tracking-[0.18em] text-slate-500">{label}</p>
      <div className="mt-1.5">{children}</div>

      <AnimatePresence>
        {hovered && tooltip && (
          <motion.div
            className="absolute -top-9 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-lg border border-white/10 bg-[#0a1626]/95 px-2.5 py-1.5 font-mono text-[10px] text-slate-300 shadow-xl backdrop-blur-md"
            initial={{ opacity: 0, y: 4, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.96 }}
            transition={{ type: "spring", stiffness: 400, damping: 28 }}
          >
            {tooltip}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/* ── Detection pipeline steps ── */
const PIPELINE = ["EVIDENCE", "FORECAST", "RISK", "REVIEW"] as const;

function PipelineStep({ step, index }: { step: string; index: number }) {
  const isReview = step === "REVIEW";
  return (
    <motion.span
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        type: "spring",
        stiffness: 320,
        damping: 28,
        delay: 0.6 + index * 0.08,
      }}
      className={`rounded px-1.5 py-0.5 font-mono text-[9px] tracking-[0.12em] ${
        isReview
          ? "bg-ember/10 text-ember"
          : "bg-signal/10 text-signal"
      }`}
    >
      {step}
    </motion.span>
  );
}

/* ── Main panel ── */
export default function IntelligencePanel() {
  const shouldReduce = useReducedMotion();

  const [pm25Val, setPm25Val] = useState<number | null>(null);
  const [confVal, setConfVal] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function fetchEvents() {
      try {
        const data = await getEvents();
        if (mounted) {
          if (data && data.length > 0) {
            const maxPm25 = Math.max(...data.map((e: any) => e.peak_pm25 || 0));
            const maxConf = Math.max(...data.map((e: any) => e.confidence_score || 0));
            setPm25Val(maxPm25);
            setConfVal(maxConf);
          }
        }
      } catch (err) {
        // Could be unauthenticated or backend error
        if (mounted) {
          setPm25Val(null);
          setConfVal(null);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }
    fetchEvents();
    return () => { mounted = false; };
  }, []);

  /* ── Mouse-tracked 3-D tilt (Watermelon card pattern) ── */
  const panelRef = useRef<HTMLElement>(null);
  const rawRotateX = useMotionValue(0);
  const rawRotateY = useMotionValue(0);
  const rotateX = useSpring(rawRotateX, { stiffness: 160, damping: 22 });
  const rotateY = useSpring(rawRotateY, { stiffness: 160, damping: 22 });
  const glowX = useTransform(rotateY, [-6, 6], ["0%", "100%"]);
  const glowOpacity = useTransform(
    rawRotateX,
    [-6, 0, 6],
    [0.04, 0, 0.04],
  );

  function handleMouseMove(e: React.MouseEvent<HTMLElement>) {
    if (shouldReduce) return;
    const rect = panelRef.current?.getBoundingClientRect();
    if (!rect) return;
    const cx = (e.clientX - rect.left) / rect.width - 0.5;
    const cy = (e.clientY - rect.top) / rect.height - 0.5;
    rawRotateY.set(cx * 7);
    rawRotateX.set(-cy * 5);
  }

  function handleMouseLeave() {
    rawRotateX.set(0);
    rawRotateY.set(0);
  }

  const Arrow = ArrowUp;
  const arrowColor = "text-risk";

  return (
    <motion.aside
      ref={panelRef as React.Ref<HTMLElement>}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={
        shouldReduce
          ? {}
          : {
              rotateX,
              rotateY,
              transformStyle: "preserve-3d",
              transformPerspective: 900,
            }
      }
      className="w-full max-w-[440px] rounded-2xl border border-signal/10 bg-deep/80 shadow-[0_0_0_1px_rgba(5,10,20,0.7),0_28px_80px_-20px_rgba(0,0,0,0.85),0_0_80px_-24px_rgba(53,219,232,0.10)] backdrop-blur-2xl"
    >
      {/* Tilt-reactive glow overlay */}
      {!shouldReduce && (
        <motion.div
          className="pointer-events-none absolute inset-0 rounded-2xl"
          style={{
            background: useTransform(
              glowX,
              (x) =>
                `radial-gradient(400px at ${x} 0%, rgba(53,219,232,0.07), transparent 60%)`,
            ),
            opacity: glowOpacity,
          }}
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between gap-3 px-5 pb-3.5 pt-5">
        <div className="flex items-center gap-2.5">
          <span className="flex h-7 w-7 items-center justify-center rounded-full border border-signal/25 bg-signal/[0.08]">
            <MapPin className="h-3.5 w-3.5 text-signal" strokeWidth={2.2} />
          </span>
          <h2 className="font-mono text-[13px] font-semibold tracking-[0.16em] text-slate-100">
            DELHI NCR
          </h2>
        </div>
        <motion.span
          className="flex items-center gap-1.5 rounded-full border border-ember/30 bg-ember/[0.07] px-3 py-1.5"
          animate={shouldReduce ? {} : { borderColor: ["rgba(245,165,36,0.3)", "rgba(245,165,36,0.55)", "rgba(245,165,36,0.3)"] }}
          transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
        >
          <TriangleAlert className="h-3 w-3 text-ember" strokeWidth={2.4} />
          <span className="font-mono text-[10px] font-medium tracking-[0.12em] text-ember">
            ELEVATED RISK
          </span>
        </motion.span>
      </div>

      <div className="space-y-2 px-4 pb-4">
        {/* Forecast chart */}
        <div className="rounded-xl border border-white/[0.06] bg-panel/50 p-4">
          <div className="mb-3 flex items-baseline justify-between">
            <p className="text-[12.5px] font-medium text-slate-200">
              PM2.5 Forecast{" "}
              <span className="text-slate-600">µg/m³</span>
            </p>
            <span className="font-mono text-[9.5px] tracking-[0.18em] text-slate-600">
              ILLUSTRATIVE · 72H
            </span>
          </div>
          <ForecastChart />
        </div>

        {/* Stat row with NumberFlow animated values */}
        <div className="grid grid-cols-3 divide-x divide-white/[0.06] rounded-xl border border-white/[0.06] bg-panel/50">
          <StatCell
            label="PM2.5"
            tooltip={pm25Val !== null ? "Measured PM2.5 level" : "Awaiting model output"}
          >
            <p className="flex items-baseline gap-1">
              {pm25Val !== null && !loading ? (
                <>
                  <NumberFlow
                    value={Math.round(pm25Val)}
                    className="font-mono text-[24px] font-semibold leading-none text-signal"
                    transformTiming={{ duration: 600, easing: "ease-out" }}
                    spinTiming={{ duration: 600, easing: "ease-out" }}
                    opacityTiming={{ duration: 350, easing: "ease-out" }}
                  />
                  <span className="text-[10px] text-slate-500">µg/m³</span>
                  <motion.span
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <Arrow className={`h-3 w-3 ${arrowColor}`} strokeWidth={2.6} />
                  </motion.span>
                </>
              ) : (
                <span className="font-mono text-[11px] text-slate-500">UNAVAILABLE</span>
              )}
            </p>
          </StatCell>

          <StatCell label="RISK" tooltip="Evidence-supported classification">
            <p className="flex items-center gap-1.5 font-mono text-[20px] font-semibold leading-none text-risk">
              {pm25Val !== null && !loading ? (
                <>
                  <span className="relative flex h-1.5 w-1.5 shrink-0">
                    <motion.span
                      className="absolute inset-0 rounded-full bg-risk"
                      animate={shouldReduce ? {} : { scale: [1, 2.4, 2.4], opacity: [0.7, 0, 0] }}
                      transition={{ duration: 2.1, repeat: Infinity, ease: "easeOut" }}
                    />
                    <span className="relative h-1.5 w-1.5 rounded-full bg-risk" />
                  </span>
                  HIGH
                </>
              ) : (
                <span className="font-mono text-[11px] text-slate-500">UNAVAILABLE</span>
              )}
            </p>
          </StatCell>

          <StatCell label="CONFIDENCE" tooltip="Model confidence score">
            {confVal !== null && !loading ? (
              <NumberFlow
                value={Math.round(confVal * 100) / 100}
                format={{ minimumFractionDigits: 2, maximumFractionDigits: 2 }}
                className="font-mono text-[24px] font-semibold leading-none text-signal"
                transformTiming={{ duration: 700, easing: "ease-out" }}
                spinTiming={{ duration: 700, easing: "ease-out" }}
                opacityTiming={{ duration: 380, easing: "ease-out" }}
              />
            ) : (
              <span className="font-mono text-[11px] text-slate-500">UNAVAILABLE</span>
            )}
          </StatCell>
        </div>

        {/* Detection pipeline — staggered mount */}
        <div className="rounded-xl border border-white/[0.06] bg-panel/50 px-4 py-3">
          <p className="mb-2 font-mono text-[9.5px] tracking-[0.2em] text-slate-600">
            DETECTION PIPELINE
          </p>
          <div className="flex items-center gap-1.5">
            {PIPELINE.map((step, i) => (
              <div key={step} className="flex items-center gap-1.5">
                <PipelineStep step={step} index={i} />
                {i < PIPELINE.length - 1 && (
                  <ChevronRight className="h-2.5 w-2.5 shrink-0 text-slate-700" strokeWidth={2} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Event card — Watermelon-style interactive card */}
        <motion.button
          type="button"
          className="group flex w-full items-center gap-3.5 rounded-xl border border-white/[0.06] bg-panel/50 px-4 py-3.5 text-left"
          whileHover={
            shouldReduce
              ? {}
              : {
                  borderColor: "rgba(53,219,232,0.28)",
                  backgroundColor: "rgba(53,219,232,0.04)",
                  x: 2,
                }
          }
          whileTap={shouldReduce ? {} : { scale: 0.99 }}
          transition={{ type: "spring", stiffness: 360, damping: 26 }}
        >
          <motion.span
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-signal/25 bg-signal/[0.07]"
            whileHover={shouldReduce ? {} : { borderColor: "rgba(53,219,232,0.45)", backgroundColor: "rgba(53,219,232,0.12)" }}
            transition={{ duration: 0.25 }}
          >
            <Wind className="h-4 w-4 text-signal" strokeWidth={2} />
          </motion.span>

          <span className="min-w-0 flex-1">
            <span className="block font-mono text-[9.5px] tracking-[0.2em] text-slate-500">
              POLLUTION EVENT
            </span>
            <span className="mt-0.5 block truncate text-[14px] font-medium text-slate-100">
              Particulate accumulation
            </span>
            <span className="mt-0.5 block font-mono text-[10px] tracking-[0.1em]">
              <span className="text-slate-600">STATUS: </span>
              <motion.span
                className="text-ember inline-block"
                animate={shouldReduce ? {} : { opacity: [1, 0.5, 1] }}
                transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
              >
                UNDER REVIEW
              </motion.span>
            </span>
          </span>

          <motion.span
            className="text-slate-600"
            whileHover={shouldReduce ? {} : { x: 3, color: "rgb(53,219,232)" }}
            transition={{ type: "spring", stiffness: 400, damping: 28 }}
          >
            <ChevronRight className="h-3.5 w-3.5" strokeWidth={2.2} />
          </motion.span>
        </motion.button>
      </div>
    </motion.aside>
  );
}
