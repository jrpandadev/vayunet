'use client';
import { motion } from 'framer-motion';
import dynamic from 'next/dynamic';
import { TextEffect } from '@/components/ui/text-effect';

// Subtle client-only 3D atmospheric flow with SSR disabled
const HeroAtmosphere3D = dynamic(
  () => import('@/components/3d/HeroAtmosphere3D'),
  { ssr: false }
);

export default function HeroSection() {
  return (
    <section className="relative pt-32 pb-20 overflow-hidden border-b border-surface-variant bg-[#03111F]">
      {/* Restrained 3D Atmospheric Particle Streamlines */}
      <HeroAtmosphere3D />

      {/* Decorative Grid Background */}
      <div
        className="absolute inset-0 z-0 opacity-10 pointer-events-none"
        style={{
          backgroundImage:
            'radial-gradient(circle at 2px 2px, var(--color-on-surface) 1px, transparent 0)',
          backgroundSize: '32px 32px',
        }}
      />

      {/* Glow Effect - Slow radial animation */}
      <motion.div
        animate={{ scale: [1, 1.1, 1], opacity: [0.15, 0.25, 0.15] }}
        transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-primary/15 blur-[120px] rounded-full z-0 pointer-events-none"
      />

      <div className="container relative z-10 mx-auto px-gutter-mobile md:px-gutter text-center max-w-4xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-primary/30 bg-primary/10 mb-8"
        >
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          <span className="text-label-sm text-primary uppercase tracking-widest font-mono">
            Coupled Environmental Intelligence
          </span>
        </motion.div>

        <h1 className="text-display-xl-mobile md:text-display-xl text-on-surface mb-6 leading-tight flex flex-col md:block items-center justify-center">
          <div>
            <TextEffect per="word" as="span" className="inline-block mr-3">
              Pollution is an
            </TextEffect>
            <TextEffect
              per="word"
              as="span"
              delay={0.2}
              className="inline-block text-transparent bg-clip-text bg-gradient-to-r from-primary to-secondary"
            >
              Event,
            </TextEffect>
          </div>
          <TextEffect per="word" as="div" delay={0.4} className="mt-2 md:mt-0">
            Not Just a Number.
          </TextEffect>
        </h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.8 }}
          className="text-body-lg text-on-surface-variant mb-10 max-w-2xl mx-auto"
        >
          We fuse citizen ground-truth, authoritative sensor data, and Sentinel-5P satellite telemetry to detect, verify, and resolve hyper-local environmental anomalies.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 1 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-space-md"
        >
          <motion.a
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            href="#explorer"
            className="w-full sm:w-auto h-12 px-8 rounded-full bg-on-surface text-surface text-body-md font-bold flex items-center justify-center gap-2 hover:bg-surface-variant hover:text-on-surface transition-colors"
          >
            <span className="material-symbols-outlined text-lg">explore</span>
            Explore Anomalies
          </motion.a>
          <motion.a
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            href="/methodology"
            className="w-full sm:w-auto h-12 px-8 rounded-full border border-outline-variant text-on-surface text-body-md font-bold flex items-center justify-center gap-2 hover:border-primary hover:text-primary transition-colors"
          >
            <span className="material-symbols-outlined text-lg">account_tree</span>
            View Architecture
          </motion.a>
        </motion.div>
      </div>
    </section>
  );
}
