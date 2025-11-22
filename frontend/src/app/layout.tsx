import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Concierge",
  description: "Your intelligent assistant for a seamless web experience.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {/* Optional CSP meta fallback (headers already set). Remove if redundant. */}
        <meta httpEquiv="Content-Security-Policy" content="default-src 'self'; connect-src 'self' http://localhost:8000 ws://localhost:8000; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline';" />
        {children}
      </body>
    </html>
  );
}
