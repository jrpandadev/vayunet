'use client';

import { useState } from 'react';

export default function EventExplorer() {
  const [activeTab, setActiveTab] = useState<'punjab' | 'mumbai' | 'odisha' | 'igp'>('punjab');

  const getTabClass = (tab: string) => {
    return activeTab === tab
      ? "px-4 py-2 bg-surface text-primary border-b-2 border-primary font-medium"
      : "px-4 py-2 bg-transparent text-on-surface-variant border-b-2 border-transparent hover:text-on-surface transition-colors";
  };

  return (
    <section className="py-24 border-b border-surface-variant bg-surface-container-lowest" id="explorer">
      <div className="container mx-auto px-gutter-mobile md:px-gutter">
        <h2 className="text-display-xl-mobile md:text-display-xl text-on-surface mb-4 text-center">Inside the Engine</h2>
        <p className="text-body-lg text-on-surface-variant max-w-2xl mx-auto mb-12 text-center">
          Explore how VayuNet correlates disparate datasets to build high-confidence event dossiers. <br/><span className="text-sm mt-2 block text-primary uppercase tracking-widest font-bold">Conceptual Demonstration</span>
        </p>

        <div className="bg-surface rounded-2xl border border-surface-variant overflow-hidden flex flex-col md:flex-row min-h-[500px]">
          {/* Sidebar / Tabs */}
          <div className="md:w-1/3 border-r border-surface-variant bg-surface-container flex flex-row md:flex-col overflow-x-auto md:overflow-visible">
            <button onClick={() => setActiveTab('punjab')} className={getTabClass('punjab')} style={{ textAlign: 'left' }}>
               <span className="text-label-sm uppercase tracking-widest block mb-1">Stubble Burning</span>
               <span className="text-body-md block">Punjab / Haryana</span>
            </button>
            <button onClick={() => setActiveTab('mumbai')} className={getTabClass('mumbai')} style={{ textAlign: 'left' }}>
               <span className="text-label-sm uppercase tracking-widest block mb-1">Industrial Emission</span>
               <span className="text-body-md block">Mumbai Coastal Zone</span>
            </button>
            <button onClick={() => setActiveTab('odisha')} className={getTabClass('odisha')} style={{ textAlign: 'left' }}>
               <span className="text-label-sm uppercase tracking-widest block mb-1">Mining Dust</span>
               <span className="text-body-md block">Odisha Coal Belt</span>
            </button>
            <button onClick={() => setActiveTab('igp')} className={getTabClass('igp')} style={{ textAlign: 'left' }}>
               <span className="text-label-sm uppercase tracking-widest block mb-1">Winter Smog</span>
               <span className="text-body-md block">Indo-Gangetic Plain</span>
            </button>
          </div>

          {/* Content Area */}
          <div className="md:w-2/3 p-8 relative overflow-hidden bg-[#080e19]">
            {activeTab === 'punjab' && (
              <div className="animate-fade-in z-10 relative">
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h3 className="text-headline-md text-error mb-2">Multi-State Agricultural Fire Event</h3>
                    <p className="text-body-sm text-on-surface-variant">October 15, 14:00 IST</p>
                  </div>
                  <div className="px-3 py-1 bg-error/20 border border-error/50 rounded-full text-error text-label-sm">
                    98% Confidence
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="p-4 bg-surface-container rounded-lg border border-surface-variant flex gap-4">
                     <span className="material-symbols-outlined text-error">satellite_alt</span>
                     <div>
                       <span className="text-label-sm text-on-surface block mb-1">TROPOMI & VIIRS</span>
                       <span className="text-body-sm text-on-surface-variant">Thermal anomaly detected with elevated aerosol signal.</span>
                     </div>
                  </div>
                  <div className="p-4 bg-surface-container rounded-lg border border-surface-variant flex gap-4">
                     <span className="material-symbols-outlined text-secondary">air</span>
                     <div>
                       <span className="text-label-sm text-on-surface block mb-1">GFS Wind Vectors</span>
                       <span className="text-body-sm text-on-surface-variant">Wind transport context transporting plume directly towards Delhi NCR.</span>
                     </div>
                  </div>
                  <div className="p-4 bg-surface-container rounded-lg border border-surface-variant flex gap-4">
                     <span className="material-symbols-outlined text-primary">person_pin</span>
                     <div>
                       <span className="text-label-sm text-on-surface block mb-1">Citizen Ground-Truth</span>
                       <span className="text-body-sm text-on-surface-variant">14 localized reports with photo evidence of active burning in Sangrur district.</span>
                     </div>
                  </div>
                </div>
                <div className="mt-8 pt-4 border-t border-surface-variant flex items-center justify-between">
                   <span className="text-body-sm text-on-surface">Outcome:</span>
                   <span className="text-body-sm text-on-surface-variant">Automated evidentiary dossier routed to Punjab PCB. Preventive alert sent to Delhi.</span>
                </div>
              </div>
            )}

            {activeTab === 'mumbai' && (
              <div className="animate-fade-in z-10 relative">
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h3 className="text-headline-md text-tertiary mb-2">Unreported Industrial Flaring</h3>
                    <p className="text-body-sm text-on-surface-variant">April 22, 02:00 IST</p>
                  </div>
                  <div className="px-3 py-1 bg-tertiary/20 border border-tertiary/50 rounded-full text-tertiary text-label-sm">
                    92% Confidence
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="p-4 bg-surface-container rounded-lg border border-surface-variant flex gap-4">
                     <span className="material-symbols-outlined text-tertiary">co2</span>
                     <div>
                       <span className="text-label-sm text-on-surface block mb-1">TROPOMI NO2</span>
                       <span className="text-body-sm text-on-surface-variant">Nighttime pass reveals dense NO2 plume off the coast, originating inland.</span>
                     </div>
                  </div>
                  <div className="p-4 bg-surface-container rounded-lg border border-surface-variant flex gap-4">
                     <span className="material-symbols-outlined text-secondary">sensors</span>
                     <div>
                       <span className="text-label-sm text-on-surface block mb-1">Regulatory Ground Sensor</span>
                       <span className="text-body-sm text-on-surface-variant">Simultaneous spike in target pollution signal.</span>
                     </div>
                  </div>
                  <div className="p-4 bg-surface-container rounded-lg border border-surface-variant flex gap-4">
                     <span className="material-symbols-outlined text-primary">forum</span>
                     <div>
                       <span className="text-label-sm text-on-surface block mb-1">Social Listening</span>
                       <span className="text-body-sm text-on-surface-variant">Cluster of "chemical odor" complaints logged via NLP on social streams.</span>
                     </div>
                  </div>
                </div>
                <div className="mt-8 pt-4 border-t border-surface-variant flex items-center justify-between">
                   <span className="text-body-sm text-on-surface">Outcome:</span>
                   <span className="text-body-sm text-on-surface-variant">Anomaly pinpointed to petrochemical facility operating outside permitted hours.</span>
                </div>
              </div>
            )}

            {activeTab === 'odisha' && (
              <div className="animate-fade-in z-10 relative">
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h3 className="text-headline-md text-primary mb-2">Fugitive Mining Dust Plume</h3>
                    <p className="text-body-sm text-on-surface-variant">May 10, 11:30 IST</p>
                  </div>
                  <div className="px-3 py-1 bg-primary/20 border border-primary/50 rounded-full text-primary text-label-sm">
                    88% Confidence
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="p-4 bg-surface-container rounded-lg border border-surface-variant flex gap-4">
                     <span className="material-symbols-outlined text-primary">blur_on</span>
                     <div>
                       <span className="text-label-sm text-on-surface block mb-1">Aerosol Optical Depth (AOD)</span>
                       <span className="text-body-sm text-on-surface-variant">Dense particulate layer (Elevated AOD signal) expanding from Talcher coalfields.</span>
                     </div>
                  </div>
                  <div className="p-4 bg-surface-container rounded-lg border border-surface-variant flex gap-4">
                     <span className="material-symbols-outlined text-secondary">wb_sunny</span>
                     <div>
                       <span className="text-label-sm text-on-surface block mb-1">Meteorology</span>
                       <span className="text-body-sm text-on-surface-variant">Warm atmospheric conditions and low humidity triggering massive surface dust lofting.</span>
                     </div>
                  </div>
                </div>
                <div className="mt-8 pt-4 border-t border-surface-variant flex items-center justify-between">
                   <span className="text-body-sm text-on-surface">Outcome:</span>
                   <span className="text-body-sm text-on-surface-variant">Mandated water-sprinkling directives issued to mining operators in the grid.</span>
                </div>
              </div>
            )}

            {activeTab === 'igp' && (
              <div className="animate-fade-in z-10 relative">
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h3 className="text-headline-md text-on-surface mb-2">Basin-Wide Inversion Layer</h3>
                    <p className="text-body-sm text-on-surface-variant">December 20, 08:00 IST</p>
                  </div>
                  <div className="px-3 py-1 bg-surface-variant border border-outline rounded-full text-on-surface text-label-sm">
                    100% Confidence
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="p-4 bg-surface-container rounded-lg border border-surface-variant flex gap-4">
                     <span className="material-symbols-outlined text-on-surface">thermostat</span>
                     <div>
                       <span className="text-label-sm text-on-surface block mb-1">Thermal Inversion</span>
                       <span className="text-body-sm text-on-surface-variant">PBL height dropped to &lt;200m, trapping all basin emissions.</span>
                     </div>
                  </div>
                  <div className="p-4 bg-surface-container rounded-lg border border-surface-variant flex gap-4">
                     <span className="material-symbols-outlined text-error">warning</span>
                     <div>
                       <span className="text-label-sm text-on-surface block mb-1">Regional Accumulation</span>
                       <span className="text-body-sm text-on-surface-variant">Urban tailpipe + biomass + industrial emissions pooling across 1000km.</span>
                     </div>
                  </div>
                </div>
                <div className="mt-8 pt-4 border-t border-surface-variant flex items-center justify-between">
                   <span className="text-body-sm text-on-surface">Outcome:</span>
                   <span className="text-body-sm text-on-surface-variant">Triggered GRAP (Graded Response Action Plan) Stage IV across Delhi-NCR.</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
