import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SFrame — Crop & Super-Resolution",
  description: "DSLR image cropping and AuraSR-v2 super-resolution",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
