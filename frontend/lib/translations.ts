/**
 * VayuNet Multilingual Translation Dictionary
 * Provides English and Hindi localized strings for the Citizen Interface.
 */

export type LanguageCode = 'en' | 'hi';

export interface TranslationDictionary {
  appName: string;
  citizenPortal: string;
  authorityDashboard: string;
  reportButton: string;
  uploadPhoto: string;
  photoTip: string;
  takePhoto: string;
  takePhotoTip: string;
  uploadFile: string;
  uploadFileTip: string;
  describeIssue: string;
  describePlaceholder: string;
  voiceButton: string;
  listening: string;
  speakPrompt: string;
  locationLabel: string;
  autoDetecting: string;
  redetectGps: string;
  manualPinAdjust: string;
  submit: string;
  submitting: string;
  authorityPortal: string;
  reportSubtitle: string;
  confidentialityNotice: string;
  errorMessageEmpty: string;
  voiceSecureNotice: string;
  voiceUnavailableNotice: string;
  voiceDeniedNotice: string;
  voiceNoSpeechNotice: string;
  reportStatus: {
    received: string;
    analyzing: string;
    evidenceProcessing: string;
    confidenceComputed: string;
    alertRouted: string;
  };
  riskLevels: {
    low: string;
    moderate: string;
    high: string;
    critical: string;
  };
}

export const translations: Record<LanguageCode, TranslationDictionary> = {
  en: {
    appName: 'VayuNet',
    citizenPortal: 'Citizen Pollution Reporter',
    authorityDashboard: 'Authority Intelligence Dashboard',
    reportButton: 'Report Pollution',
    uploadPhoto: 'Upload Observation Photo',
    photoTip: 'Take a live photo or upload clear image of smoke, dust, or emissions',
    takePhoto: 'Take Photo (Camera)',
    takePhotoTip: 'Capture live emission',
    uploadFile: 'Upload from File',
    uploadFileTip: 'JPEG, PNG, WebP',
    describeIssue: 'Describe What You Observe',
    describePlaceholder: 'e.g., Heavy dark smoke rising behind factory warehouse, strong burning plastic odor...',
    voiceButton: 'Voice Report (Speech-to-Text)',
    listening: 'Listening... Please speak now',
    speakPrompt: 'Click microphone to dictate in English',
    locationLabel: 'Observation Location',
    autoDetecting: 'Detecting GPS coordinates...',
    redetectGps: 'Re-detect GPS',
    manualPinAdjust: 'Drag pin or adjust location if needed',
    submit: 'Submit Pollution Report',
    submitting: 'Submitting report...',
    authorityPortal: 'Authority Portal',
    reportSubtitle: 'Crowdsourced observations are verified with Gemini AI and routed to municipal authorities.',
    confidentialityNotice: 'Observations are treated confidentially under public environmental reporting protocols.',
    errorMessageEmpty: 'Please enter a description or upload a photo of the incident',
    voiceSecureNotice: 'Voice input requires a secure context (HTTPS or localhost) and a supported browser.',
    voiceUnavailableNotice: 'Speech recognition is not supported in this browser. Please use Chrome or Edge.',
    voiceDeniedNotice: 'Microphone access was denied. Please allow microphone permissions in browser settings.',
    voiceNoSpeechNotice: 'No speech detected. Please try speaking again.',
    reportStatus: {
      received: 'Report Received',
      analyzing: 'Gemini AI Multimodal Analyzing...',
      evidenceProcessing: 'Synthesizing with Sensor & Satellite Grid...',
      confidenceComputed: 'Event Confidence Verified',
      alertRouted: 'Alert Routed to Municipal Authority',
    },
    riskLevels: {
      low: 'Low Impact',
      moderate: 'Moderate Exposure',
      high: 'High Risk Alert',
      critical: 'Critical Emergency',
    },
  },
  hi: {
    appName: 'वायुनेट (VayuNet)',
    citizenPortal: 'नागरिक प्रदूषण रिपोर्टर',
    authorityDashboard: 'प्राधिकरण पर्यावरण डैशबोर्ड',
    reportButton: 'प्रदूषण की रिपोर्ट करें',
    uploadPhoto: 'प्रदूषण की फोटो अपलोड करें',
    photoTip: 'धुआं, धूल या अपशिष्ट दहन की स्पष्ट तस्वीर खींचें या अपलोड करें',
    takePhoto: 'फोटो खींचें (कैमरा)',
    takePhotoTip: 'सीधे कैमरे से फोटो लें',
    uploadFile: 'फाइल से अपलोड करें',
    uploadFileTip: 'JPEG, PNG, WebP',
    describeIssue: 'प्रदूषण का विवरण लिखें',
    describePlaceholder: 'उदा. कारखाने के पीछे से काला धुआं निकल रहा है, जलते प्लास्टिक की गंध आ रही है...',
    voiceButton: 'आवाज से रिपोर्ट करें (बोलकर लिखें)',
    listening: 'सुन रहे हैं... कृपया अब बोलें',
    speakPrompt: 'हिंदी में बोलने के लिए माइक पर क्लिक करें',
    locationLabel: 'घटना का स्थान',
    autoDetecting: 'जीपीएस स्थान प्राप्त किया जा रहा है...',
    redetectGps: 'पुनः जीपीएस खोजें',
    manualPinAdjust: 'आवश्यकता होने पर पिन को सही स्थान पर ले जाएं',
    submit: 'प्रदूषण रिपोर्ट सबमिट करें',
    submitting: 'रिपोर्ट भेजी जा रही है...',
    authorityPortal: 'प्राधिकरण पोर्टल',
    reportSubtitle: 'नागरिक प्रमाण स्वतः जेमिनी एआई द्वारा संसाधित होकर संबंधित प्रदूषण नियंत्रण प्राधिकरण को प्रेषित किया जाता है।',
    confidentialityNotice: 'नागरिक संरक्षण अधिनियम के तहत आपकी पहचान गोपनीय रखी जाती है।',
    errorMessageEmpty: 'कृपया विवरण लिखें या प्रदूषण की फोटो अपलोड करें',
    voiceSecureNotice: 'आवाज से इनपुट के लिए सुरक्षित कनेक्शन (HTTPS या localhost) और समर्थित ब्राउज़र आवश्यक है।',
    voiceUnavailableNotice: 'आपके ब्राउज़र में स्पीच रिकग्निशन समर्थित नहीं है। कृपया Chrome या Edge का उपयोग करें।',
    voiceDeniedNotice: 'माइक्रोफ़ोन की अनुमति नहीं दी गई। कृपया ब्राउज़र में अनुमति प्रदान करें।',
    voiceNoSpeechNotice: 'कोई आवाज नहीं सुनी गई। कृपया पुनः प्रयास करें।',
    reportStatus: {
      received: 'रिपोर्ट प्राप्त हुई',
      analyzing: 'जेमिनी एआई बहुविध विश्लेषण जारी...',
      evidenceProcessing: 'सेंसर व सैटेलाइट डेटा से मिलान जारी...',
      confidenceComputed: 'घटना विश्वसनीयता प्रमाणित',
      alertRouted: 'संबंधित प्रदूषण नियंत्रण प्राधिकरण को सतर्क किया गया',
    },
    riskLevels: {
      low: 'कम प्रभाव',
      moderate: 'मध्यम जोखिम',
      high: 'उच्च जोखिम चेतावनी',
      critical: 'अति गंभीर आपातकाल',
    },
  },
};
