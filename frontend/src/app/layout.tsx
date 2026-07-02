import type { Metadata } from "next"
import { Inter } from "next/font/google"

import "./globals.css"
import { ThemeProvider, ToastProvider } from "@/components/providers"
import { TooltipProvider } from "@/components/ui/tooltip"

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
})

export const metadata: Metadata = {
  title: "TalentLens",
  description: "AI-powered recruitment intelligence platform",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <TooltipProvider>
            {children}
            <ToastProvider />
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
