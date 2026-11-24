"use client"

import { Fragment, useState } from "react"
import useSWR from "swr"
import { CheckIcon, ChevronRightIcon } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { qs } from "@/lib/api"
import { fmtDate, fmtNum } from "@/lib/format"
import { cn } from "@/lib/utils"
import type { Reporting, ReportingFacility, SlotCounts, SlotStatus } from "@/lib/types"
import type { DashFilters } from "./filters"

const STATUS: Record<SlotStatus, { label: string; dot: string; pill: string }> = {
  births: { label: "Births reported", dot: "bg-primary", pill: "bg-primary/12 text-primary" },
  nil: { label: "NIL reported", dot: "bg-gold", pill: "bg-gold/30 text-brand-deep" },
  missing: { label: "Not reported", dot: "bg-destructive", pill: "bg-destructive/10 text-destructive ring-1 ring-destructive/30" },
  pending: { label: "Not yet due", dot: "bg-muted-foreground/40", pill: "text-muted-foreground" },
}

function FacilityCell({ status, births }: { status: SlotStatus; births: number }) {
  const text = status === "births" ? `${births} birth${births === 1 ? "" : "s"}`
    : status === "nil" ? "NIL" : status === "missing" ? "Not reported" : "Not due"
  return (
    <span className={cn("inline-flex rounded-full px-2 py-0.5 text-xs font-semibold whitespace-nowrap", STATUS[status].pill)}>
      {text}
    </span>
  )
}

/** Facilities per status for a district or sub-district: births · NIL · not reported. */
function CountsCell({ c }: { c: SlotCounts }) {
  const total = c.births + c.nil + c.missing + c.pending
  if (c.pending === total) return <span className="text-xs text-muted-foreground">Not due</span>
  return (
    <span className="inline-flex items-center gap-2.5 text-xs font-semibold tabular-nums">
      {(c.pending ? ["births", "nil", "pending"] as const : ["births", "nil", "missing"] as const).map((k) => (
        <span key={k} title={`${STATUS[k].label}: ${c[k]} facilities`}
          className={cn("inline-flex items-center gap-1", c[k] === 0 && "opacity-35")}>
          <span aria-hidden className={cn("size-2 rounded-full", STATUS[k].dot)} />
          <span className="sr-only">{STATUS[k].label}:</span>
          <span className={cn(k === "missing" && c[k] > 0 && "text-destructive")}>{c[k]}</span>
        </span>
      ))}
    </span>
  )
}

function Outstanding({ n }: { n: number }) {
  return n > 0
    ? <span className="font-bold text-destructive tabular-nums">{fmtNum(n)}</span>
    : <CheckIcon className="ml-auto size-4 text-primary" aria-label="Nothing outstanding" />
}

function Toggle({ open, onClick, label }: { open: boolean; onClick: () => void; label: string }) {
  return (
    <button type="button" onClick={onClick} aria-expanded={open} aria-label={`${open ? "Collapse" : "Expand"} ${label}`}
      className="grid size-5 shrink-0 place-items-center rounded text-muted-foreground hover:bg-muted">
      <ChevronRightIcon className={cn("size-4 transition-transform", open && "rotate-90")} />
    </button>
  )
}

