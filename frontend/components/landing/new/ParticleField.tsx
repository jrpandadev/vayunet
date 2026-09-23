"use client";

import { useEffect, useRef } from "react";

type Particle = {
  x: number;
  y: number;
  speed: number;
  drift: number;
  phase: number;
  size: number;
  amber: boolean;
  life: number;
  max: number;
};

type FlowLine = {
  y: number;
  amp: number;
  freq: number;
  speed: number;
  offset: number;
  alpha: number;
};

/**
 * Minimal atmospheric layer — slow eastward-drifting particulate matter
 * with very subtle sinusoidal wind-flow lines. Intentionally restrained:
 * fewer particles, lower opacity, more purposeful motion.
 */
export default function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let w = 0;
    let h = 0;
    let raf = 0;
    let t = 0;

    let particles: Particle[] = [];
    let lines: FlowLine[] = [];

    const spawn = (initial: boolean): Particle => {
      // Only ~8% amber (pollution marker) — rest are clean cyan drift
      const amber = Math.random() < 0.08;
      const max = 700 + Math.random() * 600;
      return {
        x: initial ? Math.random() * w : -20 - Math.random() * 40,
        y: Math.random() * h,
        speed: 0.12 + Math.random() * 0.38,
        drift: 0.08 + Math.random() * 0.18,
        phase: Math.random() * Math.PI * 2,
        // Smaller particles for subtlety
        size: 0.4 + Math.random() * 0.9,
        amber,
        life: initial ? Math.random() * max : 0,
        max,
      };
    };

    const buildLines = () => {
      // Three gentle, widely-spaced flow lines
      lines = Array.from({ length: 3 }, (_, i) => ({
        y: h * (0.25 + i * 0.25),
        amp: 8 + Math.random() * 14,
        freq: 0.0012 + Math.random() * 0.001,
        speed: 0.00008 + Math.random() * 0.0001,
        offset: Math.random() * 1000,
        // Very faint
        alpha: 0.025 + Math.random() * 0.03,
      }));
    };

    const resize = () => {
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = Math.max(1, Math.floor(w * dpr));
      canvas.height = Math.max(1, Math.floor(h * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      // Fewer particles — max 55
      const count = Math.min(55, Math.max(24, Math.floor(w / 26)));
      particles = Array.from({ length: count }, () => spawn(true));
      buildLines();
    };

    resize();
    window.addEventListener("resize", resize);

    const drawLines = () => {
      for (const line of lines) {
        ctx.beginPath();
        for (let x = -10; x <= w + 10; x += 18) {
          const y =
            line.y +
            Math.sin(x * line.freq + line.offset + t * line.speed * 1000) * line.amp;
          if (x === -10) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = `rgba(78, 205, 224, ${line.alpha})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    };

    const render = () => {
      t += 1;
      ctx.clearRect(0, 0, w, h);
      drawLines();

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.life += 1;
        p.x += p.speed;
        p.y += Math.sin(p.phase + t * 0.006) * p.drift * 0.28;

        if (p.x > w + 24 || p.life > p.max) {
          particles[i] = spawn(false);
          continue;
        }

        const fadeIn = Math.min(1, p.life / 80);
        const fadeOut = Math.min(1, (p.max - p.life) / 100);
        // Lower max opacity for subtlety
        const a = 0.38 * fadeIn * fadeOut;

        const trail = 8 + p.speed * 12;
        const grad = ctx.createLinearGradient(p.x - trail, p.y, p.x, p.y);
        const col = p.amber ? "245, 165, 36" : "78, 214, 230";
        grad.addColorStop(0, `rgba(${col}, 0)`);
        grad.addColorStop(1, `rgba(${col}, ${a * 0.75})`);
        ctx.strokeStyle = grad;
        ctx.lineWidth = p.size;
        ctx.beginPath();
        ctx.moveTo(p.x - trail, p.y);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();

        // Dot at head — slightly smaller
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * 0.75, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${col}, ${a * 0.85})`;
        ctx.fill();
      }

      raf = requestAnimationFrame(render);
    };

    if (reduced) {
      drawLines();
      for (const p of particles) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.amber ? "rgba(245,165,36,0.22)" : "rgba(78,214,230,0.2)";
        ctx.fill();
      }
    } else {
      raf = requestAnimationFrame(render);
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 h-full w-full"
    />
  );
}
