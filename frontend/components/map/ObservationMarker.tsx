'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { CitizenObservation } from '@/lib/observations';
import {
  Camera,
  MapPin,
  Clock,
  Wind,
  ShieldAlert,
  ArrowRight,
  ExternalLink,
  X,
  Eye,
  ImageOff,
} from 'lucide-react';

interface ObservationMarkerProps {
  observation: CitizenObservation;
  onSelect?: (id: string) => void;
}

// Generates a dedicated, professional camera SVG/CSS marker
function createCameraIcon(observation: CitizenObservation) {
  const size = 34;
  const containerSize = 44;

  const cameraSvg = `
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"></path>
      <circle cx="12" cy="13" r="3"></circle>
    </svg>
  `;

  const html = `
    <div style="
      position: relative;
      width: ${containerSize}px;
      height: ${containerSize}px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
    " title="Citizen Observation: ${observation.locationName}">
      <!-- Outer Evidence Halo Ring (Neutral/Deep oceanic cyan indicating citizen evidence source, not risk) -->
      <div style="
        position: absolute;
        width: ${size + 8}px;
        height: ${size + 8}px;
        border-radius: 50%;
        background-color: rgba(2, 132, 199, 0.22);
        border: 1.5px solid rgba(56, 189, 248, 0.5);
      "></div>

      <!-- Core Camera Pin Capsule -->
      <div style="
        position: relative;
        z-index: 2;
        width: ${size}px;
        height: ${size}px;
        border-radius: 50%;
        background: radial-gradient(circle at 35% 35%, #0284c7 0%, #0369a1 55%, #0a2540 100%);
        border: 2px solid #ffffff;
        box-shadow: 0 3px 8px rgba(10, 37, 64, 0.45);
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        ${cameraSvg}
      </div>

      <!-- Micro Evidence Badge -->
      <div style="
        position: absolute;
        bottom: 2px;
        right: 2px;
        z-index: 3;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background-color: #38bdf8;
        border: 1.5px solid #ffffff;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
      "></div>
    </div>
  `;

  return L.divIcon({
    className: 'vayu-observation-pin',
    html,
    iconSize: [containerSize, containerSize],
    iconAnchor: [containerSize / 2, containerSize / 2],
    popupAnchor: [0, -containerSize / 2 + 4],
  });
}

