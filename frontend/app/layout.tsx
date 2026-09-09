import type { Metadata } from "next";
import type { ReactNode } from "react";
import { GoogleAnalytics } from "@next/third-parties/google";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { SITE_NAME, SITE_URL } from "@/lib/seo";
import "./globals.css";

// GA4 measurement ID for tulo.io. @next/third-parties' GoogleAnalytics
// component (not a hand-rolled <script> tag) is the Next.js App
// Router-native way to load gtag.js: it loads the script efficiently via
// next/script AND, critically, fires a page_view on every client-side
// route change (next/link navigation, no full page reload) -- a raw copy
// of Google's own <script> snippet only ever fires once, on the very
// first hard page load, and would silently miss every subsequent
// navigation on a Next.js site.
const GA_MEASUREMENT_ID = "G-GBJWXCM8SQ";

const DEFAULT_DESCRIPTION =
  "Tulo is a no-clutter recipe site, ingredients and instructions up front, plus native serving-size scaling and unit conversion built into every recipe.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: SITE_NAME,
    template: `%s | ${SITE_NAME}`,
  },
  description: DEFAULT_DESCRIPTION,
  openGraph: {
    siteName: SITE_NAME,
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col">
        <Header />
        <div className="flex-1 pb-20">{children}</div>
        <Footer />
      </body>
      <GoogleAnalytics gaId={GA_MEASUREMENT_ID} />
    </html>
  );
}
