'use client';
import { motion } from 'framer-motion';
import { InView } from '@/components/ui/in-view';

export default function Methodology() {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.4,
        delayChildren: 0.3
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, x: -10 },
    visible: { opacity: 1, x: 0 }
  };

  return (
    <section className="py-12 border-b border-surface-variant bg-surface" id="methodology">
      <InView>
        <div className="container mx-auto px-gutter-mobile md:px-gutter">
          <div className="flex flex-col lg:flex-row gap-16">
             <div className="lg:w-1/2">
               <h2 className="text-headline-lg text-on-surface mb-6">Scientific Rigor. <br/>Algorithmic Integrity.</h2>
               <p className="text-body-lg text-on-surface-variant mb-6">
                 VayuNet is designed for multi-source evidence fusion. We rely on established meteorological diagnostics and atmospheric science APIs.
               </p>
               <ul className="space-y-4 mb-8">
                 <li className="flex items-start gap-3">
                   <span className="material-symbols-outlined text-primary mt-0.5">check_circle</span>
                   <span className="text-body-sm text-on-surface-variant"><strong>ESA Copernicus (Sentinel-5P):</strong> Designed for satellite anomaly cross-referencing.</span>
                 </li>
                 <li className="flex items-start gap-3">
                   <span className="material-symbols-outlined text-primary mt-0.5">check_circle</span>
                   <span className="text-body-sm text-on-surface-variant"><strong>NOAA / NCEP (GFS):</strong> Meteorological diagnostics for understanding potential regional influence.</span>
                 </li>
                 <li className="flex items-start gap-3">
                   <span className="material-symbols-outlined text-primary mt-0.5">check_circle</span>
                   <span className="text-body-sm text-on-surface-variant"><strong>Google Gemini:</strong> AI-assisted evidence interpretation and human-in-the-loop verification.</span>
                 </li>
               </ul>
             </div>

             <div className="lg:w-1/2">
                <div className="bg-surface-container rounded-2xl border border-surface-variant p-1 overflow-hidden font-label-sm">
                   <div className="flex items-center gap-2 px-4 py-2 border-b border-surface-variant bg-surface">
                     <div className="flex gap-1.5">
                       <div className="w-3 h-3 rounded-full bg-error"></div>
                       <div className="w-3 h-3 rounded-full bg-tertiary"></div>
                       <div className="w-3 h-3 rounded-full bg-primary"></div>
                     </div>
                     <span className="text-on-surface-variant ml-2">vayunet-verification-engine.log</span>
                     <span className="ml-auto text-[10px] uppercase tracking-wider text-error font-bold px-2 py-0.5 border border-error/50 rounded">Conceptual Pipeline Trace</span>
                   </div>
                   <div className="p-4 text-on-surface-variant bg-[#080e19] max-h-80 overflow-y-auto">
                     <motion.div
                       variants={containerVariants}
                       initial="hidden"
                       whileInView="visible"
                       viewport={{ once: true, margin: '-50px' }}
                       className="flex flex-col gap-1 font-label-md leading-relaxed text-[11px] md:text-xs text-[#a0aabf] font-mono whitespace-pre-wrap"
                     >
                        <motion.div variants={itemVariants}><span className="text-primary">[DEMO]</span> Sentinel-5P evidence received</motion.div>
                        <motion.div variants={itemVariants}><span className="text-primary">[DEMO]</span> Meteorological context retrieved</motion.div>
                        <motion.div variants={itemVariants}><span className="text-tertiary">[DEMO]</span> Potential anomaly identified</motion.div>
                        <motion.div variants={itemVariants}><span className="text-primary">[DEMO]</span> Cross-source consistency check</motion.div>
                        <motion.div variants={itemVariants}><span className="text-primary">[DEMO]</span> Confidence assessment</motion.div>
                        <motion.div variants={itemVariants}><span className="text-error">[DEMO]</span> Human review required</motion.div>
                     </motion.div>
                   </div>
                </div>
             </div>
          </div>
        </div>
      </InView>
    </section>
  );
}
