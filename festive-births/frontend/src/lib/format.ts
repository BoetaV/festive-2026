export const nf = new Intl.NumberFormat("en-ZA")

export const fmtNum = (n: number | null | undefined) => (n === null || n === undefined ? "–" : nf.format(n))
export const fmtPct = (n: number | null | undefined) => (n === null || n === undefined ? "–" : `${n.toFixed(1)}%`)

export function fmtDate(iso: string | null | undefined, opts: Intl.DateTimeFormatOptions = { dateStyle: "medium" }) {
  if (!iso) return "–"
  const d = iso.length === 10 ? new Date(`${iso}T00:00:00`) : new Date(iso)
  return new Intl.DateTimeFormat("en-ZA", opts).format(d)
}

export const fmtDateTime = (iso: string | null | undefined) =>
  fmtDate(iso, { dateStyle: "medium", timeStyle: "short" })

export function timeAgo(iso: string | null | undefined) {
  if (!iso) return "never"
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (s < 60) return "just now"
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return `${Math.floor(s / 86400)} d ago`
}
