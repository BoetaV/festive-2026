import type { NextRequest } from "next/server"

/**
 * Same-origin proxy to the FastAPI backend.
 *
 * Keeps the session cookie first-party (httpOnly, SameSite=Lax) and lets
 * BACKEND_URL be set at runtime on Railway instead of being baked in at build.
 */
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8010"

// Hop-by-hop / host-specific headers that must not be forwarded.
// Client-supplied forwarding headers are dropped too: only the proxy decides what the API sees as
// the client's address, host and scheme.
const DROP_REQUEST = new Set([
  "host", "connection", "content-length", "accept-encoding", "transfer-encoding", "upgrade",
  "forwarded", "x-forwarded-host", "x-forwarded-proto", "x-forwarded-port", "x-real-ip",
])
const MAX_BODY_BYTES = 1_000_000
const DROP_RESPONSE = new Set(["content-encoding", "content-length", "transfer-encoding", "connection", "set-cookie"])

async function forward(req: NextRequest) {
  const url = `${BACKEND_URL}${req.nextUrl.pathname}${req.nextUrl.search}`

  const headers = new Headers()
  req.headers.forEach((value, key) => {
    if (!DROP_REQUEST.has(key)) headers.set(key, value)
  })
  // Preserve the real client IP for rate limiting and the audit log. Only the right-most
  // X-Forwarded-For entry is trustworthy (appended by the platform edge); earlier entries
  // are client-supplied and could be spoofed to dodge the login rate limit.
  const chain = req.headers.get("x-forwarded-for")
  const ip = chain ? chain.split(",").at(-1)!.trim() : req.headers.get("x-real-ip")
  headers.delete("x-forwarded-for")
  if (ip) headers.set("x-forwarded-for", ip)

  const hasBody = !["GET", "HEAD"].includes(req.method)
  if (Number(req.headers.get("content-length") ?? 0) > MAX_BODY_BYTES) {
    return Response.json({ detail: "Request body too large" }, { status: 413 })
  }
  const body = hasBody ? await req.arrayBuffer() : undefined
  if (body && body.byteLength > MAX_BODY_BYTES) {
    return Response.json({ detail: "Request body too large" }, { status: 413 })
  }
  let upstream: Response
  try {
    upstream = await fetch(url, {
      method: req.method,
      headers,
      body,
      redirect: "manual",
      cache: "no-store",
    })
  } catch {
    return Response.json({ detail: "The API is unreachable. Is the backend running?" }, { status: 502 })
  }

  const out = new Headers()
  upstream.headers.forEach((value, key) => {
    if (!DROP_RESPONSE.has(key)) out.set(key, value)
  })
  for (const cookie of upstream.headers.getSetCookie()) out.append("set-cookie", cookie)

  return new Response(upstream.body, { status: upstream.status, headers: out })
}

export { forward as GET, forward as POST, forward as PUT, forward as DELETE, forward as PATCH }
