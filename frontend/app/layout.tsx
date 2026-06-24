import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "Forge — Enterprise AI Platform",
  description: "AI-powered tools for engineering teams",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-black text-white">{children}</body>
    </html>
  )
}
