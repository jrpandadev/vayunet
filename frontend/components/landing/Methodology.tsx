export default function Methodology() {
  return (
    <section className="py-24 border-b border-surface-variant bg-surface" id="methodology">
      <div className="container mx-auto px-gutter-mobile md:px-gutter">
        <div className="flex flex-col lg:flex-row gap-16">
           <div className="lg:w-1/2">
             <h2 className="text-headline-lg text-on-surface mb-6">Scientific Rigor. <br/>Algorithmic Integrity.</h2>
             <p className="text-body-lg text-on-surface-variant mb-6">
               VayuNet does not guess. If an event cannot be mathematically triangulated using physical parameters, it is flagged as low-confidence. We rely on established meteorological and atmospheric science APIs.
             </p>
             <ul className="space-y-4 mb-8">
               <li className="flex items-start gap-3">
                 <span className="material-symbols-outlined text-primary mt-0.5">check_circle</span>
                 <span className="text-body-sm text-on-surface-variant"><strong>ESA Copernicus (Sentinel-5P):</strong> Direct ingestion of Level-2 NetCDF files for tropospheric NO2, SO2, CO, and Aerosol Index.</span>
               </li>
               <li className="flex items-start gap-3">
                 <span className="material-symbols-outlined text-primary mt-0.5">check_circle</span>
                 <span className="text-body-sm text-on-surface-variant"><strong>NOAA / NCEP (GFS):</strong> 0.25-degree resolution meteorological assimilation for accurate wind transport modeling.</span>
               </li>
               <li className="flex items-start gap-3">
                 <span className="material-symbols-outlined text-primary mt-0.5">check_circle</span>
                 <span className="text-body-sm text-on-surface-variant"><strong>Google Gemini:</strong> Zero-shot classification of citizen imagery and semantic parsing of social listening streams.</span>
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
                 </div>
                 <div className="p-4 text-on-surface-variant bg-[#080e19] max-h-80 overflow-y-auto">
<pre className="whitespace-pre-wrap font-label-md leading-relaxed text-[11px] md:text-xs text-[#a0aabf]">
<span className="text-primary">[INFO]</span> 2026-09-12T14:22:01Z - Ingesting Sentinel-5P L2_AER_AI data...
<span className="text-primary">[INFO]</span> 2026-09-12T14:22:05Z - Anomaly detected: Lat 30.2, Lon 75.8 (Punjab). AI &gt; 3.5
<span className="text-primary">[INFO]</span> 2026-09-12T14:22:10Z - Fetching GFS wind vectors for bounding box...
<span className="text-primary">[INFO]</span> 2026-09-12T14:22:15Z - Wind: 290° at 4.2 m/s. Projecting transport trajectory.
<span className="text-tertiary">[WARN]</span> 2026-09-12T14:22:16Z - Trajectory intersects Delhi NCT within 18 hours.
<span className="text-primary">[INFO]</span> 2026-09-12T14:22:20Z - Querying citizen evidence DB for spatial intersection...
<span className="text-primary">[INFO]</span> 2026-09-12T14:22:22Z - 3 valid images found. Running Gemini Vision analysis...
<span className="text-primary">[INFO]</span> 2026-09-12T14:22:28Z - Vision Analysis: "Extensive crop residue burning in fields. High confidence."
<span className="text-error">[ALERT]</span> 2026-09-12T14:22:30Z - EVENT VERIFIED. Confidence: 98%. Generating evidentiary dossier.
<span className="text-error">[ALERT]</span> 2026-09-12T14:22:35Z - Dossier dispatched to CPCB Node (ID: PJB-04).
</pre>
                 </div>
              </div>
           </div>
        </div>
      </div>
    </section>
  );
}
