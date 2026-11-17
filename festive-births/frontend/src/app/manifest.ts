import type { MetadataRoute } from "next"

/**
 * Web app manifest: makes the dashboard installable from Chrome/Edge
 * ("Install app"), which places a Festive Births icon on the desktop and Start menu.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "Festive Births 2026/27 – Eastern Cape Department of Health",
    short_name: "Festive Births",
    description: "ECDoH festive season births dashboard and capture system.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#f6f8f5",
    theme_color: "#0b6b3b",
    lang: "en-ZA",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  }
}
