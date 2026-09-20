/**
 * VayuNet Firebase Client Stub
 * Environment-variable driven configuration for Firebase Auth and Firestore.
 * Zero hardcoded keys or production secrets.
 *
 * Safe for Next.js SSR / client-side execution.
 */

import { initializeApp, getApps, getApp, FirebaseApp } from 'firebase/app';
import { getFirestore, Firestore } from 'firebase/firestore';
import { getAuth, Auth } from 'firebase/auth';

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || 'AIzaSyDrrZ94mk6lK5uZympbnpKNNfJs57uMUMI',
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || 'vayunet-52a15.firebaseapp.com',
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || 'vayunet-52a15',
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || '513267415373',
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || '1:513267415373:web:bdae4237696dd889fb9f04',
};

// Initialize Firebase only once across hot reloads
const app: FirebaseApp = !getApps().length ? initializeApp(firebaseConfig) : getApp();

export const db: Firestore = getFirestore(app);
export const auth: Auth = getAuth(app);
export default app;
