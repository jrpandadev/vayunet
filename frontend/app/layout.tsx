import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/authContext";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "VayuNet — Federated Environmental Intelligence Platform",
  description:
    "India-scale hyper-local pollution event detection fusing citizen observations, CPCB ground sensors, and Sentinel-5P satellite telemetry with Gemini multimodal AI reasoning.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-[#f8fafc] text-[#0f172a]">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
