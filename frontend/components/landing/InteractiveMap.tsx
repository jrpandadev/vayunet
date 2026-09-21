'use client';

import { useState } from 'react';

export default function InteractiveMap() {
  const [activeLayer, setActiveLayer] = useState<'all' | 'sat' | 'ground' | 'wind'>('all');

  const getLayerOpacity = (layer: string) => {
    if (activeLayer === 'all') return 1;
    return activeLayer === layer ? 1 : 0.1;
  };

  const getButtonClass = (layer: string) => {
    const base = "px-3 py-1.5 rounded-md text-label-sm font-medium transition-colors border";
    return activeLayer === layer
      ? `${base} bg-surface-variant text-on-surface border-outline`
      : `${base} bg-transparent text-on-surface-variant border-outline-variant hover:bg-surface-container-highest`;
  };

  return (
    <section className="py-20 border-b border-surface-variant" id="concept">
      <div className="container mx-auto px-gutter-mobile md:px-gutter">
        <div className="mb-12 text-center">
          <h2 className="text-headline-lg text-on-surface mb-4">The Live Topology of Air</h2>
          <p className="text-body-lg text-on-surface-variant max-w-2xl mx-auto">
            A dynamic composite of India's atmosphere, rendering invisible threats visible.
          </p>
        </div>

        <div className="bg-surface-container rounded-xl border border-surface-variant overflow-hidden flex flex-col relative h-[600px]">
          {/* Map Controls */}
          <div className="absolute top-4 left-4 z-20 bg-surface-container-highest/90 backdrop-blur border border-surface-variant p-2 rounded-lg flex flex-col gap-2">
            <span className="text-label-sm text-on-surface-variant uppercase tracking-widest px-1">Observation Layers</span>
            <div className="flex gap-2">
              <button onClick={() => setActiveLayer('all')} className={getButtonClass('all')}>All Nodes</button>
              <button onClick={() => setActiveLayer('sat')} className={getButtonClass('sat')}>Satellite Only</button>
              <button onClick={() => setActiveLayer('ground')} className={getButtonClass('ground')}>Ground Only</button>
              <button onClick={() => setActiveLayer('wind')} className={getButtonClass('wind')}>Wind Vectors</button>
            </div>
          </div>

          {/* Interactive SVG Map rendering */}
          <div className="absolute inset-0 bg-[#080e19] flex items-center justify-center p-8">
             <svg viewBox="0 0 800 600" className="w-full h-full max-w-4xl opacity-90 drop-shadow-2xl">
                {/* Base Map Outline (Simplified India India) */}
                <path d="M 250,50 L 350,20 L 450,80 L 500,50 L 600,100 L 700,200 L 650,300 L 550,450 L 400,550 L 250,400 L 150,250 L 100,200 Z" fill="#161c27" stroke="#2f3541" strokeWidth="2" strokeLinejoin="round" />

                {/* Layer: Wind Vectors */}
                <g style={{ opacity: getLayerOpacity('wind'), transition: 'opacity 0.3s' }}>
                  {/* Wind lines mimicking transport corridors */}
                  <path d="M 150,150 Q 300,200 450,300" stroke="#03b5d3" strokeWidth="1" fill="none" strokeDasharray="4 4" className="opacity-30" />
                  <path d="M 200,100 Q 400,150 600,250" stroke="#03b5d3" strokeWidth="1" fill="none" strokeDasharray="4 4" className="opacity-30" />
                  <path d="M 100,250 Q 250,350 400,450" stroke="#03b5d3" strokeWidth="1" fill="none" strokeDasharray="4 4" className="opacity-30" />
                  <path d="M 300,50 Q 450,100 650,200" stroke="#03b5d3" strokeWidth="1" fill="none" strokeDasharray="4 4" className="opacity-30" />
                </g>

                {/* Layer: Satellite Plumes (TROPOMI) */}
                <g style={{ opacity: getLayerOpacity('sat'), transition: 'opacity 0.3s' }}>
                  {/* Punjab Fire Plume */}
                  <ellipse cx="280" cy="120" rx="60" ry="30" fill="url(#plume-grad-red)" transform="rotate(-15 280 120)" className="opacity-60" />
                  <ellipse cx="320" cy="130" rx="80" ry="40" fill="url(#plume-grad-red)" transform="rotate(-10 320 130)" className="opacity-40" />

                  {/* IGP Dust Plume */}
                  <ellipse cx="450" cy="180" rx="100" ry="50" fill="url(#plume-grad-orange)" transform="rotate(10 450 180)" className="opacity-50" />

                  {/* Mumbai Coastal NO2 */}
                  <ellipse cx="200" cy="320" rx="50" ry="30" fill="url(#plume-grad-blue)" transform="rotate(45 200 320)" className="opacity-60" />
                </g>

                {/* Layer: Ground Truth (Sensors & Citizens) */}
                <g style={{ opacity: getLayerOpacity('ground'), transition: 'opacity 0.3s' }}>
                  {/* CPCB Stations (Diamonds) */}
                  <rect x="275" y="115" width="10" height="10" fill="#ffffff" stroke="#000" strokeWidth="1" transform="rotate(45 280 120)" />
                  <rect x="315" y="145" width="10" height="10" fill="#ffffff" stroke="#000" strokeWidth="1" transform="rotate(45 320 150)" />
                  <rect x="425" y="165" width="10" height="10" fill="#ffffff" stroke="#000" strokeWidth="1" transform="rotate(45 430 170)" />
                  <rect x="195" y="315" width="10" height="10" fill="#ffffff" stroke="#000" strokeWidth="1" transform="rotate(45 200 320)" />

                  {/* Citizen Reports (Pulsing Dots) */}
                  <circle cx="290" cy="135" r="4" fill="#4edea3" className="animate-pulse" />
                  <circle cx="270" cy="110" r="4" fill="#4edea3" className="animate-pulse" style={{ animationDelay: '0.5s' }} />
                  <circle cx="450" cy="190" r="4" fill="#ffb95f" className="animate-pulse" style={{ animationDelay: '1s' }} />
                  <circle cx="210" cy="330" r="4" fill="#4cd7f6" className="animate-pulse" style={{ animationDelay: '0.2s' }} />
                </g>

                <defs>
                  <radialGradient id="plume-grad-red">
                    <stop offset="0%" stopColor="#ffb4ab" stopOpacity="0.8" />
                    <stop offset="100%" stopColor="#93000a" stopOpacity="0" />
                  </radialGradient>
                  <radialGradient id="plume-grad-orange">
                    <stop offset="0%" stopColor="#ffb95f" stopOpacity="0.7" />
                    <stop offset="100%" stopColor="#653e00" stopOpacity="0" />
                  </radialGradient>
                  <radialGradient id="plume-grad-blue">
                    <stop offset="0%" stopColor="#4cd7f6" stopOpacity="0.8" />
                    <stop offset="100%" stopColor="#003640" stopOpacity="0" />
                  </radialGradient>
                </defs>
             </svg>
          </div>

          {/* Legend */}
          <div className="absolute bottom-4 right-4 bg-surface-container-highest/90 backdrop-blur p-4 rounded-lg border border-surface-variant">
            <h4 className="text-label-sm text-on-surface mb-2">Legend</h4>
            <div className="flex flex-col gap-2">
               <div className="flex items-center gap-2">
                 <div className="w-3 h-3 rotate-45 bg-surface border border-outline"></div>
                 <span className="text-label-sm text-on-surface-variant">CPCB Sensor</span>
               </div>
               <div className="flex items-center gap-2">
                 <div className="w-3 h-3 rounded-full bg-primary animate-pulse"></div>
                 <span className="text-label-sm text-on-surface-variant">Citizen Report</span>
               </div>
               <div className="flex items-center gap-2">
                 <div className="w-3 h-2 rounded-full bg-gradient-to-r from-error to-transparent"></div>
                 <span className="text-label-sm text-on-surface-variant">Satellite Plume</span>
               </div>
               <div className="flex items-center gap-2">
                 <div className="w-3 border-t border-dashed border-secondary"></div>
                 <span className="text-label-sm text-on-surface-variant">Wind Vector</span>
               </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
