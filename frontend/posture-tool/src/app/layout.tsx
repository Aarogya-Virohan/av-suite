import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

// Brand typefaces, 13 October 2026 (brand direction B, same as the PDF).
// Served from the repo, not from Google, so a build needs no network and the
// files are the same ones pdf_service.py embeds. OFL licences beside them.
const inter = localFont({
  src: [
    { path: "./fonts/inter-latin-400-normal.woff", weight: "400", style: "normal" },
    { path: "./fonts/inter-latin-600-normal.woff", weight: "600", style: "normal" },
    { path: "./fonts/inter-latin-700-normal.woff", weight: "700", style: "normal" },
  ],
  variable: "--font-inter",
  display: "swap",
});

const jakarta = localFont({
  src: [
    { path: "./fonts/plus-jakarta-sans-latin-700-normal.woff", weight: "700", style: "normal" },
    { path: "./fonts/plus-jakarta-sans-latin-800-normal.woff", weight: "800", style: "normal" },
  ],
  variable: "--font-jakarta",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Aarogya Virohan Posture Tool",
  description: "Clinical posture assessment and reporting tool",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`h-full antialiased ${inter.variable} ${jakarta.variable}`}>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
