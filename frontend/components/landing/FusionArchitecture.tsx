export default function FusionArchitecture() {
  return (
    <section className="py-24 border-b border-surface-variant bg-surface-container-lowest">
      <div className="container mx-auto px-gutter-mobile md:px-gutter text-center">
        <h2 className="text-display-xl-mobile md:text-display-xl text-on-surface mb-6">Multi-Modal Ingestion Core</h2>
        <p className="text-body-lg text-on-surface-variant max-w-3xl mx-auto mb-16">
          No single sensor can see the whole picture. VayuNet continuously ingests and cross-references data from four independent pillars of observation to eliminate false positives.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {/* Satellite */}
          <div className="flex flex-col items-center p-6 bg-surface-container rounded-2xl border border-surface-variant hover:border-primary transition-colors">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-6">
               <span className="material-symbols-outlined text-3xl text-primary">satellite_alt</span>
            </div>
            <h4 className="text-headline-md text-on-surface mb-2">Spaceborne Telemetry</h4>
            <p className="text-body-sm text-on-surface-variant text-center">Copernicus Sentinel-5P (TROPOMI) and VIIRS providing daily macro-scale gas column densities and thermal anomalies.</p>
          </div>

          {/* Ground */}
          <div className="flex flex-col items-center p-6 bg-surface-container rounded-2xl border border-surface-variant hover:border-secondary transition-colors">
            <div className="w-16 h-16 rounded-full bg-secondary/10 flex items-center justify-center mb-6">
               <span className="material-symbols-outlined text-3xl text-secondary">sensors</span>
            </div>
            <h4 className="text-headline-md text-on-surface mb-2">Authoritative Ground</h4>
            <p className="text-body-sm text-on-surface-variant text-center">Continuous micro-scale ingestion from CPCB continuous ambient air quality monitoring stations (CAAQMS).</p>
          </div>

          {/* Meteorology */}
          <div className="flex flex-col items-center p-6 bg-surface-container rounded-2xl border border-surface-variant hover:border-tertiary transition-colors">
            <div className="w-16 h-16 rounded-full bg-tertiary/10 flex items-center justify-center mb-6">
               <span className="material-symbols-outlined text-3xl text-tertiary">air</span>
            </div>
            <h4 className="text-headline-md text-on-surface mb-2">Meteorological Physics</h4>
            <p className="text-body-sm text-on-surface-variant text-center">GFS and ECMWF assimilation for planetary boundary layer height, U/V wind vectors, and transport modeling.</p>
          </div>

          {/* Citizen */}
          <div className="flex flex-col items-center p-6 bg-surface-container rounded-2xl border border-surface-variant hover:border-error transition-colors">
            <div className="w-16 h-16 rounded-full bg-error/10 flex items-center justify-center mb-6">
               <span className="material-symbols-outlined text-3xl text-error">group</span>
            </div>
            <h4 className="text-headline-md text-on-surface mb-2">Citizen Ground-Truth</h4>
            <p className="text-body-sm text-on-surface-variant text-center">Hyper-local human observation capturing visual plumes, odors, and physiological impacts undetectable by satellites.</p>
          </div>
        </div>
      </div>
    </section>
  );
}