export const ObservationMarker: React.FC<ObservationMarkerProps> = ({
  observation,
  onSelect,
}) => {
  const icon = React.useMemo(() => createCameraIcon(observation), [observation]);
  const [modalOpen, setModalOpen] = useState<boolean>(false);

  return (
    <>
      <Marker
        position={[observation.latitude, observation.longitude]}
        icon={icon}
        eventHandlers={{
          click: () => {
            if (onSelect) {
              onSelect(observation.id);
            }
          },
        }}
      >
        <Popup
          className="vayu-leaflet-popup"
          minWidth={285}
          maxWidth={345}
          autoPan={true}
          autoPanPaddingTopLeft={[50, 75]}
          autoPanPaddingBottomRight={[50, 55]}
        >
          <div className="p-1 select-none font-sans text-slate-800">
            {/* Header */}
            <div className="flex items-start justify-between gap-2 pb-2 border-b border-slate-100 mb-2">
              <div>
                <div className="flex items-center gap-1.5 font-bold text-xs uppercase tracking-wider text-slate-900">
                  <Camera className="w-3.5 h-3.5 text-sky-600" />
                  <span>FIELD OBSERVATION</span>
                </div>
                <div className="flex items-center gap-1 mt-0.5">
                  <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded">
                    {observation.id}
                  </span>
                  <span className="text-[10px] font-semibold text-sky-800 bg-sky-50 px-1.5 py-0.2 rounded border border-sky-200">
                    Citizen Observation (Simulation)
                  </span>
                </div>
              </div>

              {/* Prototype Simulation Notice */}
              <span className="text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-200 shrink-0">
                Prototype simulation data
              </span>
            </div>

            {/* Image Preview Box */}
            <div className="mb-2.5">
              {observation.image ? (
                <div className="relative rounded-lg overflow-hidden border border-slate-200 bg-slate-950 group">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={observation.image}
                    alt={`Citizen observation at ${observation.locationName}: ${observation.description || 'photo evidence'}`}
                    className="w-full h-36 object-cover transition-transform duration-200 group-hover:scale-105 cursor-pointer"
                    onClick={() => setModalOpen(true)}
                    loading="lazy"
                  />
                  <button
                    type="button"
                    onClick={() => setModalOpen(true)}
                    className="absolute bottom-2 right-2 px-2 py-1 bg-slate-900/80 hover:bg-slate-900 text-white text-[10px] font-semibold rounded backdrop-blur-xs flex items-center gap-1 transition-all cursor-pointer shadow-xs"
                    title="Click to enlarge observation photograph"
                    aria-label="Enlarge image"
                  >
                    <Eye className="w-3 h-3" />
                    <span>Enlarge</span>
                  </button>
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-1 min-h-[90px]">
                  <ImageOff className="w-5 h-5 text-slate-400" />
                  <span className="font-medium text-slate-500 text-[11px]">
                    Image preview unavailable
                  </span>
                  <span className="text-[10px] text-slate-400">
                    No photograph attached to this report
                  </span>
                </div>
              )}
            </div>

            {/* Location & Time Attributes */}
            <div className="space-y-1.5 text-xs mb-2.5 bg-slate-50/90 p-2.5 rounded-lg border border-slate-200">
              {/* Location */}
              <div>
                <span className="text-[10px] font-semibold uppercase text-slate-500 block mb-0.5">
                  Location
                </span>
                <div className="flex items-start gap-1 text-slate-900 font-medium">
                  <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5" />
                  <span>{observation.locationName}</span>
                </div>
                <span className="text-[10px] font-mono text-slate-400 ml-4.5 block">
                  {observation.latitude.toFixed(4)}°N, {observation.longitude.toFixed(4)}°E
                </span>
              </div>

              {/* Upload Time */}
              <div className="pt-1 border-t border-slate-200/60 flex items-center justify-between text-[11px]">
                <span className="text-slate-500 flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-400" />
                  <span>Uploaded:</span>
                </span>
                <span className="font-mono font-medium text-slate-800">
                  {observation.uploadedAt} (Simulation)
                </span>
              </div>

              {/* PM2.5 at Location (Clearly separated from model forecast) */}
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-500 flex items-center gap-1">
                  <Wind className="w-3 h-3 text-sky-600" />
                  <span>PM2.5 at location:</span>
                </span>
                <span className="font-mono font-bold text-slate-900">
                  {observation.pm25AtLocation} µg/m³
                </span>
              </div>
            </div>

            {/* Citizen Description (if available) */}
            {observation.description && (
              <div className="p-2 rounded-lg bg-white border border-slate-200/80 mb-2.5 text-xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-0.5">
                  Description
                </span>
                <p className="text-slate-700 italic text-[11px] leading-relaxed">
                  &ldquo;{observation.description}&rdquo;
                </p>
              </div>
            )}

            {/* Evidence Source & Model Relationship Breakdown */}
            <div className="p-2 rounded-lg bg-sky-50/70 border border-sky-200/80 mb-2 text-xs space-y-1">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-600">Source:</span>
                <span className="font-semibold text-sky-950">
                  Citizen-submitted evidence (simulation)
                </span>
              </div>

              <div className="flex items-center justify-between text-[11px] pt-1 border-t border-sky-200/50">
                <span className="text-slate-600">Related model event:</span>
                {observation.relatedEventId ? (
                  <span className="font-mono font-bold text-[#0a2540] bg-white px-1.5 py-0.2 rounded border border-sky-300">
                    {observation.relatedEventId}
                  </span>
                ) : (
                  <span className="text-slate-500 italic">
                    Model relationship: Not established
                  </span>
                )}
              </div>
            </div>

            {/* SPA Navigation Link to Related Event Dossier (using Next.js Link) */}
            {observation.relatedEventId && (
              <Link
                href={`/dashboard/event?id=${observation.relatedEventId}`}
                className="inline-flex items-center justify-center gap-1.5 w-full py-1.5 px-3 bg-[#0a2540] hover:bg-[#0f2a3f] text-white text-xs font-semibold rounded transition-colors"
                title={`Inspect correlated incident dossier ${observation.relatedEventId}`}
              >
                <span>View Related Event Dossier</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            )}
          </div>
        </Popup>
      </Marker>

      {/* Enlarged Modal Image Preview (SPA Dialog without page refresh) */}
      {modalOpen && observation.image && (
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4 animate-in fade-in"
          onClick={() => setModalOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Enlarged Observation Photograph"
        >
          <div
            className="relative bg-slate-900 border border-slate-700 rounded-xl overflow-hidden max-w-2xl w-full shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between p-3.5 border-b border-slate-800 bg-slate-900/90">
              <div className="flex items-center gap-2">
                <Camera className="w-4 h-4 text-sky-400" />
                <span className="font-bold text-xs text-white uppercase tracking-wider">
                  Field Evidence Snapshot • {observation.locationName}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
                aria-label="Close enlarged preview"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Image */}
            <div className="relative bg-black flex items-center justify-center max-h-[70vh] overflow-hidden">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={observation.image}
                alt={observation.description || observation.locationName}
                className="w-full max-h-[70vh] object-contain"
              />
            </div>

            {/* Modal Footer */}
            <div className="p-3.5 bg-slate-900 text-xs text-slate-300 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800">
              <span className="text-[11px] font-mono text-slate-400">
                Uploaded: {observation.uploadedAt} • PM2.5: {observation.pm25AtLocation} µg/m³
              </span>
              <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-amber-900/40 text-amber-300 border border-amber-800/80">
                Prototype simulation data
              </span>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default ObservationMarker;
