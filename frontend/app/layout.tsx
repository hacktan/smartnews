import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: { default: "SmartNews", template: "%s | SmartNews" },
  description: "AI-curated tech news — powered by Azure Databricks & GPT-4o-mini",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-[#f8f9fb] antialiased">
        <Navbar />
        <main className="mx-auto max-w-7xl px-4 py-8 sm:py-12">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
