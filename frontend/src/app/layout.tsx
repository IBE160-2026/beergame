import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "ØL-spillet",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="nb">
      <body>{children}</body>
    </html>
  );
}
