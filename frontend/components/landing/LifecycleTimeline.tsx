export default function LifecycleTimeline() {
  return (
    <section className="py-24 border-b border-surface-variant bg-surface">
      <div className="container mx-auto px-gutter-mobile md:px-gutter">
        <h2 className="text-headline-lg text-on-surface mb-12 text-center">The Operational Lifecycle</h2>

        <div className="relative max-w-5xl mx-auto">
           {/* Timeline track */}
           <div className="absolute left-4 md:left-1/2 top-0 bottom-0 w-0.5 bg-surface-variant -translate-x-1/2"></div>

           {/* Step 1 */}
           <div className="relative flex flex-col md:flex-row items-center gap-8 mb-16">
             <div className="md:w-1/2 md:text-right flex flex-col md:items-end pl-12 md:pl-0">
                <h4 className="text-headline-sm text-primary mb-2">1. Autonomous Detection</h4>
                <p className="text-body-sm text-on-surface-variant">The AI engine constantly scans incoming data streams for statistical anomalies and threshold breaches.</p>
             </div>
             <div className="absolute left-4 md:left-1/2 w-8 h-8 rounded-full bg-surface border-2 border-primary -translate-x-1/2 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-primary"></div>
             </div>
             <div className="md:w-1/2 hidden md:block"></div>
           </div>

           {/* Step 2 */}
           <div className="relative flex flex-col md:flex-row-reverse items-center gap-8 mb-16">
             <div className="md:w-1/2 flex flex-col items-start pl-12 md:pl-0">
                <h4 className="text-headline-sm text-secondary mb-2">2. Multimodal Verification</h4>
                <p className="text-body-sm text-on-surface-variant">A satellite anomaly triggers a localized ground-sensor query and alerts nearby citizen observers for photographic evidence.</p>
             </div>
             <div className="absolute left-4 md:left-1/2 w-8 h-8 rounded-full bg-surface border-2 border-secondary -translate-x-1/2 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-secondary"></div>
             </div>
             <div className="md:w-1/2 hidden md:block"></div>
           </div>

           {/* Step 3 */}
           <div className="relative flex flex-col md:flex-row items-center gap-8 mb-16">
             <div className="md:w-1/2 md:text-right flex flex-col md:items-end pl-12 md:pl-0">
                <h4 className="text-headline-sm text-tertiary mb-2">3. Source Apportionment (AI)</h4>
                <p className="text-body-sm text-on-surface-variant">Gemini Vision processes citizen photos and correlates them with wind data to trace the plume back to its physical origin.</p>
             </div>
             <div className="absolute left-4 md:left-1/2 w-8 h-8 rounded-full bg-surface border-2 border-tertiary -translate-x-1/2 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-tertiary"></div>
             </div>
             <div className="md:w-1/2 hidden md:block"></div>
           </div>

           {/* Step 4 */}
           <div className="relative flex flex-col md:flex-row-reverse items-center gap-8 mb-16">
             <div className="md:w-1/2 flex flex-col items-start pl-12 md:pl-0">
                <h4 className="text-headline-sm text-error mb-2">4. Triangulated Alerting</h4>
                <p className="text-body-sm text-on-surface-variant">Once confidence exceeds 85%, highly-targeted alerts are dispatched to affected populations downwind of the source.</p>
             </div>
             <div className="absolute left-4 md:left-1/2 w-8 h-8 rounded-full bg-surface border-2 border-error -translate-x-1/2 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-error"></div>
             </div>
             <div className="md:w-1/2 hidden md:block"></div>
           </div>

           {/* Step 5 */}
           <div className="relative flex flex-col md:flex-row items-center gap-8 mb-16">
             <div className="md:w-1/2 md:text-right flex flex-col md:items-end pl-12 md:pl-0">
                <h4 className="text-headline-sm text-on-surface mb-2">5. Authoritative Action</h4>
                <p className="text-body-sm text-on-surface-variant">State pollution control boards receive a complete, tamper-proof evidentiary dossier to enforce compliance.</p>
             </div>
             <div className="absolute left-4 md:left-1/2 w-8 h-8 rounded-full bg-surface border-2 border-on-surface -translate-x-1/2 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-on-surface"></div>
             </div>
             <div className="md:w-1/2 hidden md:block"></div>
           </div>

           {/* Step 6 */}
           <div className="relative flex flex-col md:flex-row-reverse items-center gap-8">
             <div className="md:w-1/2 flex flex-col items-start pl-12 md:pl-0">
                <h4 className="text-headline-sm text-primary mb-2">6. Model Retraining</h4>
                <p className="text-body-sm text-on-surface-variant">The final resolution and intervention data is fed back into the system, continuously improving the physical transport models.</p>
             </div>
             <div className="absolute left-4 md:left-1/2 w-8 h-8 rounded-full bg-surface border-2 border-primary -translate-x-1/2 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-primary"></div>
             </div>
             <div className="md:w-1/2 hidden md:block"></div>
           </div>
        </div>
      </div>
    </section>
  );
}
