'use client';

import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Filter, RotateCcw, X, ChevronDown, ChevronUp } from 'lucide-react';

export interface MapFilterState {
  city: string;
  risk: string;
  timeRange: string;
}

interface MapFilterProps {
  cities: string[];
  filterState: MapFilterState;
  onFilterChange: (newState: Partial<MapFilterState>) => void;
  onReset: () => void;
  filteredCount: number;
  totalCount: number;
  className?: string;
  defaultExpanded?: boolean;
  selectedEventId?: string | null;
}

interface FilterSelectsProps {
  cities: string[];
  filterState: MapFilterState;
  onFilterChange: (newState: Partial<MapFilterState>) => void;
  idPrefix?: string;
  isMobile?: boolean;
}

const FilterSelects: React.FC<FilterSelectsProps> = ({
  cities,
  filterState,
  onFilterChange,
  idPrefix = '',
  isMobile = false,
}) => {
  const selectClasses = isMobile
    ? 'w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2.5 text-sm text-slate-900 font-medium focus:outline-hidden focus:ring-2 focus:ring-[#0a2540] focus:border-[#0a2540] min-h-[44px] cursor-pointer'
    : 'w-full bg-slate-50 border border-slate-300 rounded px-2.5 py-1.5 text-xs text-slate-900 font-medium focus:outline-hidden focus:ring-1 focus:ring-[#0a2540] focus:border-[#0a2540] cursor-pointer';

  const labelClasses = isMobile
    ? 'block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5'
    : 'block text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-1';

  return (
    <>
      {/* City Filter */}
      <div className="min-w-0">
        <label
          htmlFor={`${idPrefix}filter-city`}
          className={labelClasses}
        >
          Air Basin / City
        </label>
        <select
          id={`${idPrefix}filter-city`}
          value={filterState.city}
          onChange={(e) => onFilterChange({ city: e.target.value })}
          className={selectClasses}
        >
          <option value="ALL">All Monitored Cities</option>
          {cities.map((city) => (
            <option key={city} value={city}>
              {city}
            </option>
          ))}
        </select>
      </div>

      {/* Risk Category Filter */}
      <div className="min-w-0">
        <label
          htmlFor={`${idPrefix}filter-risk`}
          className={labelClasses}
        >
          Risk Category
        </label>
        <select
          id={`${idPrefix}filter-risk`}
          value={filterState.risk}
          onChange={(e) => onFilterChange({ risk: e.target.value })}
          className={selectClasses}
        >
          <option value="ALL">All Risk Levels</option>
          <option value="CRITICAL">Critical Alerts Only</option>
          <option value="HIGH">High Risk</option>
          <option value="MODERATE">Moderate Exposure</option>
          <option value="LOW">Low Impact</option>
        </select>
      </div>

      {/* Observation Window Filter */}
      <div className="min-w-0">
        <label
          htmlFor={`${idPrefix}filter-time`}
          className={labelClasses}
        >
          Observation Window
        </label>
        <select
          id={`${idPrefix}filter-time`}
          value={filterState.timeRange}
          onChange={(e) => onFilterChange({ timeRange: e.target.value })}
          className={selectClasses}
        >
          <option value="ALL">All Ingested Records</option>
          <option value="24H">Past 24 Hours</option>
          <option value="48H">Past 48 Hours</option>
          <option value="7D">Past 7 Days</option>
        </select>
      </div>
    </>
  );
};