export function ReportingTable({ filters }: { filters: DashFilters }) {
  const { data, isLoading, error } = useSWR<Reporting>(
    `/api/dashboard/reporting${qs({ ...filters })}`, { keepPreviousData: true, refreshInterval: 60_000 })
  const [open, setOpen] = useState<Set<string>>(new Set())
  const [followUp, setFollowUp] = useState(false)

  if (error) return null
  if (!data) return isLoading ? <Skeleton className="h-64" /> : null

  // A single district or sub-district in scope opens straight away.
  const single = data.districts.length === 1
  const isOpen = (key: string, autoOpen: boolean) => followUp || autoOpen || open.has(key)
  const flip = (key: string) => setOpen((s) => { const n = new Set(s); if (n.has(key)) n.delete(key); else n.add(key); return n })
  const keep = (x: { outstanding: number }) => !followUp || x.outstanding > 0
  const slotCols = data.time_slots.length

  const facilityRow = (f: ReportingFacility, key: string) => (
    <TableRow key={key} className={cn(f.outstanding > 0 && "bg-destructive/[0.03]")}>
      <TableCell className="pl-14">
        <div className="font-medium">{f.name}</div>
      </TableCell>
      <TableCell className="text-xs text-muted-foreground">{f.facility_type ?? "–"}</TableCell>
      {f.slots.map((s, i) => <TableCell key={i} className="text-center"><FacilityCell {...s} /></TableCell>)}
      <TableCell className="text-right"><Outstanding n={f.outstanding} /></TableCell>
    </TableRow>
  )

  return (
    <Card className="gap-3">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
        <div className="grid gap-1 border-l-4 border-gold pl-3">
          <CardTitle className="font-extrabold text-brand-deep">Reporting per time slot</CardTitle>
          <CardDescription>
            {fmtDate(data.report_date, { dateStyle: "long" })} · as at {fmtDate(data.as_at, { timeStyle: "short" })} ·{" "}
            {fmtNum(data.facility_count)} facilities
            {!filters.report_date && " · choose a reporting day above to change the day"}
          </CardDescription>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className={cn("text-xl font-extrabold tabular-nums", data.outstanding > 0 ? "text-destructive" : "text-primary")}>
              {fmtNum(data.outstanding)}
            </div>
            <div className="text-xs text-muted-foreground">time slots not reported</div>
          </div>
          <label className="flex items-center gap-2 text-sm font-medium">
            <Switch checked={followUp} onCheckedChange={(v) => setFollowUp(!!v)} />
            Follow-up only
          </label>
        </div>
      </CardHeader>
      <CardContent className="grid min-w-0 gap-3">
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground" aria-label="Legend">
          {(Object.keys(STATUS) as SlotStatus[]).map((k) => (
            <li key={k} className="inline-flex items-center gap-1.5">
              <span aria-hidden className={cn("size-2.5 rounded-full", STATUS[k].dot)} />{STATUS[k].label}
            </li>
          ))}
          <li>District and sub-district rows count facilities.</li>
        </ul>
        <div className="max-h-[36rem] overflow-auto rounded-lg border">
          <Table>
            <TableHeader className="sticky top-0 z-10 bg-secondary [&_th]:font-bold [&_th]:text-brand-deep">
              <TableRow>
                <TableHead className="min-w-64">District / sub-district / facility</TableHead>
                <TableHead>Facilities</TableHead>
                {data.time_slots.map((s, i) => (
                  <TableHead key={s} className="text-center">
                    {s.replace(" - ", "–")}
                    {!data.slots_due[i] && <span className="block text-[10px] font-medium text-muted-foreground">not yet due</span>}
                  </TableHead>
                ))}
                <TableHead className="text-right">Not reported</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.districts.filter(keep).map((d) => {
                const dOpen = isOpen(d.name, single)
                const singleMuni = single && d.municipalities.length === 1
                return (
                  <Fragment key={d.name}>
                    <TableRow className="bg-muted/40 font-semibold">
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          <Toggle open={dOpen} onClick={() => flip(d.name)} label={d.name} />
                          <span className="font-bold text-brand-deep">{d.name}</span>
                        </div>
                      </TableCell>
                      <TableCell className="tabular-nums">{d.facility_count}</TableCell>
                      {d.slots.map((c, i) => <TableCell key={i} className="text-center"><CountsCell c={c} /></TableCell>)}
                      <TableCell className="text-right"><Outstanding n={d.outstanding} /></TableCell>
                    </TableRow>
                    {dOpen && d.municipalities.filter(keep).map((m) => {
                      const key = `${d.name}/${m.name}`
                      const mOpen = isOpen(key, singleMuni)
                      return (
                        <Fragment key={key}>
                          <TableRow>
                            <TableCell className="pl-8">
                              <div className="flex items-center gap-1.5">
                                <Toggle open={mOpen} onClick={() => flip(key)} label={m.name} />
                                <span className="font-semibold">{m.name}</span>
                              </div>
                            </TableCell>
                            <TableCell className="tabular-nums">{m.facility_count}</TableCell>
                            {m.slots.map((c, i) => <TableCell key={i} className="text-center"><CountsCell c={c} /></TableCell>)}
                            <TableCell className="text-right"><Outstanding n={m.outstanding} /></TableCell>
                          </TableRow>
                          {mOpen && m.facilities.filter(keep).map((f) => facilityRow(f, `${key}/${f.name}`))}
                        </Fragment>
                      )
                    })}
                  </Fragment>
                )
              })}
              {followUp && data.outstanding === 0 && (
                <TableRow>
                  <TableCell colSpan={slotCols + 3} className="py-8 text-center text-muted-foreground">
                    Every facility has reported for all time slots that are due.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
            {data.districts.length > 1 && (
              <TableFooter>
                <TableRow>
                  <TableCell className="font-bold">Province</TableCell>
                  <TableCell className="font-bold tabular-nums">{data.facility_count}</TableCell>
                  {data.totals.map((c, i) => <TableCell key={i} className="text-center"><CountsCell c={c} /></TableCell>)}
                  <TableCell className="text-right"><Outstanding n={data.outstanding} /></TableCell>
                </TableRow>
              </TableFooter>
            )}
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
