'use client';

import React from 'react';
import { Polygon, Popup, Tooltip } from 'react-leaflet';
import L from 'leaflet';
import {
  RiskZone,
  MOCK_RISK_ZONES,
  RISK_ZONE_HEX,
  RISK_ZONE_BASE_OPACITY,
} from '@/lib/riskZones';
import RiskBadge from '@/components/ui/RiskBadge';
import { Layers, TrendingUp, AlertTriangle } from 'lucide-react';

interface RiskZoneLayerProps {
  zones?: RiskZone[];
  onSelectZone?: (id: string) => void;
}

export const RiskZoneLayer: React.FC<RiskZoneLayerProps> = ({
  zones = MOCK_RISK_ZONES,
  onSelectZone,
}) => {
  return (
    <>
      {zones.map((zone) => {
        const color = RISK_ZONE_HEX[zone.level] || RISK_ZONE_HEX.MODERATE;
        const baseFillOpacity = RISK_ZONE_BASE_OPACITY[zone.level] || 0.18;

        // Interactive hover opacity is capped at 0.28 so the zone remains clearly
        // semi-transparent at all times and never obscures street names, highways, or markers.
        const hoverFillOpacity = Math.min(baseFillOpacity + 0.05, 0.28);

        return (
          <Polygon
            key={zone.id}
            positions={zone.coordinates}
            pathOptions={{
              color: color,
              weight: 1.5,
              opacity: 0.75,
              dashArray: '5 5',
              fillColor: color,
              fillOpacity: baseFillOpacity,
            }}
            eventHandlers={{
              mouseover: (e) => {
                const layer = e.target;
                layer.setStyle({
                  weight: 2.0,
                  opacity: 0.95,
                  fillOpacity: hoverFillOpacity,
                });
              },
              mouseout: (e) => {
                const layer = e.target;
                layer.setStyle({
                  weight: 1.5,
                  opacity: 0.75,
                  fillOpacity: baseFillOpacity,
                });
              },
              click: (e) => {
                // Explicitly anchor popup at zone centroid for predictable, safe viewport framing
                if (e.target.getPopup()) {
                  e.target.getPopup().setLatLng(zone.center);
                }
                e.target.openPopup(zone.center);
                if (onSelectZone) {
                  onSelectZone(zone.id);
                }
              },
            }}
          >
            {/* Sticky Cursor Tooltip with Risk Tier & Predicted Value */}
            <Tooltip
              sticky
              direction="center"
              className="vayu-risk-zone-tooltip"
              opacity={0.95}
            >
              <div className="text-xs font-sans px-1 py-0.5">
                <span className="font-bold uppercase tracking-wider" style={{ color }}>
                  {zone.level.replace('_', ' ')}
                </span>
                <span className="text-slate-700 font-mono ml-1.5 font-semibold">
                  PM2.5: {zone.predicted_pm25} µg/m³
                </span>
              </div>
            </Tooltip>

            {/* Click Popup Card - Limited strictly to approved Step 4 schema fields */}
            <Popup
              className="vayu-leaflet-popup"
              minWidth={280}
              maxWidth={330}
              autoPan={true}
              autoPanPaddingTopLeft={[50, 85]}
              autoPanPaddingBottomRight={[50, 60]}
            >
              <div className="p-1 select-none font-sans text-slate-800">
                {/* 1. Header: Predicted/Simulation Status & Zone Identifier */}
                <div className="flex items-start justify-between gap-2 pb-2 border-b border-slate-100 mb-2">
                  <div>
                    <div className="flex items-center gap-1.5 font-bold text-xs uppercase tracking-wider text-slate-900">
                      <Layers className="w-3.5 h-3.5" style={{ color }} />
                      <span>PM2.5 RISK ZONE</span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded mt-0.5 inline-block">
                      {zone.id}
                    </span>
                  </div>

                  <span className="text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-200 shrink-0">
                    Simulation Zone
                  </span>
                </div>

                {/* 2. Zone Name & Predicted Risk Badge */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h4 className="text-xs font-bold text-slate-900 leading-snug">
                    {zone.name}
                  </h4>
                  <RiskBadge level={zone.level as any} size="sm" />
                </div>

                {/* 3. PM2.5 Forecast Metric Box: Predicted PM2.5, Forecast Uncertainty, Horizon & Confidence */}
                <div className="mb-2.5 p-2 rounded-lg bg-sky-50/80 border border-dashed border-sky-300">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-sky-950">
                      <TrendingUp className="w-3 h-3 text-sky-700" />
                      PM2.5 Forecast
                    </span>
                    <span className="text-[10px] font-mono text-sky-800 bg-sky-100/90 px-1.5 py-0.2 rounded font-semibold">
                      {zone.forecast_horizon}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-1.5 text-xs">
                    <div className="bg-white/90 p-2 rounded border border-sky-200">
                      <span className="text-[10px] text-slate-500 block">Predicted PM2.5</span>
                      <span className="font-mono font-bold text-slate-900 text-sm">
                        {zone.predicted_pm25} µg/m³
                      </span>
                    </div>

                    <div className="bg-white/90 p-2 rounded border border-sky-200">
                      <span className="text-[10px] text-slate-500 block">Forecast Uncertainty</span>
                      <span className="font-mono font-bold text-xs text-sky-900">
                        {zone.forecast_uncertainty}
                      </span>
                    </div>
                  </div>

                  <div className="mt-1.5 pt-1 border-t border-sky-200/60 flex items-center justify-between text-[10px] text-sky-900 font-mono">
                    <span>Forecast Horizon: {zone.forecast_horizon}</span>
                    <span>Confidence: {zone.prediction_confidence}%</span>
                  </div>
                </div>

                {/* 4. Mandatory Prototype Simulation Disclaimer Banner */}
                <div className="p-2 rounded-md bg-amber-50/90 border border-amber-200 text-amber-900 flex items-start gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-700 shrink-0 mt-0.5" />
                  <p className="text-[10px] leading-tight font-medium">
                    {zone.simulation_disclaimer}
                  </p>
                </div>
              </div>
            </Popup>
          </Polygon>
        );
      })}
    </>
  );
};

export default RiskZoneLayer;
