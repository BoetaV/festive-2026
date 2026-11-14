"use client"

import Link from "next/link"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import useSWR from "swr"
import { toast } from "sonner"
import {
  ActivityIcon, AmbulanceIcon, AwardIcon, BuildingIcon, CircleSlashIcon, DownloadIcon, HeartPulseIcon,
  PlusIcon, ScaleIcon, ScissorsIcon, TrophyIcon, UsersRoundIcon,
} from "lucide-react"
import { Button, buttonVariants } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { KpiCard } from "@/components/kpi-card"
import { SexBarChart, SingleBarChart } from "@/components/charts"
import { ChartCard, type Column } from "@/components/dashboard/chart-card"
import { FilterBar, type DashFilters } from "@/components/dashboard/filters"
import { AccessSection } from "@/components/dashboard/access-section"
import { download, qs } from "@/lib/api"
import { can, useAuth } from "@/lib/auth"
import { fmtDate, fmtDateTime, fmtNum, fmtPct } from "@/lib/format"
import { cn } from "@/lib/utils"
import type { Dashboard, MF, Meta } from "@/lib/types"

const mfColumns = (first: string): Column<MF>[] => [
  { key: "name", label: first },
  { key: "male", label: "Male", numeric: true },
  { key: "female", label: "Female", numeric: true },
  { key: "total", label: "Total", numeric: true },
]

