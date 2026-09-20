'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Mic, AlertCircle, X } from 'lucide-react';
import { LanguageCode, translations } from '@/lib/translations';

// Web Speech API globals for TypeScript
interface IWindow extends Window {
  SpeechRecognition?: any;
  webkitSpeechRecognition?: any;
}

interface VoiceInputProps {
  language: LanguageCode;
  onTranscript: (text: string) => void;
  className?: string;
}

export const VoiceInput: React.FC<VoiceInputProps> = ({
  language,
  onTranscript,
  className = '',
}) => {
  const [isListening, setIsListening] = useState<boolean>(false);
  const [errorNotice, setErrorNotice] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);
  const t = translations[language];

  // Clean up any active speech recognition on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {}
        recognitionRef.current = null;
      }
    };
  }, []);

  const toggleListening = () => {
    // 1. Dynamic check for secure context (HTTPS or localhost)
    const isSecureContext = typeof window !== 'undefined' && Boolean(
      window.isSecureContext ||
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1'
    );

    if (!isSecureContext) {
      setErrorNotice(t.voiceSecureNotice);
      return;
    }

    // 2. Dynamic check for browser SpeechRecognition support
    const win = typeof window !== 'undefined' ? (window as unknown as IWindow) : null;
    const SpeechRecognitionClass = win?.SpeechRecognition || win?.webkitSpeechRecognition;

    if (!SpeechRecognitionClass) {
      setErrorNotice(t.voiceUnavailableNotice);
      return;
    }

    // 3. Lazy initialize recognition instance if not already created
    if (!recognitionRef.current) {
      try {
        const recog = new SpeechRecognitionClass();
        recog.continuous = false;
        recog.interimResults = false;
        recog.lang = language === 'hi' ? 'hi-IN' : 'en-IN';

        recog.onstart = () => {
          setIsListening(true);
          setErrorNotice(null);
        };

        recog.onresult = (event: any) => {
          if (event.results && event.results.length > 0) {
            const text = event.results[0][0]?.transcript;
            if (text) {
              onTranscript(text);
            }
          }
        };

        recog.onerror = (event: any) => {
          console.warn('Speech recognition error:', event.error);
          setIsListening(false);
          if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
            setErrorNotice(t.voiceDeniedNotice);
          } else if (event.error === 'no-speech') {
            setErrorNotice(t.voiceNoSpeechNotice);
          } else if (event.error === 'network') {
            setErrorNotice(language === 'hi' ? 'नेटवर्क त्रुटि। कृपया पुनः प्रयास करें।' : 'Network error during voice recognition.');
          } else if (event.error !== 'aborted') {
            setErrorNotice(language === 'hi' ? `त्रुटि: ${event.error}` : `Recognition error: ${event.error}`);
          }
        };

        recog.onend = () => {
          setIsListening(false);
        };

        recognitionRef.current = recog;
      } catch (err) {
        console.warn('Failed to initialize SpeechRecognition:', err);
        setErrorNotice(t.voiceUnavailableNotice);
        return;
      }
    }

    // 4. Toggle listening state
    if (isListening) {
      try {
        recognitionRef.current.stop();
      } catch {}
      setIsListening(false);
    } else {
      try {
        setErrorNotice(null);
        recognitionRef.current.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
        recognitionRef.current.start();
      } catch (err) {
        console.warn('Recognition start exception:', err);
        try {
          recognitionRef.current.abort();
          setTimeout(() => {
            recognitionRef.current?.start();
          }, 100);
        } catch {
          setErrorNotice(language === 'hi' ? 'माइक्रोफ़ोन प्रारंभ करने में असमर्थ' : 'Unable to start microphone');
        }
      }
    }
  };

  return (
    <div className={`space-y-1.5 ${className}`}>
      <button
        type="button"
        onClick={toggleListening}
        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer select-none ${
          isListening
            ? 'bg-rose-600 text-white shadow-md ring-4 ring-rose-200 animate-pulse'
            : 'bg-slate-100 hover:bg-slate-200 text-[#0a2540] border border-slate-300 active:bg-slate-300'
        }`}
        title={isListening ? 'Stop voice recording' : t.speakPrompt}
        aria-pressed={isListening}
      >
        <Mic className={`w-3.5 h-3.5 ${isListening ? 'animate-bounce' : 'text-[#0a2540]'}`} />
        <span>{isListening ? t.listening : t.voiceButton}</span>
        <span className="text-[10px] font-mono opacity-75">
          ({language === 'hi' ? 'हिंदी' : 'EN'})
        </span>
      </button>

      {errorNotice && (
        <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900 flex items-start gap-2 shadow-xs">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold text-[11px]">
              {language === 'hi' ? 'सुरक्षित कनेक्शन (HTTPS) आवश्यक है' : 'Secure Context (HTTPS) Required'}
            </p>
            <p className="text-[11px] text-amber-800 mt-0.5 leading-relaxed">
              {errorNotice}
            </p>
            <p className="text-[10px] text-amber-700 mt-1 font-mono">
              Origin: {typeof window !== 'undefined' ? window.location.origin : ''} (HTTP LAN)
            </p>
          </div>
          <button
            type="button"
            onClick={() => setErrorNotice(null)}
            className="text-amber-600 hover:text-amber-900 p-0.5 cursor-pointer"
            aria-label="Dismiss notice"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
};

export default VoiceInput;
