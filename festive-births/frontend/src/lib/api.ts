export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public fieldErrors: Record<string, string> = {},
  ) {
    super(message)
  }
}

async function parse(res: Response) {
  if (res.status === 204) return null
  const type = res.headers.get("content-type") ?? ""
  return type.includes("application/json") ? res.json() : res.text()
}

export async function api<T = unknown>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, headers, ...rest } = init
  const res = await fetch(path, {
    credentials: "same-origin",
    ...rest,
    headers: {
      // Required by the backend's CSRF check on every state-changing request.
      "X-CSRF-Protection": "1",
      ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  })
  const body = await parse(res)
  if (!res.ok) {
    const detail = body && typeof body === "object" ? (body as { detail?: unknown }).detail : body
    if (detail && typeof detail === "object" && "field_errors" in detail) {
      const fe = (detail as { field_errors: Record<string, string> }).field_errors
      throw new ApiError(res.status, "Please correct the highlighted fields.", fe)
    }
    if (res.status === 403 && detail === "password_change_required" && typeof window !== "undefined") {
      // Plain helper outside React, so a hard navigation is the right tool here.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = "/change-password"
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : `Request failed (${res.status})`)
  }
  return body as T
}

export const fetcher = <T,>(path: string) => api<T>(path)

/** Triggers a browser download for a binary endpoint (Excel / PDF). */
export async function download(path: string, fallbackName: string) {
  const res = await fetch(path, { credentials: "same-origin" })
  if (!res.ok) throw new ApiError(res.status, "Download failed")
  const blob = await res.blob()
  const name = /filename="([^"]+)"/.exec(res.headers.get("content-disposition") ?? "")?.[1] ?? fallbackName
  const url = URL.createObjectURL(blob)
  const a = Object.assign(document.createElement("a"), { href: url, download: name })
  a.click()
  URL.revokeObjectURL(url)
}

export function qs(params: Record<string, string | number | boolean | null | undefined>) {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== null && v !== undefined && v !== "") p.set(k, String(v))
  const s = p.toString()
  return s ? `?${s}` : ""
}
