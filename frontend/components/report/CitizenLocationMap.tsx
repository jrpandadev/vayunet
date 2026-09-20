'use client';

import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import { MapPin, Crosshair } from 'lucide-react';

interface CitizenLocationMapProps {
  lat: number;
  lng: number;
  onLocationChange: (lat: number, lng: number) => void;
  helperText?: string;
  className?: string;
}

// Custom location pin
const locationPin = L.divIcon({
  className: 'citizen-location-pin',
  html: `
    <div style="
      position: relative;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
    ">
      <div style="
        position: absolute;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background-color: #0284c7;
        opacity: 0.25;
        border: 2px solid #0284c7;
      "></div>
      <div style="
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background-color: #0a2540;
        border: 3px solid #ffffff;
        box-shadow: 0 2px 6px rgba(10, 37, 64, 0.5);
      "></div>
    </div>
  `,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

// Map click listener
function MapClickHandler({ onLocationChange }: { onLocationChange: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) {
      onLocationChange(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// Auto-center helper when coordinates change externally
function MapCenterUpdater({ lat, lng }: { lat: number, lng: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lng], map.getZoom() || 14);
  }, [lat, lng, map]);
  return null;
}

export const CitizenLocationMap: React.FC<CitizenLocationMapProps> = ({
  lat,
  lng,
  onLocationChange,
  helperText,
  className = '',
}) => {
  return (
    <div className={`relative w-full h-56 rounded-lg overflow-hidden border border-slate-200 shadow-inner ${className}`}>
      <MapContainer
        center={[lat, lng]}
        zoom={14}
        scrollWheelZoom={false}
        className="w-full h-full"
        style={{ width: '100%', height: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        <MapCenterUpdater lat={lat} lng={lng} />
        <MapClickHandler onLocationChange={onLocationChange} />

        <Marker
          position={[lat, lng]}
          icon={locationPin}
          draggable={true}
          eventHandlers={{
            dragend: (e) => {
              const marker = e.target;
              const pos = marker.getLatLng();
              onLocationChange(pos.lat, pos.lng);
            },
          }}
        />
      </MapContainer>

      {/* Helper badge overlaid on mini-map */}
      <div className="absolute bottom-2 left-2 z-[1000] bg-white/90 backdrop-blur-xs px-2.5 py-1 rounded border border-slate-200 text-[10px] text-slate-600 font-medium flex items-center gap-1 shadow-xs pointer-events-none">
        <Crosshair className="w-3 h-3 text-[#0a2540]" />
        <span>{helperText || 'Click map or drag pin to adjust spot'}</span>
      </div>
    </div>
  );
};

export default CitizenLocationMap;
