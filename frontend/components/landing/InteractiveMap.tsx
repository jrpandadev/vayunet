'use client';
import { motion } from 'framer-motion';
import { InView } from '@/components/ui/in-view';

export default function InteractiveMap() {
  const stages = [
    { id: 'observe', label: 'OBSERVE', desc: 'Satellite & ground sensor telemetry.' },
    { id: 'fuse', label: 'FUSE', desc: 'Multi-modal evidence aggregation.' },
    { id: 'model', label: 'MODEL', desc: 'Meteorological context & dispersion.' },
    { id: 'verify', label: 'VERIFY', desc: 'Human-in-the-loop review process.' },
    { id: 'forecast', label: 'FORECAST', desc: 'Predictive transport trajectories.' },
    { id: 'act', label: 'ACT', desc: 'Actionable authority dossiers.' },
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
        delayChildren: 0.2
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
  };

  return (
    <section className="py-20 border-b border-surface-variant overflow-hidden" id="concept">
      <InView>
        <div className="container mx-auto px-gutter-mobile md:px-gutter">
          <div className="mb-12 text-center">
            <h2 className="text-headline-lg text-on-surface mb-4">Architecture Pipeline</h2>
            <p className="text-body-lg text-on-surface-variant max-w-2xl mx-auto">
              A conceptual demonstration of VayuNet's end-to-end event verification process.
            </p>
          </div>

          <div className="bg-surface-container rounded-xl border border-surface-variant p-8 md:p-12 relative">
            {/* Connecting Line Background */}
            <div className="hidden md:block absolute top-1/2 left-12 right-12 h-[2px] bg-surface-variant -translate-y-1/2 z-0"></div>

            {/* Animated signal line */}
            <div className="hidden md:block absolute top-1/2 left-12 right-12 h-[2px] -translate-y-1/2 z-0 overflow-hidden">
              <motion.div
                initial={{ x: '-100%' }}
                animate={{ x: '100%' }}
                transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
                className="absolute top-0 bottom-0 left-0 w-1/3 bg-gradient-to-r from-transparent via-primary to-transparent opacity-80"
              ></motion.div>
            </div>

            <motion.div
              variants={containerVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-100px' }}
              className="relative flex flex-col md:flex-row justify-between gap-8 md:gap-4 z-10"
            >
              {stages.map((stage, i) => (
                <motion.div
                  key={stage.id}
                  variants={itemVariants}
                  className="flex-1 flex flex-col items-center text-center group"
                >
                   <motion.div
                     whileHover={{ scale: 1.1, boxShadow: '0 0 20px rgba(78,222,163,0.3)' }}
                     className="w-12 h-12 rounded-full bg-surface border-2 border-primary flex items-center justify-center mb-4 shadow-[0_0_15px_rgba(78,222,163,0.15)] relative z-10 transition-shadow duration-300"
                   >
                      <span className="text-label-md text-on-surface font-bold">{i+1}</span>
                   </motion.div>
                   <h4 className="text-label-lg text-primary tracking-widest mb-2 transition-colors duration-300 group-hover:text-secondary">{stage.label}</h4>
                   <p className="text-[13px] leading-relaxed text-on-surface-variant px-2">{stage.desc}</p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </div>
      </InView>
    </section>
  );
}
