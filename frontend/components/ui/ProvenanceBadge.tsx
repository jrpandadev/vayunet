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

  let icon = <ShieldCheck className="w-3.5 h-3.5 text-[#E8F4FD]" />;
  let label = source;
  let badgeStyle = 'bg-[rgba(255,255,255,0.05)] text-[#E8F4FD] border-[rgba(255,255,255,0.1)]';

  if (normalized.includes('cpcb') || normalized.includes('dpcc') || normalized.includes('mpcb') || normalized.includes('ospcb')) {
    icon = <ShieldCheck className="w-3.5 h-3.5 text-[#E8F4FD]" />;
    label = 'CPCB Certified';
    badgeStyle = 'bg-[rgba(255,255,255,0.05)] text-[#E8F4FD] border-[rgba(255,255,255,0.1)] font-medium';
  } else if (normalized.includes('sentinel') || normalized.includes('satellite')) {
    icon = <Orbit className="w-3.5 h-3.5 text-[#00E5FF]" />;
    label = 'Sentinel-5P Satellite';
    badgeStyle = 'bg-[rgba(0,213,255,0.08)] text-[#00E5FF] border-[rgba(0,213,255,0.2)] font-medium';
  } else if (normalized.includes('citizen')) {
    icon = <Users className="w-3.5 h-3.5 text-[#7BA4BC]" />;
    label = 'Citizen Crowdsource';
    badgeStyle = 'bg-[rgba(255,255,255,0.02)] text-[#7BA4BC] border-[rgba(255,255,255,0.1)] font-medium';
  } else if (normalized.includes('weather') || normalized.includes('open_meteo')) {
    icon = <Wind className="w-3.5 h-3.5 text-[#00E5FF]" />;
    label = 'Weather Grid';
    badgeStyle = 'bg-[rgba(0,213,255,0.05)] text-[#E8F4FD] border-[rgba(0,213,255,0.15)] font-medium';
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
