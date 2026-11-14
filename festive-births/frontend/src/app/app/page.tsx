"use client"

import Link from "next/link"
import useSWR from "swr"
import { ArrowRightIcon, BabyIcon, CircleSlashIcon, ClockIcon, KeyRoundIcon, PlusIcon, ShieldCheckIcon } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { KpiCard } from "@/components/kpi-card"
import { PageHeader } from "@/components/page-header"
import { can, useAuth } from "@/lib/auth"
import { fmtDate, fmtDateTime, fmtNum, timeAgo } from "@/lib/format"
import { ROLE_LABEL, type Delivery, type Paged } from "@/lib/types"

export default function OverviewPage() {
  const { user } = useAuth()
  const { data: births } = useSWR<Paged<Delivery>>("/api/deliveries?kind=births&page_size=6")
  const { data: nil } = useSWR<Paged<Delivery>>("/api/deliveries?kind=nil&page_size=1")
  const babies = births?.items.reduce((s, d) => s + d.babies.length, 0)

  const scope = user?.facility ?? user?.district ?? "Whole province"

  return (
    <>
      <PageHeader
        title={`Good day, ${user?.first_name ?? ""}`}
        description={`${user ? ROLE_LABEL[user.role] : ""} · Scope: ${scope}`}
        actions={
          can.edit(user) && (
            <Link href="/app/deliveries/new" className={buttonVariants()}>
              <PlusIcon /> Capture birth
            </Link>
          )
        }
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <KpiCard label="Deliveries in your scope" icon={BabyIcon} value={fmtNum(births?.total)} sub="Live-birth records" />
        <KpiCard label="NIL reports in your scope" icon={CircleSlashIcon} value={fmtNum(nil?.total)} sub="Time slots with no births" />
        <KpiCard
          label="Your last sign-in"
          icon={ClockIcon}
          value={<span className="text-lg">{timeAgo(user?.last_login_at)}</span>}
          sub={fmtDateTime(user?.last_login_at)}
        />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recently captured</CardTitle>
            <Link href="/app/deliveries" className="flex items-center gap-1 text-sm text-primary hover:underline">
              All records <ArrowRightIcon className="size-3.5" />
            </Link>
          </CardHeader>
          <CardContent className="grid gap-2">
            {births?.items.length === 0 && <p className="text-sm text-muted-foreground">Nothing captured yet.</p>}
            {births?.items.map((d) => (
              <Link
                key={d.id}
                href={`/app/deliveries/${d.id}`}
                className="flex items-center justify-between gap-3 rounded-lg border p-3 text-sm hover:bg-muted/50"
              >
                <div className="min-w-0">
                  <div className="truncate font-medium">{d.mother_name} {d.mother_surname}</div>
                  <div className="truncate text-xs text-muted-foreground">
                    {d.facility} · {fmtDate(d.report_date)} {d.delivery_time?.slice(0, 5)}
                  </div>
                </div>
                <div className="flex shrink-0 gap-1">
                  {d.babies.map((b, i) => (
                    <Badge key={i} variant="outline">{b.gender === "Male" ? "M" : "F"} {fmtNum(b.weight)}g</Badge>
                  ))}
                </div>
              </Link>
            ))}
            {babies !== undefined && births && births.items.length > 0 && (
              <p className="pt-1 text-xs text-muted-foreground">{babies} babies in the latest {births.items.length} deliveries</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Your account security</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 text-sm">
            <div className="flex items-start gap-3">
              <ShieldCheckIcon className="mt-0.5 size-4 text-status-good" />
              <div>
                <div className="font-medium">Password set</div>
                <div className="text-xs text-muted-foreground">Stored as an Argon2id hash</div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <ClockIcon className="mt-0.5 size-4 text-muted-foreground" />
              <div>
                <div className="font-medium">Session timeout</div>
                <div className="text-xs text-muted-foreground">You&apos;re signed out after 30 minutes of inactivity</div>
              </div>
            </div>
            <Link href="/change-password" className={buttonVariants({ variant: "outline", className: "mt-2" })}>
              <KeyRoundIcon /> Change password
            </Link>
          </CardContent>
        </Card>
      </div>
    </>
  )
}
