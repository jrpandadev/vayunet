export default function LiveStatusStrip() {
  return (
    <div className="w-full border-b border-surface-variant bg-surface-container-low overflow-hidden flex items-center h-12 relative">
      <div className="absolute left-0 top-0 bottom-0 w-24 bg-gradient-to-r from-surface-container-low to-transparent z-10"></div>
      <div className="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-surface-container-low to-transparent z-10"></div>

      <div className="flex gap-12 px-12 animate-sweep items-center">
        <div className="flex items-center gap-2 text-label-md text-on-surface-variant">
          <span className="w-1.5 h-1.5 rounded-full bg-error animate-pulse"></span>
          <span>Punjab: Crop Burning Detected</span>
          <span className="text-error font-telemetry-metric ml-2">Satellite Evidence</span>
        </div>
        <div className="flex items-center gap-2 text-label-md text-on-surface-variant">
          <span className="w-1.5 h-1.5 rounded-full bg-tertiary"></span>
          <span>Mumbai: Industrial Emission Verified</span>
          <span className="text-tertiary font-telemetry-metric ml-2">Atmospheric Signal</span>
        </div>
        <div className="flex items-center gap-2 text-label-md text-on-surface-variant">
          <span className="w-1.5 h-1.5 rounded-full bg-primary"></span>
          <span>Odisha: Dust Plume Monitored</span>
          <span className="text-primary font-telemetry-metric ml-2">ML Forecast Trajectory</span>
        </div>
        <div className="flex items-center gap-2 text-label-md text-on-surface-variant">
           <span className="material-symbols-outlined text-sm">satellite_alt</span>
           <span>Sentinel-5P Pass Completed 14 mins ago</span>
        </div>
        <div className="flex items-center gap-2 text-label-md text-on-surface-variant">
           <span className="material-symbols-outlined text-sm">group</span>
           <span>1,244 Active Citizen Observers</span>
        </div>
        <div className="flex items-center gap-2 text-label-md text-on-surface-variant">
           <span className="px-2 py-0.5 bg-surface-variant rounded-full text-[10px] uppercase tracking-wider text-on-surface">Conceptual visualization — not live measurements</span>
        </div>
      </div>
    </div>
  );
}
