"use client"

import { useState } from "react"
import useSWR from "swr"
import { toast } from "sonner"
import { FileSpreadsheetIcon, FileTextIcon, UsersIcon } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { EMPTY_FILTERS, FilterBar, type DashFilters } from "@/components/dashboard/filters"
import { Field } from "@/components/form-controls"
import { Input } from "@/components/ui/input"
import { PageHeader } from "@/components/page-header"
import { download, qs } from "@/lib/api"
import { can, useAuth } from "@/lib/auth"
import { fmtDate, fmtDateTime, fmtNum } from "@/lib/format"
import type { Meta } from "@/lib/types"

interface WeightRow {
  baby_id: number; delivery_id: number; report_date: string; facility: string | null; district: string
  mother_name: string; gender: string | null; weight: number; category: string
}
interface NilRow {
  id: number; report_date: string; time_slot: string | null; district: string; local_municipality: string | null
  facility: string | null; captured_by_name: string | null; created_at: string
}

function AbnormalWeights() {
  const { data } = useSWR<WeightRow[]>("/api/reports/abnormal-weights")
  const counts = (data ?? []).reduce<Record<string, number>>((m, r) => ({ ...m, [r.category]: (m[r.category] ?? 0) + 1 }), {})
  return (
    <Card>
      <CardHeader>
        <CardTitle>Abnormal birth weights</CardTitle>
        <CardDescription>Babies under 2,500 g or 4,000 g and over, lightest first.</CardDescription>
        <div className="flex flex-wrap gap-1.5 pt-1">
          {Object.entries(counts).map(([k, v]) => <Badge key={k} variant="outline">{k}: {v}</Badge>)}
        </div>
      </CardHeader>
      <CardContent className="max-h-[60vh] overflow-auto">
        <Table>
          <TableHeader className="sticky top-0 bg-card">
            <TableRow>
              <TableHead>Date</TableHead><TableHead>Facility</TableHead><TableHead>Mother</TableHead>
              <TableHead>Sex</TableHead><TableHead className="text-right">Weight</TableHead><TableHead>Category</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data?.length === 0 && <TableRow><TableCell colSpan={6} className="py-8 text-center text-muted-foreground">No abnormal weights recorded.</TableCell></TableRow>}
            {data?.map((r) => (
              <TableRow key={r.baby_id}>
                <TableCell>{fmtDate(r.report_date)}</TableCell>
                <TableCell><div>{r.facility}</div><div className="text-xs text-muted-foreground">{r.district}</div></TableCell>
                <TableCell>{r.mother_name}</TableCell>
                <TableCell>{r.gender}</TableCell>
                <TableCell className="text-right tabular-nums">{fmtNum(r.weight)} g</TableCell>
                <TableCell><Badge variant={r.weight < 1500 ? "destructive" : "secondary"}>{r.category}</Badge></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

function NilReports({ meta }: { meta?: Meta }) {
  const [filters, setFilters] = useState<DashFilters>(EMPTY_FILTERS)
  const [range, setRange] = useState({ start_date: "", end_date: "" })
  const { district, local_municipality, facility, report_date } = filters
  const { data } = useSWR<NilRow[]>(
    `/api/reports/nil${qs({ district, local_municipality, facility, start_date: report_date || range.start_date, end_date: report_date || range.end_date })}`,
  )
  return (
    <Card>
      <CardHeader>
        <CardTitle>NIL reports</CardTitle>
        <CardDescription>Time slots in which facilities reported no births.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        <FilterBar meta={meta} value={filters} onChange={setFilters} />
        {!report_date && (
          <div className="grid gap-2 sm:grid-cols-2">
            <Field label="From"><Input type="date" value={range.start_date} onChange={(e) => setRange({ ...range, start_date: e.target.value })} /></Field>
            <Field label="To"><Input type="date" value={range.end_date} onChange={(e) => setRange({ ...range, end_date: e.target.value })} /></Field>
          </div>
        )}
        <div className="max-h-[60vh] overflow-auto">
          <Table>
            <TableHeader className="sticky top-0 bg-card">
              <TableRow>
                <TableHead>Date</TableHead><TableHead>Time slot</TableHead><TableHead>Facility</TableHead>
                <TableHead>Captured by</TableHead><TableHead>Submitted</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.length === 0 && <TableRow><TableCell colSpan={5} className="py-8 text-center text-muted-foreground">No NIL reports for this selection.</TableCell></TableRow>}
              {data?.map((r) => (
                <TableRow key={r.id}>
                  <TableCell>{fmtDate(r.report_date)}</TableCell>
                  <TableCell>{r.time_slot}</TableCell>
                  <TableCell><div>{r.facility}</div><div className="text-xs text-muted-foreground">{r.local_municipality} · {r.district}</div></TableCell>
                  <TableCell>{r.captured_by_name ?? "–"}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{fmtDateTime(r.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        {data && <p className="text-xs text-muted-foreground">{data.length} NIL report(s)</p>}
      </CardContent>
    </Card>
  )
}

function Exports({ meta }: { meta?: Meta }) {
  const { user } = useAuth()
  const [filters, setFilters] = useState<DashFilters>(EMPTY_FILTERS)
  const run = (path: string, name: string) => download(path, name).then(() => toast.success("Download started")).catch(() => toast.error("Export failed"))

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><FileTextIcon className="size-4" /> Dashboard PDF report</CardTitle>
          <CardDescription>All KPIs and breakdown tables for the selected area, ready to print or email.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          <FilterBar meta={meta} value={filters} onChange={setFilters} />
          <div><Button onClick={() => run(`/api/dashboard/pdf${qs({ ...filters })}`, "dashboard_report.pdf")}>Generate PDF</Button></div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><FileSpreadsheetIcon className="size-4" /> Full data export</CardTitle>
          <CardDescription>Every delivery and baby in your scope as an Excel workbook (one row per baby).</CardDescription>
        </CardHeader>
        <CardContent><Button variant="outline" onClick={() => run("/api/deliveries/export", "festive_births.xlsx")}>Download Excel</Button></CardContent>
      </Card>
      {can.exportUsers(user) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><UsersIcon className="size-4" /> User list export</CardTitle>
            <CardDescription>All accounts with roles, allocations and sign-in status. Superusers only.</CardDescription>
          </CardHeader>
          <CardContent><Button variant="outline" onClick={() => run("/api/users/export", "users.xlsx")}>Download Excel</Button></CardContent>
        </Card>
      )}
      <p className="text-xs text-muted-foreground lg:col-span-2">Exports contain personal information and are recorded in the audit log. Store them securely.</p>
    </div>
  )
}

export default function ReportsPage() {
  const { data: meta } = useSWR<Meta>("/api/meta")
  return (
    <>
      <PageHeader title="Reports & exports" description="Clinical exception reports and downloadable data, scoped to your access." />
      <Tabs defaultValue="weights" className="gap-4">
        <TabsList>
          <TabsTrigger value="weights">Abnormal weights</TabsTrigger>
          <TabsTrigger value="nil">NIL reports</TabsTrigger>
          <TabsTrigger value="exports">Exports</TabsTrigger>
        </TabsList>
        <TabsContent value="weights"><AbnormalWeights /></TabsContent>
        <TabsContent value="nil"><NilReports meta={meta} /></TabsContent>
        <TabsContent value="exports"><Exports meta={meta} /></TabsContent>
      </Tabs>
    </>
  )
}
