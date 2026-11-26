"use client"

import { useRouter } from "next/navigation"
import { useMemo, useState } from "react"
import useSWR from "swr"
import { toast } from "sonner"
import { BabyIcon, CircleSlashIcon, Loader2Icon, MapPinIcon, UserIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Field, NativeSelect } from "@/components/form-controls"
import { api, ApiError } from "@/lib/api"
import { can, useAuth } from "@/lib/auth"
import { fmtDate } from "@/lib/format"
import type { Delivery, Meta } from "@/lib/types"
import { cn } from "@/lib/utils"

type BabyRow = { gender: "" | "Male" | "Female"; weight: string }

function slotFor(t: string): string {
  if (!t) return ""
  const [h, m] = t.split(":").map(Number)
  const mins = h * 60 + m
  if (mins === 0) return "18:01 - 24:00"
  if (mins <= 360) return "00:01 - 06:00"
  if (mins <= 720) return "06:01 - 12:00"
  if (mins <= 1080) return "12:01 - 18:00"
  return "18:01 - 24:00"
}

function ageOn(dob: string, on: string): number | null {
  if (!dob || !on) return null
  const b = new Date(dob), d = new Date(on)
  return d.getFullYear() - b.getFullYear() - (d.getMonth() < b.getMonth() || (d.getMonth() === b.getMonth() && d.getDate() < b.getDate()) ? 1 : 0)
}

