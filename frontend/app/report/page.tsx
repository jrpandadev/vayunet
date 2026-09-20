'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { submitReport } from '@/lib/api';
import { LanguageCode, translations } from '@/lib/translations';
import VoiceInput from '@/components/report/VoiceInput';
import StatusStepper from '@/components/report/StatusStepper';
import {
  Camera,
  Upload,
  MapPin,
  Send,
  Trash2,
  AlertTriangle,
  ExternalLink,
  Navigation,
} from 'lucide-react';

// Dynamic import of the Leaflet mini-map with SSR disabled
const CitizenLocationMap = dynamic(
  () => import('@/components/report/CitizenLocationMap'),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-56 rounded-lg bg-slate-100 flex flex-col items-center justify-center text-slate-400 text-xs">
        <div className="h-6 w-6 border-2 border-[#0a2540] border-t-transparent rounded-full animate-spin mb-2" />
        <span>Loading GPS Location Grid...</span>
      </div>
    ),
  }
);

export default function CitizenReportPage() {
  const [language, setLanguage] = useState<LanguageCode>('en');
  const t = translations[language];

  // Camera & File input refs for value reset on image removal
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Form State
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [description, setDescription] = useState<string>('');
  const [lat, setLat] = useState<number>(28.6139); // Default: New Delhi
  const [lng, setLng] = useState<number>(77.2090);
  const [isLocating, setIsLocating] = useState<boolean>(false);
  const [locationStatus, setLocationStatus] = useState<string | null>(null);

  // Submission Pipeline State
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submittedEventId, setSubmittedEventId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Restore language preference safely if previously stored
  useEffect(() => {
    try {
      if (typeof window !== 'undefined') {
        const saved = localStorage.getItem('vayunet_lang') as LanguageCode | null;
        if (saved === 'en' || saved === 'hi') {
          setLanguage(saved);
        }
      }
    } catch (e) {
      console.warn('Could not read localStorage:', e);
    }
  }, []);

  const handleLanguageChange = (lang: LanguageCode) => {
    setLanguage(lang);
    try {
      if (typeof window !== 'undefined') {
        localStorage.setItem('vayunet_lang', lang);
      }
    } catch (e) {
      console.warn('Could not write localStorage:', e);
    }
  };

  // Auto-detect location safely on mount
  useEffect(() => {
    detectLocation();
  }, []);

  const detectLocation = () => {
    try {
      if (typeof window !== 'undefined' && 'geolocation' in navigator) {
        setIsLocating(true);
        setLocationStatus(t.autoDetecting);
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            setLat(Number(pos.coords.latitude.toFixed(5)));
            setLng(Number(pos.coords.longitude.toFixed(5)));
            setIsLocating(false);
            setLocationStatus(null);
          },
          (err) => {
            console.warn('Geolocation error:', err.message);
            setIsLocating(false);
            setLocationStatus(null);
          },
          { enableHighAccuracy: false, timeout: 8000 }
        );
      }
    } catch (err) {
      console.warn('Geolocation access failed:', err);
      setIsLocating(false);
      setLocationStatus(null);
    }
  };

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setPhotoFile(file);
      setPhotoPreview(URL.createObjectURL(file));
    }
    // Clear value to allow re-capturing or selecting the same image
    e.target.value = '';
  };

  const removePhoto = () => {
    setPhotoFile(null);
    if (photoPreview) {
      URL.revokeObjectURL(photoPreview);
      setPhotoPreview(null);
    }
    if (cameraInputRef.current) cameraInputRef.current.value = '';
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleVoiceTranscript = (text: string) => {
    setDescription((prev) => (prev ? `${prev} ${text}` : text));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim() && !photoFile) {
      setErrorMessage(t.errorMessageEmpty);
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const response = await submitReport({
        photo: photoFile,
        text: description,
        lat,
        lng,
      });

      if (response.success) {
        setSubmittedEventId(response.event_id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Submission failed';
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setSubmittedEventId(null);
    setDescription('');
    removePhoto();
    setErrorMessage(null);
    detectLocation();
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] text-[#0f172a] flex flex-col">
      {/* Citizen Top Navigation */}
      <header className="bg-white border-b border-[#e2e8f0] px-4 py-3 sticky top-0 z-30 shadow-xs">
        <div className="max-w-3xl mx-auto flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded bg-[#0a2540] text-white flex items-center justify-center font-bold text-sm shadow-xs">
              V
            </div>
            <div>
              <span className="font-bold tracking-tight text-sm text-[#0a2540] block">
                {t.appName}
              </span>
              <span className="text-[10px] text-slate-500 font-medium block">
                {t.citizenPortal}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Accessible Language Switch Buttons */}
            <div className="flex items-center bg-slate-100 rounded-full p-1 border border-slate-200 text-xs">
              <button
                type="button"
                onClick={() => handleLanguageChange('en')}
                className={`px-3.5 py-1.5 min-h-[36px] min-w-[64px] rounded-full font-semibold transition-all cursor-pointer flex items-center justify-center ${
                  language === 'en'
                    ? 'bg-white text-[#0a2540] shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 active:bg-slate-200'
                }`}
                aria-pressed={language === 'en'}
              >
                English
              </button>
              <button
                type="button"
                onClick={() => handleLanguageChange('hi')}
                className={`px-3.5 py-1.5 min-h-[36px] min-w-[64px] rounded-full font-semibold transition-all cursor-pointer flex items-center justify-center ${
                  language === 'hi'
                    ? 'bg-white text-[#0a2540] shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 active:bg-slate-200'
                }`}
                aria-pressed={language === 'hi'}
              >
                हिंदी
              </button>
            </div>

            {/* Link to Authority Portal */}
            <Link
              href="/dashboard"
              className="hidden sm:inline-flex items-center gap-1 px-3 py-1.5 rounded border border-slate-300 hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors"
            >
              <span>{t.authorityPortal}</span>
              <ExternalLink className="w-3 h-3 text-slate-400" />
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 px-4 py-6 max-w-2xl mx-auto w-full">
        {submittedEventId ? (
          /* Submission Stepper & Tracking */
          <StatusStepper
            eventId={submittedEventId}
            language={language}
            onReset={handleReset}
          />
        ) : (
          /* Report Submission Form */
          <div className="bg-white border border-[#e2e8f0] rounded-xl p-5 sm:p-7 shadow-xs space-y-6">
            <div>
              <h2 className="text-lg font-bold text-[#0f172a] tracking-tight">
                {t.reportButton}
              </h2>
              <p className="text-xs text-[#64748b] mt-1 leading-relaxed">
                {t.reportSubtitle}
              </p>
            </div>

            {errorMessage && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* 1. Photo Capture & Upload */}
              <div className="space-y-2">
                <span className="block text-xs font-bold uppercase tracking-wider text-slate-700">
                  {t.uploadPhoto}
                </span>
                <p className="text-[11px] text-slate-500">{t.photoTip}</p>

                {photoPreview ? (
                  <div className="relative rounded-lg overflow-hidden border border-slate-200 bg-slate-100 max-h-64 flex items-center justify-center">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={photoPreview}
                      alt="Pollution observation preview"
                      className="object-cover w-full h-56"
                    />
                    <button
                      type="button"
                      onClick={removePhoto}
                      className="absolute top-2 right-2 p-2 rounded-full bg-slate-900/80 text-white hover:bg-rose-600 transition-colors shadow-sm cursor-pointer"
                      title="Remove image"
                      aria-label="Remove image"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {/* Camera Capture Control - Pure Semantic Label */}
                    <label
                      htmlFor="camera-capture-input"
                      className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-slate-300 rounded-lg hover:border-[#0a2540] hover:bg-slate-50 active:bg-slate-100 transition-all cursor-pointer text-center w-full select-none"
                    >
                      <Camera className="w-6 h-6 text-[#0a2540] mb-1.5 pointer-events-none" />
                      <span className="text-xs font-semibold text-slate-800 pointer-events-none">
                        {t.takePhoto}
                      </span>
                      <span className="text-[10px] text-slate-400 mt-0.5 pointer-events-none">
                        {t.takePhotoTip}
                      </span>
                      <input
                        ref={cameraInputRef}
                        id="camera-capture-input"
                        type="file"
                        accept="image/*"
                        capture="environment"
                        onChange={handlePhotoChange}
                        className="sr-only"
                      />
                    </label>

                    {/* Gallery / File Upload Control - Pure Semantic Label */}
                    <label
                      htmlFor="file-upload-input"
                      className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-slate-300 rounded-lg hover:border-[#0a2540] hover:bg-slate-50 active:bg-slate-100 transition-all cursor-pointer text-center w-full select-none"
                    >
                      <Upload className="w-6 h-6 text-slate-500 mb-1.5 pointer-events-none" />
                      <span className="text-xs font-semibold text-slate-800 pointer-events-none">
                        {t.uploadFile}
                      </span>
                      <span className="text-[10px] text-slate-400 mt-0.5 pointer-events-none">
                        {t.uploadFileTip}
                      </span>
                      <input
                        ref={fileInputRef}
                        id="file-upload-input"
                        type="file"
                        accept="image/*"
                        onChange={handlePhotoChange}
                        className="sr-only"
                      />
                    </label>
                  </div>
                )}
              </div>

              {/* 2. Text Description & Web Speech Voice Input */}
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <label
                    htmlFor="report-description"
                    className="block text-xs font-bold uppercase tracking-wider text-slate-700 cursor-pointer"
                  >
                    {t.describeIssue}
                  </label>

                  {/* Web Speech API Voice Button */}
                  <VoiceInput
                    language={language}
                    onTranscript={handleVoiceTranscript}
                  />
                </div>

                <textarea
                  id="report-description"
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={t.describePlaceholder}
                  className="w-full p-3 rounded-lg border border-slate-300 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-hidden focus:ring-1 focus:ring-[#0a2540] focus:border-[#0a2540] leading-relaxed"
                />
              </div>

              {/* 3. Geolocation & Interactive Mini-Map */}
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-700">
                    <MapPin className="w-4 h-4 text-[#0a2540]" />
                    <span>{t.locationLabel}</span>
                  </div>

                  <button
                    type="button"
                    onClick={detectLocation}
                    disabled={isLocating}
                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#0a2540] hover:text-sky-700 transition-colors cursor-pointer"
                  >
                    <Navigation className={`w-3 h-3 ${isLocating ? 'animate-spin' : ''}`} />
                    <span>{isLocating ? t.autoDetecting : t.redetectGps}</span>
                  </button>
                </div>

                {locationStatus && (
                  <p className="text-[11px] text-sky-700 font-medium">
                    {locationStatus}
                  </p>
                )}

                {/* Interactive Leaflet Mini-Map with pin draggable / clickable */}
                <CitizenLocationMap
                  lat={lat}
                  lng={lng}
                  helperText={t.manualPinAdjust}
                  onLocationChange={(newLat, newLng) => {
                    setLat(Number(newLat.toFixed(5)));
                    setLng(Number(newLng.toFixed(5)));
                  }}
                />

                <div className="flex items-center justify-between text-[11px] text-[#64748b] font-mono tabular-telemetry">
                  <span>
                    Lat: <strong className="text-slate-800">{lat}</strong>
                  </span>
                  <span>
                    Lng: <strong className="text-slate-800">{lng}</strong>
                  </span>
                </div>
              </div>

              {/* 4. Submit Action */}
              <div className="pt-3 border-t border-slate-100">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full py-3 px-5 rounded-lg bg-[#0a2540] hover:bg-[#0f2a3f] text-white text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-sm disabled:opacity-50 cursor-pointer"
                >
                  {isSubmitting ? (
                    <>
                      <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>{t.submitting}</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      <span>{t.submit}</span>
                    </>
                  )}
                </button>
                <p className="text-center text-[10px] text-slate-400 mt-2">
                  {t.confidentialityNotice}
                </p>
              </div>
            </form>
          </div>
        )}
      </main>
    </div>
  );
}
