"use client"

import Link from "next/link"
import { useState } from "react"
import useSWR from "swr"
import { toast } from "sonner"
import { DownloadIcon, PencilIcon, PlusIcon, SearchIcon, Trash2Icon } from "lucide-react"
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { NativeSelect } from "@/components/form-controls"
import { PageHeader, Pagination } from "@/components/page-header"
import { api, download, qs } from "@/lib/api"
import { can, useAuth } from "@/lib/auth"
import { fmtDate } from "@/lib/format"
import type { Delivery, Meta, Paged } from "@/lib/types"

export default function DeliveriesPage() {
  const { user } = useAuth()
  const [q, setQ] = useState("")
  const [reportDate, setReportDate] = useState("")
  const [kind, setKind] = useState("")
  const [page, setPage] = useState(1)
  const [toDelete, setToDelete] = useState<Delivery | null>(null)

  const { data: meta } = useSWR<Meta>("/api/meta")
  const key = `/api/deliveries${qs({ q, report_date: reportDate, kind, page, page_size: 20 })}`
  const { data, mutate, isLoading } = useSWR<Paged<Delivery>>(key, { keepPreviousData: true })
  const editable = can.edit(user)

  async function confirmDelete() {
    if (!toDelete) return
    try {
      await api(`/api/deliveries/${toDelete.id}`, { method: "DELETE" })
      toast.success("Record deleted")
      mutate()
    } catch (e) {
      toast.error((e as Error).message)
    } finally {
      setToDelete(null)
    }
  }

  return (
    <>
      <PageHeader
        title="Delivery records"
        description="Records in your scope, newest first."
        actions={
          <>
            <Button variant="outline" onClick={() => download("/api/deliveries/export", "festive_births.xlsx").catch(() => toast.error("Export failed"))}>
              <DownloadIcon /> Excel
            </Button>
            {editable && (
              <Link href="/app/deliveries/new" className={buttonVariants()}>
                <PlusIcon /> Capture birth
              </Link>
            )}
          </>
        }
      />

      <div className="mb-3 grid gap-2 sm:grid-cols-[1fr_200px_160px]">
        <div className="relative">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search mother, facility or birth mode…"
            className="pl-8"
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1) }}
          />
        </div>
        <NativeSelect
          aria-label="Report date"
          value={reportDate}
          placeholder="All reporting days"
          options={(meta?.report_dates ?? []).map((d) => ({ value: d, label: fmtDate(d) }))}
          onChange={(e) => { setReportDate(e.target.value); setPage(1) }}
        />
        <NativeSelect
          aria-label="Record type"
          value={kind}
          placeholder="Births & NIL"
          options={[{ value: "births", label: "Births only" }, { value: "nil", label: "NIL reports only" }]}
          onChange={(e) => { setKind(e.target.value); setPage(1) }}
        />
      </div>

      <Card className="py-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date / time</TableHead>
                <TableHead>Facility</TableHead>
                <TableHead>Mother</TableHead>
                <TableHead>Mode</TableHead>
                <TableHead>Babies</TableHead>
                <TableHead>Captured by</TableHead>
                <TableHead className="w-20" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading && !data && (
                <TableRow><TableCell colSpan={7} className="py-10 text-center text-muted-foreground">Loading…</TableCell></TableRow>
              )}
              {data?.items.length === 0 && (
                <TableRow><TableCell colSpan={7} className="py-10 text-center text-muted-foreground">No records found.</TableCell></TableRow>
              )}
              {data?.items.map((d) => (
                <TableRow key={d.id}>
                  <TableCell className="whitespace-nowrap">
                    <div>{fmtDate(d.report_date)}</div>
                    <div className="text-xs text-muted-foreground">{d.delivery_time?.slice(0, 5) ?? d.time_slot}</div>
                  </TableCell>
                  <TableCell>
                    <div className="max-w-52 truncate">{d.facility}</div>
                    <div className="text-xs text-muted-foreground">{d.district}</div>
                  </TableCell>
                  <TableCell>
                    {d.no_births_to_report ? (
                      <Badge variant="secondary">NIL report</Badge>
                    ) : (
                      <>
                        <div>{d.mother_name} {d.mother_surname}</div>
                        <div className="text-xs text-muted-foreground">
                          Age {d.mother_age ?? "–"}{d.born_before_arrival && " · BBA"}
                        </div>
                      </>
                    )}
                  </TableCell>
                  <TableCell className="max-w-40 truncate text-sm">{d.birth_mode ?? "–"}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {d.babies.map((b, i) => (
                        <Badge key={i} variant="outline" className="tabular-nums">
                          {b.gender === "Male" ? "M" : "F"} {b.weight}g
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{d.captured_by_name ?? "–"}</TableCell>
                  <TableCell>
                    {editable && (
                      <div className="flex justify-end gap-1">
                        <Link href={`/app/deliveries/${d.id}`} aria-label="Edit" className={buttonVariants({ variant: "ghost", size: "icon-sm" })}>
                          <PencilIcon />
                        </Link>
                        <Button variant="ghost" size="icon-sm" aria-label="Delete" onClick={() => setToDelete(d)}>
                          <Trash2Icon className="text-destructive" />
                        </Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>
      {data && <Pagination page={page} pageSize={20} total={data.total} onPage={setPage} />}

      <AlertDialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this record?</AlertDialogTitle>
            <AlertDialogDescription>
              {toDelete?.no_births_to_report
                ? `NIL report for ${toDelete?.facility} (${toDelete?.time_slot}).`
                : `Delivery for ${toDelete?.mother_name} ${toDelete?.mother_surname} at ${toDelete?.facility}.`}{" "}
              This cannot be undone and will be recorded in the audit log.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={confirmDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
