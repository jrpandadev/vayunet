import React from 'react';
import { EventTimelineItem } from '@/lib/types';
import { Clock } from 'lucide-react';

interface TimelineProps {
  items: EventTimelineItem[];
  className?: string;
}

function formatEventName(eventName: string): string {
  if (eventName === 'alert_sent') {
    return 'Alert Routed to Authority';
  }
  return eventName
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function getEventBadgeColor(eventName: string): { dot: string; text: string } {
  const lower = eventName.toLowerCase();
  if (lower.includes('critical') || lower.includes('alert_sent')) {
    return { dot: 'bg-[#ef4444]', text: 'text-rose-900 font-semibold' };
  }
  if (lower.includes('high')) {
    return { dot: 'bg-[#f97316]', text: 'text-orange-900 font-semibold' };
  }
  if (lower.includes('gemini') || lower.includes('satellite')) {
    return { dot: 'bg-[#0284c7]', text: 'text-slate-800' };
  }
  if (lower.includes('citizen')) {
    return { dot: 'bg-emerald-600', text: 'text-slate-800' };
  }
  return { dot: 'bg-[#0a2540]', text: 'text-slate-700' };
}

export const Timeline: React.FC<TimelineProps> = ({ items, className = '' }) => {
  if (!items || items.length === 0) {
    return (
      <div className="py-4 text-center text-xs text-[#64748b]">
        No timeline entries recorded.
      </div>
    );
  }

  return (
    <div className={`relative pl-4 border-l-2 border-slate-200 space-y-6 ${className}`}>
      {items.map((item, index) => {
        const { dot, text } = getEventBadgeColor(item.event);
        return (
          <div key={index} className="relative group">
            {/* Timeline node dot */}
            <div
              className={`absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full ring-4 ring-white ${dot}`}
              aria-hidden="true"
            />

            <div className="flex items-baseline justify-between gap-4">
              <span className={`text-sm ${text}`}>
                {formatEventName(item.event)}
              </span>
              <span className="inline-flex items-center gap-1 text-xs text-[#64748b] font-mono tabular-telemetry shrink-0">
                <Clock className="w-3 h-3 text-slate-400" />
                {item.time}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default Timeline;
