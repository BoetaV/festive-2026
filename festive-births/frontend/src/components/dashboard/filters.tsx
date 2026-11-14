"use client"

import { RotateCcwIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { NativeSelect } from "@/components/form-controls"
import { fmtDate } from "@/lib/format"
import type { Meta } from "@/lib/types"

export interface DashFilters {
  report_date: string
  district: string
  local_municipality: string
  facility: string
}

export const EMPTY_FILTERS: DashFilters = { report_date: "", district: "", local_municipality: "", facility: "" }

export function FilterBar({
  meta,
  value,
  onChange,
}: {
  meta: Meta | undefined
  value: DashFilters
  onChange: (f: DashFilters) => void
}) {
  const munis = value.district ? (meta?.municipalities[value.district] ?? []) : []
  const facilities = value.local_municipality ? (meta?.facilities[value.local_municipality] ?? []) : []
  const active = Object.values(value).some(Boolean)

  return (
    <div className="grid grid-cols-2 gap-2 md:grid-cols-[repeat(4,minmax(0,1fr))_auto]">
      <NativeSelect
        aria-label="Report date"
        value={value.report_date}
        placeholder="All reporting days"
        options={(meta?.report_dates ?? []).map((d) => ({ value: d, label: fmtDate(d, { dateStyle: "long" }) }))}
        onChange={(e) => onChange({ ...value, report_date: e.target.value })}
      />
      <NativeSelect
        aria-label="District"
        value={value.district}
        placeholder="All districts"
        options={meta?.districts ?? []}
        onChange={(e) => onChange({ ...value, district: e.target.value, local_municipality: "", facility: "" })}
      />
      <NativeSelect
        aria-label="Sub-district"
        value={value.local_municipality}
        placeholder="All sub-districts"
        options={munis}
        disabled={!value.district}
        onChange={(e) => onChange({ ...value, local_municipality: e.target.value, facility: "" })}
      />
      <NativeSelect
        aria-label="Facility"
        value={value.facility}
        placeholder="All facilities"
        options={facilities}
        disabled={!value.local_municipality}
        onChange={(e) => onChange({ ...value, facility: e.target.value })}
      />
      <Button variant="outline" disabled={!active} onClick={() => onChange(EMPTY_FILTERS)} className="col-span-2 md:col-span-1">
        <RotateCcwIcon /> Reset
      </Button>
    </div>
  )
}
