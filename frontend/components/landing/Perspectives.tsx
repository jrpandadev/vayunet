export default function Perspectives() {
  return (
    <section className="py-24 border-b border-surface-variant bg-surface">
      <div className="container mx-auto px-gutter-mobile md:px-gutter">
        <h2 className="text-headline-lg text-on-surface mb-12 text-center">Built for the Entire Ecosystem</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
           <div className="bg-surface-container-low p-8 rounded-2xl border border-surface-variant">
              <span className="material-symbols-outlined text-4xl text-primary mb-6">psychology</span>
              <h4 className="text-headline-md text-on-surface mb-4">For the Citizen</h4>
              <p className="text-body-sm text-on-surface-variant mb-6">
                Understand what you are breathing, where it's coming from, and submit photographic evidence that directly triggers regulatory action.
              </p>
           </div>

           <div className="bg-surface-container-low p-8 rounded-2xl border border-surface-variant">
              <span className="material-symbols-outlined text-4xl text-secondary mb-6">insights</span>
              <h4 className="text-headline-md text-on-surface mb-4">For the Analyst</h4>
              <p className="text-body-sm text-on-surface-variant mb-6">
                Access a unified dashboard fusing TROPOMI Level-2 products, GFS physics, and CPCB telemetry without writing complex geospatial pipelines.
              </p>
           </div>

           <div className="bg-surface-container-low p-8 rounded-2xl border border-surface-variant">
              <span className="material-symbols-outlined text-4xl text-error mb-6">gavel</span>
              <h4 className="text-headline-md text-on-surface mb-4">For the Authority</h4>
              <p className="text-body-sm text-on-surface-variant mb-6">
                Receive high-confidence, AI-verified event dossiers with source apportionment, ready for legal and administrative compliance enforcement.
              </p>
           </div>
        </div>
      </div>
    </section>
  );
}
