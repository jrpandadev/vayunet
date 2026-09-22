'use client';

import React, { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getEventById, updateEventAction } from '@/lib/api';
import { PollutionEvent, AuthorityAction } from '@/lib/types';
import DashboardHeader from '@/components/layout/DashboardHeader';
import RiskBadge from '@/components/ui/RiskBadge';
import ProvenanceBadge from '@/components/ui/ProvenanceBadge';
import Card, { CardHeader, CardContent } from '@/components/ui/Card';
import Timeline from '@/components/ui/Timeline';
import ExplanationBox from '@/components/evidence/ExplanationBox';
import ConfidenceGauge from '@/components/evidence/ConfidenceGauge';
import MiniForecastChart from '@/components/forecast/MiniForecastChart';
import AIModelPanel from '@/components/ai/AIModelPanel';
import {
  CitizenEvidenceCard,
  SensorEvidenceCard,
  SatelliteEvidenceCard,
  WeatherEvidenceCard,
} from '@/components/evidence/EvidenceCard';
import {
  ArrowLeft,
  MapPin,
  Clock,
  ShieldAlert,
  CheckCircle2,
  Search,
  XCircle,
  AlertCircle,
  Building2,
  FileCheck2,
  Sparkles,
} from 'lucide-react';

import { Suspense } from 'react';

function EventDetailContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const eventId = searchParams?.get('id') as string;

  const [event, setEvent] = useState<PollutionEvent | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionInProgress, setActionInProgress] = useState<boolean>(false);
  const [actionFeedback, setActionFeedback] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);
  const [fromAlerts, setFromAlerts] = useState<boolean>(false);
  const [returnToAlertsUrl, setReturnToAlertsUrl] = useState<string>('/dashboard/alerts');

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const searchParams = new URLSearchParams(window.location.search);
    if (searchParams.get('from') === 'alerts') {
      setFromAlerts(true);
      const tab = searchParams.get('tab');
      const q = searchParams.get('q');
      const queryParams = new URLSearchParams();
      if (tab) queryParams.set('tab', tab);
      if (q) queryParams.set('q', q);
      const queryStr = queryParams.toString();
      setReturnToAlertsUrl(queryStr ? `/dashboard/alerts?${queryStr}` : '/dashboard/alerts');
    }
  }, []);

  useEffect(() => {
    let mounted = true;

    async function loadEvent() {
      if (!eventId) return;
      setLoading(true);
      try {
        const data = await getEventById(eventId);
        if (mounted) {
          setEvent(data);
        }
      } catch (err) {
        console.error('Failed to load event:', err);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadEvent();

    return () => {
      mounted = false;
    };
  }, [eventId]);

  const handleAuthorityAction = async (action: AuthorityAction) => {
    if (!event) return;
    setActionInProgress(true);
    setActionFeedback(null);

    try {
      const result = await updateEventAction(event.event_id, action);
      if (result.success) {
        setEvent(result.event);
        setActionFeedback({
          type: 'success',
          message: `Authority action "${action.toUpperCase()}" registered successfully${result.isSimulation ? ' (Simulation Mode)' : ''}.`,
        });
      }
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Action failed';
      setActionFeedback({
        type: 'error',
        message: `Failed to record authority action: ${errorMsg}`,
      });
    } finally {
      setActionInProgress(false);
    }
  };

  // Loading State
  if (loading) {
    return (
      <div className="flex flex-col min-h-screen bg-[#03111F]">
        <DashboardHeader
          title="Incident Surveillance"
          subtitle="Loading telemetry and multi-source evidence..."
        />
        <div className="flex-1 flex flex-col items-center justify-center p-12 text-[#7BA4BC]">
          <div className="h-8 w-8 border-3 border-[#00E5FF] border-t-transparent rounded-full animate-spin mb-4 shadow-[0_0_15px_rgba(0,229,255,0.5)]" />
          <p className="text-sm font-medium animate-pulse">Synthesizing evidence for incident {eventId}...</p>
        </div>
      </div>
    );
  }

  // Not Found State
  if (!event) {
    return (
      <div className="flex flex-col min-h-screen bg-[#03111F]">
        <DashboardHeader
          title="Incident Not Found"
          subtitle="The requested pollution event could not be retrieved from the catalog."
        />
        <div className="flex-1 flex flex-col items-center justify-center p-12">
          <div className="bg-[rgba(6,24,39,0.80)] border border-[rgba(255,68,68,0.25)] rounded-lg p-8 max-w-md w-full text-center shadow-lg shadow-black/40">
            <div className="h-12 w-12 rounded-full bg-[rgba(255,68,68,0.08)] text-[#FF7070] flex items-center justify-center mx-auto mb-4 border border-[rgba(255,68,68,0.25)]">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-bold text-[#E8F4FD]">
              Pollution Event Not Found
            </h2>
            <p className="text-xs text-[#7BA4BC] mt-2 mb-6">
              Event identifier &ldquo;{eventId}&rdquo; does not exist in the active monitoring catalog or mock dataset.
            </p>
            {fromAlerts ? (
              <button
                type="button"
                onClick={() => {
                  if (typeof window !== 'undefined' && window.history.length > 1) {
                    router.back();
                  } else {
                    router.push(returnToAlertsUrl);
                  }
                }}
                className="inline-flex items-center justify-center gap-2 w-full py-2.5 px-4 bg-gradient-to-r from-[#0066CC] to-[#004A99] hover:from-[#0077EE] hover:to-[#0055BB] text-white text-xs font-semibold rounded transition-colors cursor-pointer border border-[rgba(0,150,255,0.30)]"
              >
                <ArrowLeft className="w-4 h-4" />
                Return to Alert Centre
              </button>
            ) : (
              <Link
                href="/dashboard"
                className="inline-flex items-center justify-center gap-2 w-full py-2.5 px-4 bg-gradient-to-r from-[#0066CC] to-[#004A99] hover:from-[#0077EE] hover:to-[#0055BB] text-white text-xs font-semibold rounded transition-colors border border-[rgba(0,150,255,0.30)]"
              >
                <ArrowLeft className="w-4 h-4" />
                Return to Authority Overview
              </Link>
            )}
          </div>
        </div>
      </div>
    );
  }

  const supporting = event.detection.supporting_evidence || [];
  const contradicting = event.detection.contradicting_evidence || [];

  const isCitizenSupporting = supporting.some((s) => s.includes('citizen'));
  const isCitizenContradicting = contradicting.some((c) => c.includes('citizen'));

  const isSensorSupporting = supporting.some((s) => s.includes('sensor'));
  const isSensorContradicting = contradicting.some((c) => c.includes('sensor'));

  const isSatelliteSupporting = supporting.some((s) => s.includes('satellite'));
  const isSatelliteContradicting = contradicting.some((c) => c.includes('satellite'));

  const isWeatherSupporting = supporting.some((s) => s.includes('weather'));
  const isWeatherContradicting = contradicting.some((c) => c.includes('weather'));

  const isPendingAction = event.response.status === 'pending';

  return (
    <div className="flex flex-col min-h-screen bg-[#03111F]">
      {/* Dynamic Command Header */}
      <DashboardHeader
        title={`Incident Breakdown: ${event.location.city}`}
        subtitle={`Air Basin Incident ID: ${event.event_id} • Surveillance Telemetry`}
        actions={
          fromAlerts ? (
            <button
              type="button"
              onClick={() => {
                if (typeof window !== 'undefined' && window.history.length > 1) {
                  router.back();
                } else {
                  router.push(returnToAlertsUrl);
                }
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-[rgba(0,213,255,0.20)] text-xs font-semibold text-[#00E5FF] hover:bg-[rgba(0,213,255,0.08)] transition-all cursor-pointer bg-[rgba(6,24,39,0.80)]"
              title="Return to Alert Surveillance Centre"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Alerts</span>
            </button>
          ) : (
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-[rgba(0,213,255,0.20)] text-xs font-semibold text-[#00E5FF] hover:bg-[rgba(0,213,255,0.08)] transition-all bg-[rgba(6,24,39,0.80)]"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Dashboard</span>
            </Link>
          )
        }
      />

      <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* Section A: Event Header Banner */}
        <div className="bg-[rgba(6,24,39,0.80)] border border-[rgba(0,213,255,0.14)] rounded-lg p-5 shadow-lg shadow-black/20 flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="h-12 w-12 rounded bg-[rgba(0,213,255,0.08)] border border-[rgba(0,213,255,0.20)] flex items-center justify-center text-[#00E5FF] shrink-0">
              <ShieldAlert className="w-6 h-6" />
            </div>

            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-bold text-[#E8F4FD] tracking-tight">
                  {event.location.city}
                </h2>
                <RiskBadge level={event.risk} size="md" />
                <span className="text-xs font-mono uppercase bg-[rgba(255,255,255,0.05)] text-[#7BA4BC] px-2 py-0.5 rounded border border-[rgba(255,255,255,0.1)]">
                  {event.outcome}
                </span>
              </div>

              <div className="mt-1 flex flex-wrap items-center gap-4 text-xs text-[#7BA4BC]">
                <span className="flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-[#2E5470]" />
                  <span className="font-mono tabular-telemetry">
                    {event.location.lat.toFixed(4)}°N, {event.location.lng.toFixed(4)}°E
                  </span>
                </span>
                <span className="text-[#2E5470]">•</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5 text-[#2E5470]" />
                  <span className="font-mono tabular-telemetry">
                    Timestamp: {new Date(event.timestamp).toUTCString()}
                  </span>
                </span>
                <span className="text-[#2E5470]">•</span>
                <span className="font-mono text-[#2E5470]">
                  ID: {event.event_id}
                </span>
              </div>
            </div>
          </div>

          {/* Authority Response State */}
          <div className="flex items-center gap-3">
            <div className="text-right">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#7BA4BC] block">
                Authority Status
              </span>
              <span className="text-xs font-semibold text-[#E8F4FD] capitalize">
                {event.response.status}
              </span>
            </div>
            {event.response.alert_sent && (
              <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded bg-[rgba(255,77,77,0.1)] text-[#FF4D4D] border border-[rgba(255,77,77,0.25)]">
                <FileCheck2 className="w-3.5 h-3.5" />
                Alert Routed
              </span>
            )}
          </div>
        </div>

        {/* Action Feedback Banner */}
        {actionFeedback && (
          <div
            className={`p-3.5 rounded-lg border text-xs flex items-center justify-between gap-3 ${
              actionFeedback.type === 'success'
                ? 'bg-[rgba(39,224,195,0.1)] text-[#27E0C3] border-[rgba(39,224,195,0.25)]'
                : 'bg-[rgba(255,68,68,0.1)] text-[#FF7070] border-[rgba(255,68,68,0.25)]'
            }`}
            role="status"
          >
            <div className="flex items-center gap-2">
              {actionFeedback.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-[#27E0C3] shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-[#FF7070] shrink-0" />
              )}
              <span>{actionFeedback.message}</span>
            </div>
            <button
              onClick={() => setActionFeedback(null)}
              className="text-[11px] underline opacity-80 hover:opacity-100"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Step 12: Dedicated AI & Predictive Model Assessment Dossier */}
        <AIModelPanel entityType="EVENT" event={event} isCompact={false} />

        {/* Section B: Gemini / AI Explanation */}
        <ExplanationBox explanation={event.explanation} />

        {/* Sections E, G, H: Detection Confidence, Forecast Uncertainty & Source Hypothesis */}
        <ConfidenceGauge
          detection={event.detection}
          forecast={event.forecast}
          hypothesis={event.source_hypothesis}
        />
              {/* Section D: Supporting vs Contradicting Cross-Validation Summary */}
        <div className="bg-[rgba(6,24,39,0.80)] border border-[rgba(0,213,255,0.14)] rounded-lg p-4 shadow-lg shadow-black/20">
          <div className="flex items-center justify-between pb-2 border-b border-[rgba(0,213,255,0.10)] mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-[#E8F4FD]">
              Evidence Cross-Validation Matrix
            </span>
            <span className="text-[11px] text-[#7BA4BC]">
              Corroboration Score:{' '}
              <strong className="text-[#00E5FF] tabular-telemetry">
                {supporting.length} Supporting / {contradicting.length} Contradicting
              </strong>
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="bg-[rgba(39,224,195,0.05)] border border-[rgba(39,224,195,0.2)] rounded p-3">
              <span className="text-xs font-semibold text-[#27E0C3] flex items-center gap-1.5 mb-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#27E0C3]" />
                Supporting Corroborators ({supporting.length})
              </span>
              <div className="flex flex-wrap gap-1.5">
                {supporting.length > 0 ? (
                  supporting.map((item, idx) => (
                    <span
                      key={idx}
                      className="text-[11px] font-mono px-2 py-0.5 rounded bg-[rgba(39,224,195,0.1)] text-[#27E0C3] border border-[rgba(39,224,195,0.2)]"
                    >
                      ✓ {item}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-[#2E5470] italic">
                    None registered
                  </span>
                )}
              </div>
            </div>

            <div className="bg-[rgba(255,181,46,0.05)] border border-[rgba(255,181,46,0.2)] rounded p-3">
              <span className="text-xs font-semibold text-[#FFB52E] flex items-center gap-1.5 mb-1.5">
                <AlertCircle className="w-3.5 h-3.5 text-[#FFB52E]" />
                Contradicting / Inconclusive ({contradicting.length})
              </span>
              <div className="flex flex-wrap gap-1.5">
                {contradicting.length > 0 ? (
                  contradicting.map((item, idx) => (
                    <span
                      key={idx}
                      className="text-[11px] font-mono px-2 py-0.5 rounded bg-[rgba(255,181,46,0.1)] text-[#FFB52E] border border-[rgba(255,181,46,0.2)]"
                    >
                      ⚠ {item}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-[#2E5470] italic">
                    Zero contradicting indicators
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Section C: Four Evidence Cards */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#E8F4FD]">
              Fused Multi-Source Telemetry Streams
            </h3>
            <span className="text-xs text-[#7BA4BC]">
              4 Synchronized Telemetry Layers
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <CitizenEvidenceCard
              evidence={event.evidence.citizen}
              isSupporting={isCitizenSupporting}
              isContradicting={isCitizenContradicting}
            />
            <SensorEvidenceCard
              evidence={event.evidence.sensor}
              isSupporting={isSensorSupporting}
              isContradicting={isSensorContradicting}
            />
            <SatelliteEvidenceCard
              evidence={event.evidence.satellite}
              isSupporting={isSatelliteSupporting}
              isContradicting={isSatelliteContradicting}
            />
            <WeatherEvidenceCard
              evidence={event.evidence.weather}
              isSupporting={isWeatherSupporting}
              isContradicting={isWeatherContradicting}
            />
          </div>
        </div>

        {/* Section I & J: Mini Forecast Chart & Event Timeline */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Mini Forecast Chart (2 cols) */}
          <div className="lg:col-span-2">
            <MiniForecastChart
              forecast={event.forecast}
              currentPm25={event.evidence.sensor?.pm25 || 100}
            />
          </div>

          {/* Event Timeline (1 col) */}
          <div>
            <Card className="h-full flex flex-col justify-between !bg-[rgba(6,24,39,0.80)] !border-[rgba(0,213,255,0.14)]">
              <div>
                <CardHeader
                  title="Incident Chronology"
                  subtitle="Sequence of detection and alerts"
                />
                <CardContent>
                  <Timeline items={event.timeline} />
                </CardContent>
              </div>

              <div className="p-4 border-t border-[rgba(0,213,255,0.1)] bg-[rgba(255,255,255,0.02)] text-[11px] text-[#7BA4BC] flex items-center justify-between">
                <span>Total Steps: {event.timeline.length}</span>
                <span className="font-mono text-[#2E5470]">All times UTC</span>
              </div>
            </Card>
          </div>
        </div>

        {/* Section K: Authority Response Actions */}
        <div className="bg-[rgba(6,24,39,0.80)] border border-[rgba(0,213,255,0.14)] rounded-lg p-5 shadow-lg shadow-black/20">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[rgba(0,213,255,0.1)] mb-4">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#E8F4FD] flex items-center gap-2">
                <Building2 className="w-4 h-4 text-[#00E5FF]" />
                Authority Response Workflow
              </h3>
              <p className="text-xs text-[#7BA4BC] mt-0.5">
                Assigned Authority: {event.response.authority_class || 'State Pollution Control Board'}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-[#7BA4BC]">Workflow State:</span>
              <span
                className={`text-xs px-2.5 py-0.5 rounded font-bold uppercase ${
                  isPendingAction
                    ? 'bg-[rgba(255,181,46,0.1)] text-[#FFB52E] border border-[rgba(255,181,46,0.25)]'
                    : 'bg-[rgba(255,255,255,0.05)] text-[#E8F4FD] border border-[rgba(255,255,255,0.1)]'
                }`}
              >
                {event.response.status}
              </span>
            </div>
          </div>

          {isPendingAction ? (
            <div>
              <p className="text-xs text-[#7BA4BC] mb-4">
                This incident is in a <strong>pending</strong> state awaiting human authority determination. Select an authorized response action:
              </p>

              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => handleAuthorityAction('confirm')}
                  disabled={actionInProgress}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded bg-gradient-to-r from-[#0066CC] to-[#004A99] hover:from-[#0077EE] hover:to-[#0055BB] text-white text-xs font-semibold transition-colors disabled:opacity-50 border border-[rgba(0,150,255,0.30)]"
                >
                  <CheckCircle2 className="w-4 h-4 text-[#00E5FF]" />
                  <span>Confirm Event & Issue Civic Alert</span>
                </button>

                <button
                  onClick={() => handleAuthorityAction('investigate')}
                  disabled={actionInProgress}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)] text-[#E8F4FD] border border-[rgba(255,255,255,0.15)] text-xs font-semibold transition-colors disabled:opacity-50"
                >
                  <Search className="w-4 h-4 text-[#00E5FF]" />
                  <span>Dispatch Field Investigation Unit</span>
                </button>

                <button
                  onClick={() => handleAuthorityAction('dismiss')}
                  disabled={actionInProgress}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded bg-[rgba(255,68,68,0.1)] hover:bg-[rgba(255,68,68,0.15)] text-[#FF7070] border border-[rgba(255,68,68,0.25)] text-xs font-semibold transition-colors disabled:opacity-50"
                >
                  <XCircle className="w-4 h-4 text-[#FF7070]" />
                  <span>Dismiss as False Alarm</span>
                </button>
              </div>

              <p className="text-[11px] text-[#2E5470] mt-3 italic">
                * Note: Running in mock data simulation mode. State changes update the active session memory through lib/api.ts.
              </p>
            </div>
          ) : (
            <div className="bg-[rgba(39,224,195,0.05)] rounded p-3.5 border border-[rgba(39,224,195,0.15)] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#27E0C3]" />
                <span className="text-xs text-[#E8F4FD]">
                  Incident response already acknowledged. Outcome finalized as{' '}
                  <strong className="text-[#00E5FF] capitalize font-mono">
                    {event.outcome}
                  </strong>
                  .
                </span>
              </div>
              <span className="text-[11px] text-[#7BA4BC] font-mono">
                No further pending actions required
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function EventDetailPage() {
  return (
    <Suspense fallback={<div>Loading event...</div>}>
      <EventDetailContent />
    </Suspense>
  );
}
