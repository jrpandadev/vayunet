export default function AnomalyCatalog() {
  return (
    <section className="py-20 bg-surface-container-lowest border-b border-surface-variant">
      <div className="container mx-auto px-gutter-mobile md:px-gutter">
        <h3 className="text-headline-md text-on-surface mb-8 border-b border-surface-variant pb-4">Actively Monitored Event Signatures</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Card 1 */}
          <div className="bg-surface-container rounded-xl p-6 border border-surface-variant hover:border-error transition-colors group">
             <div className="w-12 h-12 rounded-full bg-error/10 flex items-center justify-center mb-4 group-hover:bg-error/20 transition-colors">
                <span className="material-symbols-outlined text-error">local_fire_department</span>
             </div>
             <h4 className="text-headline-sm text-on-surface mb-2">Agricultural Fires</h4>
             <p className="text-body-sm text-on-surface-variant mb-4">Post-harvest stubble burning creating massive, fast-moving PM2.5 and Black Carbon plumes.</p>
             <div className="flex gap-2">
                <span className="px-2 py-1 bg-surface-variant rounded text-label-sm text-on-surface">TROPOMI Aerosol</span>
                <span className="px-2 py-1 bg-surface-variant rounded text-label-sm text-on-surface">VIIRS Fire</span>
             </div>
          </div>

          {/* Card 2 */}
          <div className="bg-surface-container rounded-xl p-6 border border-surface-variant hover:border-tertiary transition-colors group">
             <div className="w-12 h-12 rounded-full bg-tertiary/10 flex items-center justify-center mb-4 group-hover:bg-tertiary/20 transition-colors">
                <span className="material-symbols-outlined text-tertiary">factory</span>
             </div>
             <h4 className="text-headline-sm text-on-surface mb-2">Industrial Emissions</h4>
             <p className="text-body-sm text-on-surface-variant mb-4">Continuous or accidental point-source release of NO2, SO2, and toxic VOCs.</p>
             <div className="flex gap-2 flex-wrap">
                <span className="px-2 py-1 bg-surface-variant rounded text-label-sm text-on-surface">TROPOMI NO2</span>
                <span className="px-2 py-1 bg-surface-variant rounded text-label-sm text-on-surface">Citizen Odor</span>
             </div>
          </div>

          {/* Card 3 */}
          <div className="bg-surface-container rounded-xl p-6 border border-surface-variant hover:border-primary transition-colors group">
             <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                <span className="material-symbols-outlined text-primary">air</span>
             </div>
             <h4 className="text-headline-sm text-on-surface mb-2">Dust & Sand Storms</h4>
             <p className="text-body-sm text-on-surface-variant mb-4">Synoptic-scale transport of coarse particulate matter (PM10) driven by meteorology.</p>
             <div className="flex gap-2">
                <span className="px-2 py-1 bg-surface-variant rounded text-label-sm text-on-surface">AOD</span>
                <span className="px-2 py-1 bg-surface-variant rounded text-label-sm text-on-surface">Wind Vectors</span>
             </div>
          </div>

          {/* Card 4 */}
          <div className="bg-surface-container rounded-xl p-6 border border-surface-variant hover:border-secondary transition-colors group">
             <div className="w-12 h-12 rounded-full bg-secondary/10 flex items-center justify-center mb-4 group-hover:bg-secondary/20 transition-colors">
                <span className="material-symbols-outlined text-secondary">commute</span>
             </div>
             <h4 className="text-headline-sm text-on-surface mb-2">Urban Congestion</h4>
             <p className="text-body-sm text-on-surface-variant mb-4">Micro-level spikes in tailpipe emissions trapping ground-level ozone and CO.</p>
             <div className="flex gap-2">
                <span className="px-2 py-1 bg-surface-variant rounded text-label-sm text-on-surface">CPCB Ground</span>
                <span className="px-2 py-1 bg-surface-variant rounded text-label-sm text-on-surface">TROPOMI CO</span>
             </div>
          </div>
        </div>
      </div>
    </section>
  );
}
