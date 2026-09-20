import React from 'react';
import { ShieldCheck, Orbit, Users, Wind } from 'lucide-react';

export type ProvenanceSource = 'CPCB' | 'Sentinel-5P' | 'citizen' | 'Citizen' | 'weather' | 'Weather' | 'open_meteo';

interface ProvenanceBadgeProps {
  source: string;
  qualityOrFreshness?: string;
  className?: string;
}

export const ProvenanceBadge: React.FC<ProvenanceBadgeProps> = ({
  source,
  qualityOrFreshness,
  className = '',
}) => {
  const normalized = source.toLowerCase();

  let icon = <ShieldCheck className="w-3.5 h-3.5 text-[#0a2540]" />;
  let label = source;
  let badgeStyle = 'bg-slate-100 text-[#0a2540] border-[#0a2540]/30';

  if (normalized.includes('cpcb') || normalized.includes('dpcc') || normalized.includes('mpcb') || normalized.includes('ospcb')) {
    icon = <ShieldCheck className="w-3.5 h-3.5 text-[#0a2540]" />;
    label = 'CPCB Certified';
    badgeStyle = 'bg-slate-100 text-[#0a2540] border-slate-300 font-medium';
  } else if (normalized.includes('sentinel') || normalized.includes('satellite')) {
    icon = <Orbit className="w-3.5 h-3.5 text-[#0284c7]" />;
    label = 'Sentinel-5P Satellite';
    badgeStyle = 'bg-sky-50 text-[#0369a1] border-sky-200 font-medium';
  } else if (normalized.includes('citizen')) {
    icon = <Users className="w-3.5 h-3.5 text-slate-600" />;
    label = 'Citizen Crowdsource';
    badgeStyle = 'bg-slate-50 text-slate-700 border-slate-200 font-medium';
  } else if (normalized.includes('weather') || normalized.includes('open_meteo')) {
    icon = <Wind className="w-3.5 h-3.5 text-cyan-700" />;
    label = 'Weather Grid';
    badgeStyle = 'bg-cyan-50 text-cyan-800 border-cyan-200 font-medium';
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs border ${badgeStyle} ${className}`}
      title={`Data Provenance: ${label}${qualityOrFreshness ? ` (${qualityOrFreshness})` : ''}`}
    >
      {icon}
      <span>{label}</span>
      {qualityOrFreshness && (
        <span className="text-[10px] uppercase opacity-75 font-mono">
          • {qualityOrFreshness}
        </span>
      )}
    </span>
  );
};

export default ProvenanceBadge;