export function DeliveryForm({ initial }: { initial?: Delivery }) {
  const router = useRouter()
  const { user } = useAuth()
  const { data: meta } = useSWR<Meta>("/api/meta")

  const lockFacility = user?.role === "user"
  const lockDistrict = lockFacility || user?.role === "admin"

  const [f, setF] = useState(() => ({
    district: initial?.district ?? "",
    local_municipality: initial?.local_municipality ?? "",
    facility: initial?.facility ?? "",
    report_date: initial?.report_date ?? "",
    no_births_to_report: initial?.no_births_to_report ?? false,
    time_slot: initial?.time_slot ?? "",
    born_before_arrival: initial?.born_before_arrival ?? false,
    delivery_time: initial?.delivery_time?.slice(0, 5) ?? "",
    mother_name: initial?.mother_name ?? "",
    mother_surname: initial?.mother_surname ?? "",
    mother_dob: initial?.mother_dob ?? "",
    birth_mode: initial?.birth_mode ?? "",
    gravidity: initial?.gravidity?.toString() ?? "",
    parity: initial?.parity?.toString() ?? "",
  }))
  const [babies, setBabies] = useState<BabyRow[]>(
    initial?.babies.length
      ? initial.babies.map((b) => ({ gender: b.gender ?? "", weight: b.weight?.toString() ?? "" }))
      : [{ gender: "", weight: "" }],
  )
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)

  // Users are pinned to their own facility/district; show that instead of the editable value.
  const district = lockDistrict ? (user?.district ?? "") : f.district
  const muni = lockFacility ? (user?.local_municipality ?? "") : f.local_municipality
  const facility = lockFacility ? (user?.facility ?? "") : f.facility
  const facilityType = meta?.facility_types[facility] ?? ""
  const age = useMemo(() => ageOn(f.mother_dob, f.report_date), [f.mother_dob, f.report_date])
  const derivedSlot = slotFor(f.delivery_time)

  const set = <K extends keyof typeof f>(k: K, v: (typeof f)[K]) => setF((s) => ({ ...s, [k]: v }))
  const err = (k: string) => errors[k]

  function setBabyCount(n: number) {
    setBabies((b) => Array.from({ length: n }, (_, i) => b[i] ?? { gender: "", weight: "" }))
  }

  async function submit(again: boolean) {
    setBusy(true)
    setErrors({})
    const body = {
      district, local_municipality: muni, facility,
      report_date: f.report_date,
      no_births_to_report: f.no_births_to_report,
      time_slot: f.no_births_to_report ? f.time_slot : null,
      born_before_arrival: f.born_before_arrival,
      delivery_time: f.delivery_time || null,
      mother_name: f.mother_name, mother_surname: f.mother_surname,
      mother_dob: f.mother_dob || null,
      birth_mode: f.birth_mode,
      gravidity: f.gravidity === "" ? null : Number(f.gravidity),
      parity: f.parity === "" ? null : Number(f.parity),
      babies: f.no_births_to_report ? [] : babies.map((b) => ({ gender: b.gender || null, weight: b.weight === "" ? null : Number(b.weight) })),
    }
    try {
      if (initial) {
        await api(`/api/deliveries/${initial.id}`, { method: "PUT", json: body })
        toast.success("Record updated")
        router.push("/app/deliveries")
      } else {
        await api("/api/deliveries", { method: "POST", json: body })
        toast.success(f.no_births_to_report ? "NIL report submitted" : "Delivery captured")
        if (again) {
          setF((s) => ({ ...s, delivery_time: "", mother_name: "", mother_surname: "", mother_dob: "", birth_mode: "", gravidity: "", parity: "", born_before_arrival: false, time_slot: "" }))
          setBabies([{ gender: "", weight: "" }])
          window.scrollTo({ top: 0, behavior: "smooth" })
        } else {
          router.push("/app/deliveries")
        }
      }
    } catch (e) {
      const apiErr = e as ApiError
      setErrors(apiErr.fieldErrors ?? {})
      toast.error(apiErr.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form
      className="grid gap-4"
      onSubmit={(e) => { e.preventDefault(); submit(false) }}
      noValidate
    >
      {/* Read-only once the season is locked (or for roles that can't capture); the API enforces it too. */}
      <fieldset disabled={!can.edit(user)} className="contents">
      {/* ---------- Location & reporting ---------- */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><MapPinIcon className="size-4" /> Location & reporting day</CardTitle>
          {lockDistrict && (
            <CardDescription>
              {lockFacility ? "Locked to your facility." : "Locked to your district."}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Field label="District" error={err("district")}>
            <NativeSelect
              value={district}
              disabled={lockDistrict}
              placeholder="Select district"
              options={meta?.districts ?? []}
              aria-invalid={!!err("district")}
              onChange={(e) => setF((s) => ({ ...s, district: e.target.value, local_municipality: "", facility: "" }))}
            />
          </Field>
          <Field label="Sub-district" error={err("local_municipality")}>
            <NativeSelect
              value={muni}
              disabled={lockFacility || !district}
              placeholder="Select sub-district"
              options={(lockFacility && muni ? [muni] : meta?.municipalities[district]) ?? []}
              aria-invalid={!!err("local_municipality")}
              onChange={(e) => setF((s) => ({ ...s, local_municipality: e.target.value, facility: "" }))}
            />
          </Field>
          <Field label="Facility" error={err("facility")} hint={facilityType && `Facility type: ${facilityType}`}>
            <NativeSelect
              value={facility}
              disabled={lockFacility || !muni}
              placeholder="Select facility"
              options={(lockFacility && facility ? [facility] : meta?.facilities[muni]) ?? []}
              aria-invalid={!!err("facility")}
              onChange={(e) => set("facility", e.target.value)}
            />
          </Field>
          <Field label="Report date" error={err("report_date")}>
            <NativeSelect
              value={f.report_date}
              placeholder="Select reporting day"
              options={(meta?.report_dates ?? []).map((d) => ({ value: d, label: fmtDate(d, { dateStyle: "full" }) }))}
              aria-invalid={!!err("report_date")}
              onChange={(e) => set("report_date", e.target.value)}
            />
          </Field>
          <div className="flex items-center gap-3 rounded-lg border p-3 sm:col-span-2">
            <Switch
              id="nil"
              checked={f.no_births_to_report}
              onCheckedChange={(v) => set("no_births_to_report", !!v)}
            />
            <Label htmlFor="nil" className="grid gap-0.5">
              <span className="flex items-center gap-1.5"><CircleSlashIcon className="size-3.5" /> No births to report (NIL report)</span>
              <span className="text-xs font-normal text-muted-foreground">Submit once per time slot in which no babies were born.</span>
            </Label>
          </div>
          {f.no_births_to_report && (
            <Field label="Time slot" error={err("time_slot")}>
              <NativeSelect
                value={f.time_slot}
                placeholder="Select time slot"
                options={meta?.time_slots ?? []}
                aria-invalid={!!err("time_slot")}
                onChange={(e) => set("time_slot", e.target.value)}
              />
            </Field>
          )}
        </CardContent>
      </Card>

      {!f.no_births_to_report && (
        <>
          {/* ---------- Mother ---------- */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><UserIcon className="size-4" /> Mother & delivery</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Field label="Name" error={err("mother_name")}>
                <Input value={f.mother_name} aria-invalid={!!err("mother_name")} onChange={(e) => set("mother_name", e.target.value)} />
              </Field>
              <Field label="Surname" error={err("mother_surname")}>
                <Input value={f.mother_surname} aria-invalid={!!err("mother_surname")} onChange={(e) => set("mother_surname", e.target.value)} />
              </Field>
              <Field
                label="Date of birth"
                error={err("mother_dob")}
                hint={age !== null ? <span className={cn((age < 10 || age > 65) && "text-destructive")}>Age on delivery: {age}{age <= 19 && age >= 10 ? " (teen)" : ""}</span> : undefined}
              >
                <Input type="date" value={f.mother_dob} aria-invalid={!!err("mother_dob")} onChange={(e) => set("mother_dob", e.target.value)} />
              </Field>
              <Field label="Time of delivery" error={err("delivery_time")} hint={derivedSlot && `Time slot: ${derivedSlot}`}>
                <Input type="time" value={f.delivery_time} aria-invalid={!!err("delivery_time")} onChange={(e) => set("delivery_time", e.target.value)} />
              </Field>
              <Field label="Mode of delivery" error={err("birth_mode")}>
                <NativeSelect
                  value={f.birth_mode}
                  placeholder="Select mode"
                  options={meta?.birth_modes ?? []}
                  aria-invalid={!!err("birth_mode")}
                  onChange={(e) => set("birth_mode", e.target.value)}
                />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Gravidity" error={err("gravidity")}>
                  <Input type="number" min={0} max={30} value={f.gravidity} onChange={(e) => set("gravidity", e.target.value)} />
                </Field>
                <Field label="Parity" error={err("parity")}>
                  <Input type="number" min={0} max={30} value={f.parity} aria-invalid={!!err("parity")} onChange={(e) => set("parity", e.target.value)} />
                </Field>
              </div>
              <label className="flex items-center gap-2 text-sm sm:col-span-2 lg:col-span-3">
                <Checkbox checked={f.born_before_arrival} onCheckedChange={(v) => set("born_before_arrival", !!v)} />
                Born before arrival (BBA)
              </label>
            </CardContent>
          </Card>

          {/* ---------- Babies ---------- */}
          <Card>
            <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
              <div className="grid gap-1">
                <CardTitle className="flex items-center gap-2"><BabyIcon className="size-4" /> Babies</CardTitle>
                <CardDescription>Twins and higher-order births are counted as one delivery.</CardDescription>
              </div>
              <NativeSelect
                aria-label="Number of babies"
                className="w-40"
                value={String(babies.length)}
                options={[1, 2, 3, 4, 5].map((n) => ({ value: String(n), label: n === 1 ? "1 baby" : `${n} babies` }))}
                onChange={(e) => setBabyCount(Number(e.target.value))}
              />
            </CardHeader>
            <CardContent className="grid gap-3">
              {err("babies") && <p className="text-xs text-destructive">{err("babies")}</p>}
              {babies.map((b, i) => (
                <div key={i} className="grid items-start gap-3 rounded-lg border p-3 sm:grid-cols-[80px_1fr_1fr]">
                  <div className="pt-1.5 text-sm font-medium">Baby {i + 1}</div>
                  <Field label="Sex" error={err(`babies.${i}.gender`)}>
                    <NativeSelect
                      value={b.gender}
                      placeholder="Select"
                      options={["Male", "Female"]}
                      aria-invalid={!!err(`babies.${i}.gender`)}
                      onChange={(e) => setBabies((s) => s.map((x, j) => (j === i ? { ...x, gender: e.target.value as BabyRow["gender"] } : x)))}
                    />
                  </Field>
                  <Field
                    label="Weight (grams)"
                    error={err(`babies.${i}.weight`)}
                    hint={b.weight && Number(b.weight) < 2500 ? "Low birth weight" : b.weight && Number(b.weight) >= 4000 ? "High birth weight" : undefined}
                  >
                    <Input
                      type="number"
                      inputMode="numeric"
                      min={200}
                      max={7000}
                      placeholder="e.g. 3200"
                      value={b.weight}
                      aria-invalid={!!err(`babies.${i}.weight`)}
                      onChange={(e) => setBabies((s) => s.map((x, j) => (j === i ? { ...x, weight: e.target.value } : x)))}
                    />
                  </Field>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}

      </fieldset>
      <div className="flex flex-wrap justify-end gap-2">
        <Button type="button" variant="ghost" onClick={() => router.back()}>{can.edit(user) ? "Cancel" : "Back"}</Button>
        {can.edit(user) && <>
        {!initial && (
          <Button type="button" variant="outline" disabled={busy} onClick={() => submit(true)}>
            Save & capture another
          </Button>
        )}
        <Button type="submit" disabled={busy}>
          {busy && <Loader2Icon className="animate-spin" />}
          {initial ? "Update record" : f.no_births_to_report ? "Submit NIL report" : "Save delivery"}
        </Button>
        </>}
      </div>
    </form>
  )
}
