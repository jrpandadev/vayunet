'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { LanguageCode, translations } from '@/lib/translations';
import {
  CheckCircle2,
  Sparkles,
  Layers,
  ShieldCheck,
  Radio,
  ArrowRight,
  RotateCcw,
  Clock,
  ShieldAlert,
} from 'lucide-react';

interface StatusStepperProps {
  eventId: string;
  language: LanguageCode;
  onReset: () => void;
  className?: string;
}

export const StatusStepper: React.FC<StatusStepperProps> = ({
  eventId,
  language,
  onReset,
  className = '',
}) => {
  const t = translations[language];

  const steps = [
    {
      id: 1,
      title: t.reportStatus.received,
      desc: language === 'hi' ? 'रिपोर्ट सुरक्षित रूप से प्राप्त हुई' : 'Transmission acknowledged by central ingest gateway',
      icon: <CheckCircle2 className="w-4 h-4 text-emerald-600" />,
    },
    {
      id: 2,
      title: t.reportStatus.analyzing,
      desc: language === 'hi' ? 'छवि व पाठ की दृश्य व्याख्या जारी' : 'Evaluating visual plume density and event classification',
      icon: <Sparkles className="w-4 h-4 text-sky-600" />,
    },
    {
      id: 3,
      title: t.reportStatus.evidenceProcessing,
      desc: language === 'hi' ? 'समीपस्थ CPCB स्टेशन व उपग्रह डेटा से मिलान' : 'Cross-referencing nearby CPCB ground monitors & Sentinel-5P pass',
      icon: <Layers className="w-4 h-4 text-[#0a2540]" />,
    },
    {
      id: 4,
      title: t.reportStatus.confidenceComputed,
      desc: language === 'hi' ? 'बहु-स्रोतीय विश्वसनीयता स्कोर: 84%' : 'Multi-source corroboration score computed (Confidence: 0.84)',
      icon: <ShieldCheck className="w-4 h-4 text-emerald-600" />,
    },
    {
      id: 5,
      title: t.reportStatus.alertRouted,
      desc: language === 'hi' ? 'संबंधित नगर निगम व नियंत्रण कक्ष को सूचित' : 'Surveillance incident created on Authority Intelligence Dashboard',
      icon: <Radio className="w-4 h-4 text-rose-600" />,
    },
  ];

  const [currentStep, setCurrentStep] = useState<number>(1);
  const [completed, setCompleted] = useState<boolean>(false);

  useEffect(() => {
    // Progress through the pipeline steps to simulate backend AI fusion
    const timer = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev < steps.length) {
          return prev + 1;
        } else {
          setCompleted(true);
          clearInterval(timer);
          return prev;
        }
      });
    }, 1200);

    return () => clearInterval(timer);
  }, [steps.length]);

  return (
    <div className={`bg-white border border-[#e2e8f0] rounded-xl p-6 shadow-sm ${className}`}>
      {/* Header */}
      <div className="text-center pb-5 border-b border-slate-100">
        <div className="inline-flex items-center justify-center h-12 w-12 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200 mb-3 shadow-xs">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-[#0f172a]">
          {language === 'hi' ? 'प्रदूषण रिपोर्ट प्रक्रिया' : 'Observation Processing Pipeline'}
        </h3>
        <p className="text-xs font-mono text-slate-500 mt-1">
          Tracking Token: <strong className="text-slate-800">{eventId}</strong>
          {eventId.startsWith('evt_citizen_') && (
            <span className="ml-2 text-[10px] font-sans font-semibold text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
              Simulation Mode
            </span>
          )}
        </p>
      </div>

      {/* Stepper Timeline */}
      <div className="py-6 space-y-6">
        {steps.map((step) => {
          const isDone = step.id < currentStep || completed;
          const isCurrent = step.id === currentStep && !completed;

          return (
            <div key={step.id} className="flex items-start gap-4">
              <div className="flex flex-col items-center">
                <div
                  className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold transition-all shadow-xs ${
                    isDone
                      ? 'bg-emerald-600 text-white'
                      : isCurrent
                      ? 'bg-[#0a2540] text-white ring-4 ring-sky-100'
                      : 'bg-slate-100 text-slate-400 border border-slate-200'
                  }`}
                >
                  {isDone ? (
                    <CheckCircle2 className="w-4 h-4" />
                  ) : isCurrent ? (
                    <div className="h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    step.id
                  )}
                </div>
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h4
                    className={`text-xs font-bold uppercase tracking-wider ${
                      isDone || isCurrent ? 'text-[#0f172a]' : 'text-slate-400'
                    }`}
                  >
                    {step.title}
                  </h4>
                  {isCurrent && (
                    <span className="text-[10px] text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-200 font-mono animate-pulse">
                      Processing...
                    </span>
                  )}
                </div>
                <p className="text-xs text-[#64748b] mt-0.5">{step.desc}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Actions upon pipeline completion */}
      {completed && (
        <div className="pt-5 border-t border-slate-100 bg-slate-50/50 -mx-6 -mb-6 p-6 rounded-b-xl flex flex-col sm:flex-row items-center justify-between gap-3">
          <button
            onClick={onReset}
            className="inline-flex items-center justify-center gap-1.5 w-full sm:w-auto px-4 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded transition-colors cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>{language === 'hi' ? 'अन्य रिपोर्ट सबमिट करें' : 'Submit Another Report'}</span>
          </button>

          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center gap-1.5 w-full sm:w-auto px-4 py-2 bg-[#0a2540] hover:bg-[#0f2a3f] text-white text-xs font-semibold rounded transition-colors shadow-xs"
          >
            <span>{language === 'hi' ? 'प्राधिकरण डैशबोर्ड देखें' : 'View Authority Dashboard'}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}
    </div>
  );
};

export default StatusStepper;