export function DashboardView() {
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()
  const { user } = useAuth()

  const filters: DashFilters = {
    report_date: params.get("report_date") ?? "",
    district: params.get("district") ?? "",
    local_municipality: params.get("local_municipality") ?? "",
    facility: params.get("facility") ?? "",
  }
  const query = qs({ ...filters })
  const { data: meta } = useSWR<Meta>("/api/meta")
  const { data, isLoading, error } = useSWR<Dashboard>(`/api/dashboard${query}`, { keepPreviousData: true, refreshInterval: 60_000 })

  const setFilters = (f: DashFilters) => router.replace(`${pathname}${qs({ ...f })}`, { scroll: false })

  const k = data?.kpis
  const totals = (key = "name", label = "Total") => ({
    [key]: label, male: fmtNum(k?.males), female: fmtNum(k?.females), total: fmtNum(k?.total_births),
  })
  const nonEmpty = (rows: MF[] | undefined) => (rows ?? []).filter((r) => r.total > 0)

  async function downloadPdf() {
    try {
      await download(`/api/dashboard/pdf${query}`, "dashboard_report.pdf")
    } catch {
      toast.error("Could not generate the PDF report.")
    }
  }

  return (
    <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-6 md:py-8">
      {/* ---------- Hero: green campaign band ---------- */}
      <section className="relative overflow-hidden rounded-2xl bg-primary text-primary-foreground shadow-sm">
        {/* Decorative overlapping rings from the ECDoH artwork */}
        <span aria-hidden className="brand-ring -top-28 -right-24 size-80 border-[28px] md:size-96" />
        <span aria-hidden className="brand-ring -bottom-40 -left-28 size-80 border-[28px]" />
        <div className="absolute inset-x-0 top-0 h-1.5 bg-gold" aria-hidden />

        <div className="relative grid items-center gap-8 px-6 py-8 md:grid-cols-[1fr_auto] md:px-10 md:py-10">
          <div className="grid gap-4">
            <div className="eyebrow flex items-center gap-2 text-gold">
              <TrophyIcon className="size-4" /> Festive season 2026/27 <TrophyIcon className="size-4" />
            </div>
            <h1 className="text-3xl leading-tight font-black tracking-tight md:text-5xl">
              Festive Season<br className="hidden sm:block" /> Births Dashboard
            </h1>
            <p className="text-sm font-medium text-primary-foreground/85 md:text-base">
              {data ? `${data.scope.name} · ${filters.report_date ? fmtDate(filters.report_date, { dateStyle: "long" }) : "all reporting days"}` : "Eastern Cape"}
            </p>
            {meta?.report_dates?.length ? (
              <div className="flex w-fit items-center gap-2 rounded-full bg-gold px-4 py-1.5 text-xs font-extrabold tracking-wide text-gold-foreground uppercase">
                <AwardIcon className="size-4" />
                Reporting days: {meta.report_dates.map((d) => fmtDate(d, { day: "numeric", month: "short" })).join(" · ")}
              </div>
            ) : null}
            <div className="flex items-center gap-2 text-xs font-medium text-primary-foreground/80">
              <span className="relative flex size-2">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-gold opacity-70" />
                <span className="relative inline-flex size-2 rounded-full bg-gold" />
              </span>
              Live · refreshes every minute
              {data?.last_updated && <> · last capture {fmtDateTime(data.last_updated)}</>}
            </div>
            <div className="flex flex-wrap gap-2 pt-1">
              {user && (
                <Button onClick={downloadPdf} className="bg-gold font-bold text-gold-foreground hover:bg-gold/90">
                  <DownloadIcon /> PDF report
                </Button>
              )}
              {can.edit(user) && (
                <Link href="/app/deliveries/new" className={cn(buttonVariants({ variant: "outline" }), "border-white/60 bg-transparent font-bold text-white hover:bg-white/10 hover:text-white")}>
                  <PlusIcon /> Capture birth
                </Link>
              )}
            </div>
          </div>

          {/* Headline figure: white disc with gold ring, like the "110 FACILITIES" badge */}
          <div className="grid justify-items-center gap-3">
            <div className="grid size-52 place-items-center rounded-full border-[10px] border-gold bg-white text-center shadow-[0_0_0_10px_var(--brand-ring)] md:size-60">
              <div>
                <div className="text-6xl leading-none font-black tracking-tighter text-[#0b6b3b] tabular-nums md:text-7xl">
                  {k ? fmtNum(k.total_births) : "–"}
                </div>
                <div className="eyebrow mt-2 text-sm text-[#2a5ca8]">Births</div>
              </div>
            </div>
            {k && (
              <div className="grid w-56 gap-1.5 text-xs font-semibold">
                <div className="flex h-2 overflow-hidden rounded-full bg-white/20" aria-hidden>
                  <div className="bg-white" style={{ width: `${k.total_births ? (100 * k.males) / k.total_births : 0}%` }} />
                  <div className="bg-gold" style={{ width: `${k.total_births ? (100 * k.females) / k.total_births : 0}%` }} />
                </div>
                <div className="flex justify-between">
                  <span>{fmtNum(k.males)} male</span>
                  <span className="text-gold">{fmtNum(k.females)} female</span>
                </div>
                <div className="text-center text-primary-foreground/80">
                  Average birth weight {k.average_weight ? `${fmtNum(k.average_weight)} g` : "–"}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      <FilterBar meta={meta} value={filters} onChange={setFilters} />

      {error && <p className="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">Could not load the dashboard: {error.message}</p>}

      {/* ---------- KPI tiles ---------- */}
      {!k && isLoading ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
      ) : k ? (
        <section aria-label="Key indicators" className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <KpiCard label="Deliveries" icon={ActivityIcon} value={fmtNum(k.deliveries)} sub="Mothers delivered" />
          <KpiCard label="NIL reports" icon={CircleSlashIcon} value={fmtNum(k.nil_reports)} sub="Time slots with no births" />
          <KpiCard label="Facilities reporting" icon={BuildingIcon} value={fmtNum(k.facilities_reporting)} sub="Births or NIL submitted" />
          <KpiCard label="Low birth weight" icon={ScaleIcon} value={fmtNum(k.low_birth_weight)} sub={`${fmtPct(k.low_birth_weight_rate)} of babies under 2.5 kg`} />
          <KpiCard label="Teen births" icon={UsersRoundIcon} value={fmtNum(k.teen_births)} sub={`${fmtPct(k.teen_birth_rate)} to mothers aged 10–19`} />
          <KpiCard label="Caesarean rate" icon={ScissorsIcon} value={fmtPct(k.caesarean_rate)} sub="Elective + emergency" />
          <KpiCard label="Born before arrival" icon={AmbulanceIcon} value={fmtNum(k.born_before_arrival)} sub="BBA deliveries" />
          <KpiCard label="Multiple births" icon={HeartPulseIcon} value={fmtNum(k.multiple_birth_sets)} sub="Sets of twins or more" />
        </section>
      ) : null}

      {/* ---------- Breakdowns ---------- */}
      {data && (
        <>
          <div className="grid gap-4 lg:grid-cols-5">
            <ChartCard
              className="lg:col-span-3"
              title={`Births per ${data.scope.level.toLowerCase()}`}
              description={data.scope.name}
              rows={data.by_area}
              columns={mfColumns(data.scope.level)}
              total={totals("name", `${data.scope.name} total`)}
              chart={<SexBarChart data={data.by_area} horizontal labelWidth={data.scope.level === "Facility" ? 170 : 130} />}
            />
            <ChartCard
              className="lg:col-span-2"
              title="Mother's age group"
              description="Age on the day of delivery"
              rows={data.age_groups}
              columns={mfColumns("Age group")}
              chart={<SexBarChart data={data.age_groups} />}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <ChartCard
              title="Births by hour of day"
              description="Time of delivery"
              rows={data.by_hour.map((h) => ({ name: `${String(h.hour).padStart(2, "0")}:00`, total: h.total }))}
              columns={[{ key: "name", label: "Hour" }, { key: "total", label: "Births", numeric: true }]}
              chart={<SingleBarChart data={data.by_hour} dataKey="total" nameKey="hour" label="Births" tickFormatter={(v) => `${String(v).padStart(2, "0")}h`} />}
            />
            <ChartCard
              title="Mode of delivery"
              rows={nonEmpty(data.birth_modes)}
              columns={mfColumns("Mode")}
              total={totals()}
              chart={<SexBarChart data={nonEmpty(data.birth_modes)} horizontal labelWidth={170} />}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <ChartCard
              title="Birth weight category"
              rows={data.weight_bands}
              columns={mfColumns("Category")}
              total={totals()}
              chart={<SexBarChart data={data.weight_bands.map((w) => ({ ...w, name: w.name.replace(/ \(.*\)/, "") }))} horizontal labelWidth={92} />}
            />
            <ChartCard
              title="Births per time slot"
              rows={data.time_slots}
              columns={mfColumns("Time slot")}
              total={totals()}
              chart={<SexBarChart data={data.time_slots.map((s) => ({ ...s, name: s.name.replace(" - ", "–") }))} />}
            />
            <ChartCard
              title="Births per facility type"
              rows={data.facility_types}
              columns={mfColumns("Facility type")}
              total={totals()}
              chart={<SexBarChart data={data.facility_types} horizontal labelWidth={120} />}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <ChartCard
              title="Teenage pregnancies by facility"
              description="Babies born to mothers aged 10–19"
              rows={data.teen_by_facility}
              columns={[
                { key: "facility", label: "Facility" },
                { key: "age_10_14", label: "10–14 yrs", numeric: true },
                { key: "age_15_19", label: "15–19 yrs", numeric: true },
              ]}
              total={{
                facility: "Total",
                age_10_14: fmtNum(data.teen_by_facility.reduce((s, r) => s + r.age_10_14, 0)),
                age_15_19: fmtNum(data.teen_by_facility.reduce((s, r) => s + r.age_15_19, 0)),
              }}
              emptyText="No teenage pregnancies recorded for this selection."
            />
            <ChartCard
              title="Multiple births per facility"
              description="Number of sets"
              rows={data.multiple_births}
              columns={[
                { key: "facility", label: "Facility" },
                { key: "twins", label: "Twins", numeric: true },
                { key: "triplets", label: "Triplets", numeric: true },
                { key: "quadruplets", label: "Quads", numeric: true },
                { key: "quintuplets", label: "Quints", numeric: true },
              ]}
              emptyText="No multiple births recorded for this selection."
            />
          </div>
        </>
      )}

      <div className="mt-4 border-t pt-8">
        <AccessSection />
      </div>
    </div>
  )
}
