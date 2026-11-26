import type { NextConfig } from "next"

const isProd = process.env.NODE_ENV === "production"

// Next.js injects small inline bootstrap scripts, so script-src needs 'unsafe-inline' (a nonce-based
// policy would force every page to render dynamically). Everything else is locked to this origin:
// no third-party scripts, no framing, no plugins, and forms and <base> can't point elsewhere.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isProd ? "" : " 'unsafe-eval'"}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  `connect-src 'self'${isProd ? "" : " ws:"}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  ...(isProd ? ["upgrade-insecure-requests"] : []),
].join("; ")

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  ...(isProd ? [{ key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" }] : []),
]

const nextConfig: NextConfig = {
  output: "standalone", // small self-contained server for the Docker/Railway image
  poweredByHeader: false,
  // No remote images are used; keep the image optimiser to local files and refuse SVG.
  images: { remotePatterns: [], dangerouslyAllowSVG: false, contentDispositionType: "attachment" },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }]
  },
}

export default nextConfig
