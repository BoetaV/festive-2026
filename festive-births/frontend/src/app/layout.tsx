import type { Metadata, Viewport } from "next"
import { Geist_Mono, Montserrat } from "next/font/google"
import { Providers } from "@/components/providers"
import "./globals.css"

// Montserrat: the heavy geometric sans of the ECDoH campaign artwork (variable font, all weights).
const montserrat = Montserrat({ variable: "--font-sans", subsets: ["latin"] })
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] })

export const metadata: Metadata = {
  title: { default: "Festive Births 2026", template: "%s · Festive Births 2026" },
  description: "Eastern Cape Department of Health – festive season births dashboard and capture system.",
  applicationName: "Festive Births",
  appleWebApp: { title: "Festive Births", capable: true, statusBarStyle: "default" },
}

// Colours the browser/installed-app title bar ECDoH green.
export const viewport: Viewport = { themeColor: "#0b6b3b" }

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en-ZA" suppressHydrationWarning className={`${montserrat.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-background">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