export const MapFilter: React.FC<MapFilterProps> = ({
  cities,
  filterState,
  onFilterChange,
  onReset,
  filteredCount,
  totalCount,
  className = '',
  defaultExpanded = false,
  selectedEventId,
}) => {
  const [mobileOpen, setMobileOpen] = useState<boolean>(false);
  const [desktopExpanded, setDesktopExpanded] = useState<boolean>(defaultExpanded);
  const [mounted, setMounted] = useState<boolean>(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Auto-minimize desktop filter when an event or hotspot is selected to ensure popup is unobstructed
  useEffect(() => {
    if (selectedEventId) {
      setDesktopExpanded(false);
    }
  }, [selectedEventId]);

  // Lock background scrolling while mobile bottom sheet is open
  useEffect(() => {
    if (mobileOpen) {
      const originalStyle = window.getComputedStyle(document.body).overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = originalStyle;
      };
    }
  }, [mobileOpen]);

  // Handle escape key to close mobile bottom sheet
  useEffect(() => {
    if (!mobileOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMobileOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [mobileOpen]);

  const isFiltered =
    filterState.city !== 'ALL' ||
    filterState.risk !== 'ALL' ||
    filterState.timeRange !== 'ALL';

  return (
    <>
      {/* DESKTOP COLLAPSED TRIGGER: Compact "Filters" control with current site count */}
      {!desktopExpanded && (
        <div className="hidden sm:block">
          <button
            type="button"
            onClick={() => setDesktopExpanded(true)}
            className="inline-flex items-center gap-2 bg-white/95 backdrop-blur-md border border-slate-300/90 text-[#0a2540] font-semibold text-xs px-3.5 py-2 rounded-lg shadow-md hover:bg-white hover:border-slate-400 active:scale-95 transition-all cursor-pointer select-none"
            aria-label="Expand surveillance filters"
            aria-expanded={false}
          >
            <Filter className="w-3.5 h-3.5 text-[#0a2540]" />
            <span>Filters</span>
            <span className="text-slate-300">•</span>
            <span className="font-mono text-slate-700 bg-slate-100 px-2 py-0.5 rounded text-[11px] border border-slate-200">
              {filteredCount} {filteredCount === 1 ? 'site' : 'sites'}
            </span>
            {isFiltered && (
              <span
                className="w-2 h-2 rounded-full bg-sky-500 ring-2 ring-white"
                title="Active filters applied"
              />
            )}
            <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
          </button>
        </div>
      )}

      {/* DESKTOP EXPANDED FILTER PANEL: Visible when expanded on sm screens and up (640px+) */}
      {desktopExpanded && (
        <div
          className={`hidden sm:block bg-white/95 backdrop-blur-md border border-slate-300/90 rounded-lg p-3.5 shadow-xl text-xs select-none max-w-lg w-full ${className}`}
        >
          <div className="flex items-center justify-between gap-3 pb-2.5 border-b border-slate-100 mb-3">
            <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[#0a2540]">
              <Filter className="w-3.5 h-3.5 text-[#0a2540]" />
              <span>Surveillance Filters</span>
              {isFiltered && (
                <span className="text-[10px] font-semibold text-sky-700 bg-sky-50 px-1.5 py-0.5 rounded border border-sky-200">
                  Active
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                Showing {filteredCount} of {totalCount} Sites
              </span>
              <button
                type="button"
                onClick={() => setDesktopExpanded(false)}
                className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                title="Collapse filters"
                aria-label="Collapse surveillance filters"
              >
                <ChevronUp className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <FilterSelects
              cities={cities}
              filterState={filterState}
              onFilterChange={onFilterChange}
              idPrefix="desktop-"
              isMobile={false}
            />
          </div>

          <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between">
            <button
              type="button"
              onClick={onReset}
              className="inline-flex items-center gap-1 text-[11px] text-slate-600 hover:text-[#0a2540] font-semibold transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset All Filters</span>
            </button>
            <div className="flex items-center gap-2.5">
              <span className="text-[10px] text-slate-400 font-mono">
                OpenStreetMap Spatial Grid
              </span>
              <button
                type="button"
                onClick={() => setDesktopExpanded(false)}
                className="inline-flex items-center gap-1 text-[11px] text-slate-600 hover:text-[#0a2540] font-semibold px-2 py-0.5 rounded hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <span>Collapse</span>
                <ChevronUp className="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MOBILE TRIGGER CONTROL: Visible only below sm screens (<640px) */}
      <div className="sm:hidden">
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="inline-flex items-center gap-2 bg-white/95 backdrop-blur-md border border-slate-200 text-[#0a2540] font-semibold text-xs px-3.5 py-2.5 rounded-lg shadow-md hover:bg-white active:scale-95 transition-all cursor-pointer select-none"
          aria-label="Open surveillance filters"
          aria-expanded={mobileOpen}
        >
          <Filter className="w-3.5 h-3.5 text-[#0a2540]" />
          <span>
            Filters · {filteredCount} {filteredCount === 1 ? 'site' : 'sites'}
          </span>
          {isFiltered && (
            <span
              className="w-2 h-2 rounded-full bg-sky-500 ring-2 ring-white"
              title="Active filters applied"
            />
          )}
        </button>
      </div>

      {/* MOBILE BOTTOM SHEET DRAWER: Rendered in Portal to prevent clipping */}
      {mounted &&
        mobileOpen &&
        createPortal(
          <div className="sm:hidden fixed inset-0 z-[1200] flex flex-col justify-end pointer-events-none">
            {/* Backdrop: dim background and dismiss on tap */}
            <div
              className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs pointer-events-auto transition-opacity"
              onClick={() => setMobileOpen(false)}
              aria-label="Close filters backdrop"
            />

            {/* Bottom Sheet Modal Container */}
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="mobile-filter-title"
              className="relative pointer-events-auto w-full max-w-lg mx-auto bg-white rounded-t-2xl shadow-2xl border-t border-slate-200 flex flex-col max-h-[82vh] overflow-hidden"
            >
              {/* Drag Handle Bar */}
              <div className="pt-2.5 pb-1 flex justify-center">
                <div className="w-10 h-1 bg-slate-300 rounded-full" />
              </div>

              {/* Header with Title, Count Badge, and Close Button */}
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <Filter className="w-4 h-4 text-[#0a2540]" />
                  <h2
                    id="mobile-filter-title"
                    className="font-bold text-xs uppercase tracking-wider text-[#0a2540]"
                  >
                    Surveillance Filters
                  </h2>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-mono font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                    Showing {filteredCount} of {totalCount} Sites
                  </span>
                  <button
                    type="button"
                    onClick={() => setMobileOpen(false)}
                    className="p-1.5 -mr-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 active:bg-slate-200 transition-colors cursor-pointer"
                    aria-label="Close filters"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Filter Controls Body */}
              <div className="px-4 py-4 space-y-3.5 overflow-y-auto flex-1 overscroll-contain">
                <FilterSelects
                  cities={cities}
                  filterState={filterState}
                  onFilterChange={onFilterChange}
                  idPrefix="mobile-"
                  isMobile={true}
                />
              </div>

              {/* Action Footer */}
              <div className="px-4 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={onReset}
                  className="inline-flex items-center gap-1.5 text-xs text-slate-600 hover:text-[#0a2540] font-semibold py-2 px-2.5 rounded-lg active:bg-slate-200 transition-colors cursor-pointer min-h-[44px]"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Reset All Filters</span>
                </button>

                <button
                  type="button"
                  onClick={() => setMobileOpen(false)}
                  className="bg-[#0a2540] text-white px-5 py-2.5 rounded-lg text-xs font-semibold hover:bg-[#0f3456] active:scale-95 transition-all shadow-xs cursor-pointer min-h-[44px] flex items-center justify-center"
                >
                  Apply & View Map ({filteredCount})
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}
    </>
  );
};

export default MapFilter;
