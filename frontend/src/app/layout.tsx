import type { Metadata } from "next";
import type { ReactNode } from "react";

// Source Sans 3, self-hosted: no request goes to Google Fonts (AD-18).
import "@fontsource/source-sans-3/400.css";
import "@fontsource/source-sans-3/600.css";
import "@fontsource/source-sans-3/700.css";
import "./globals.css";

import { SiteFooter } from "@/components/site-footer";
import { nb } from "@/copy/nb";

import { Providers } from "./providers";

export const metadata: Metadata = {
  title: { default: nb.product.name, template: `%s – ${nb.product.name}` },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="nb">
      <body>
        <Providers>
          {children}
          <SiteFooter />
        </Providers>
      </body>
    </html>
  );
}
