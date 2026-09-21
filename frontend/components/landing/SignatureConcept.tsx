'use client';
import { motion } from 'framer-motion';
import { InView } from '@/components/ui/in-view';

export default function SignatureConcept() {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.3,
        delayChildren: 0.2
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, x: -20 },
    visible: { opacity: 1, x: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
  };

  const lineVariants = {
    hidden: { height: 0, opacity: 0 },
    visible: { height: 24, opacity: 1, transition: { duration: 0.4 } }
  };

  return (
    <section className="py-24 border-b border-surface-variant bg-surface" id="fusion">
      <div className="container mx-auto px-gutter-mobile md:px-gutter">
        <InView>
          <div className="flex flex-col lg:flex-row gap-16 items-center">
            <div className="lg:w-1/2">
               <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/30 bg-primary/10 mb-6">
                  <span className="text-label-sm text-primary uppercase tracking-widest">Physical Ontology</span>
               </div>
               <h2 className="text-display-xl-mobile md:text-display-xl text-on-surface mb-6">Pollution isn't a number. <br/>It's a physical process.</h2>
               <p className="text-body-lg text-on-surface-variant mb-6">
                 Traditional AQI apps show you a static number (e.g., "Delhi is 350"). That number is a lagging indicator—the aftermath of a process.
               </p>
               <p className="text-body-lg text-on-surface-variant mb-8">
                 VayuNet models the <strong className="text-on-surface">entire lifecycle</strong>. An emission source activates, the atmosphere transports it, chemical reactions alter it, and finally, it impacts a population. By understanding the signature, we can intervene at the source.
               </p>
            </div>
            <div className="lg:w-1/2 w-full">
               <div className="bg-surface-container rounded-2xl p-8 border border-surface-variant relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent"></div>

                  <motion.div
                    variants={containerVariants}
                    initial="hidden"
                    whileInView="visible"
                    viewport={{ once: true, margin: '-50px' }}
                    className="relative z-10 flex flex-col gap-4"
                  >
                     {/* 7-node pipeline */}
                     <motion.div variants={itemVariants} className="flex items-center gap-4 bg-surface p-4 rounded-lg border border-outline-variant">
                       <div className="w-10 h-10 rounded bg-error/20 flex items-center justify-center shrink-0"><span className="material-symbols-outlined text-error">factory</span></div>
                       <div>
                         <h5 className="text-label-lg text-on-surface">1. Source Emission</h5>
                         <p className="text-body-sm text-on-surface-variant">Point (factory) or non-point (crop fire) release.</p>
                       </div>
                     </motion.div>

                     <div className="flex justify-center -my-2"><motion.div variants={lineVariants} className="w-0.5 bg-outline-variant"></motion.div></div>

                     <motion.div variants={itemVariants} className="flex items-center gap-4 bg-surface p-4 rounded-lg border border-outline-variant">
                       <div className="w-10 h-10 rounded bg-secondary/20 flex items-center justify-center shrink-0"><span className="material-symbols-outlined text-secondary">air</span></div>
                       <div>
                         <h5 className="text-label-lg text-on-surface">2. Atmospheric Transport</h5>
                         <p className="text-body-sm text-on-surface-variant">Wind vectors and planetary boundary layer dynamics.</p>
                       </div>
                     </motion.div>

                     <div className="flex justify-center -my-2"><motion.div variants={lineVariants} className="w-0.5 bg-outline-variant"></motion.div></div>

                     <motion.div variants={itemVariants} className="flex items-center gap-4 bg-surface p-4 rounded-lg border border-outline-variant">
                       <div className="w-10 h-10 rounded bg-tertiary/20 flex items-center justify-center shrink-0"><span className="material-symbols-outlined text-tertiary">science</span></div>
                       <div>
                         <h5 className="text-label-lg text-on-surface">3. Chemical Transformation</h5>
                         <p className="text-body-sm text-on-surface-variant">Secondary aerosol formation and photochemical reactions.</p>
                       </div>
                     </motion.div>

                     <div className="flex justify-center -my-2"><motion.div variants={lineVariants} className="w-0.5 bg-outline-variant"></motion.div></div>

                     <motion.div variants={itemVariants} className="flex items-center gap-4 bg-surface p-4 rounded-lg border border-primary/30 bg-primary/5 relative">
                       <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary rounded-r"></div>
                       <div className="w-10 h-10 rounded bg-primary/20 flex items-center justify-center shrink-0"><span className="material-symbols-outlined text-primary">personal_injury</span></div>
                       <div>
                         <h5 className="text-label-lg text-primary">4. Ground-Level Impact (The Event)</h5>
                         <p className="text-body-sm text-on-surface">Where people breathe it. This is what we detect and verify.</p>
                       </div>
                     </motion.div>
                  </motion.div>
               </div>
            </div>
          </div>
        </InView>
      </div>
    </section>
  );
}
