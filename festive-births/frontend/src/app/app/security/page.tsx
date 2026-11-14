"use client"

import { useState } from "react"
import useSWR from "swr"
import { toast } from "sonner"
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"
import {
  AlertTriangleIcon, BanIcon, CheckCircle2Icon, FingerprintIcon, KeyRoundIcon, LockIcon, LockOpenIcon,
  LogInIcon, SearchIcon, ShieldAlertIcon, ShieldCheckIcon, UserXIcon, UsersIcon,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent, type ChartConfig,
} from "@/components/ui/chart"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { NativeSelect } from "@/components/form-controls"
import { KpiCard } from "@/components/kpi-card"
import { PageHeader, Pagination } from "@/components/page-header"
import { api, qs } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { fmtDate, fmtDateTime, fmtNum, timeAgo } from "@/lib/format"
import { ROLE_LABEL, type AuditEntry, type Paged, type User } from "@/lib/types"
import { cn } from "@/lib/utils"

interface Overview {
  stats: {
    total_users: number; active_users: number; inactive_users: number; locked_accounts: number
    pending_password_change: number; logins_24h: number; failed_logins_24h: number; rate_limited_24h: number
    never_logged_in: number
  }
  users_by_role: { role: keyof typeof ROLE_LABEL; count: number }[]
  logins_by_day: { date: string; success: number; failed: number }[]
  top_failing_persal: { persal_number: string; count: number }[]
  locked_users: User[]
  pending_users: User[]
  policy: {
    hashing: string; session_idle_minutes: number; max_failed_logins: number; lockout_minutes: number
    login_rate_limit_per_minute: number; password_min_length: number; secure_cookies: boolean
  }
}

const ACTIONS: Record<string, string> = {
  login_success: "Signed in", login_failed: "Failed sign-in", login_blocked: "Sign-in blocked",
  login_rate_limited: "Rate limited", account_locked: "Account locked", logout: "Signed out",
  logout_everywhere: "Signed out everywhere", password_changed: "Password changed",
  password_change_failed: "Password change failed", password_reset: "Password reset (admin)",
  account_unlocked: "Account unlocked", sessions_revoked: "Sessions revoked", user_created: "User created",
  user_updated: "User updated", user_deleted: "User deleted", delivery_created: "Delivery captured",
  delivery_updated: "Delivery updated", delivery_deleted: "Delivery deleted", export_deliveries: "Exported deliveries",
  export_users: "Exported users", export_dashboard_pdf: "Exported PDF",
}

const loginConfig = {
  success: { label: "Successful", color: "var(--chart-1)" },
  failed: { label: "Failed / blocked", color: "var(--chart-2)" },
} satisfies ChartConfig

/** Status pill: reserved status colour + icon + label, never colour alone. */
function Status({ level, children }: { level: "good" | "warning" | "critical"; children: React.ReactNode }) {
  const Icon = level === "good" ? CheckCircle2Icon : level === "warning" ? AlertTriangleIcon : ShieldAlertIcon
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium">
      <Icon className={cn("size-3.5", { good: "text-status-good", warning: "text-status-warning", critical: "text-status-critical" }[level])} />
      {children}
    </span>
  )
}

function AuditLog() {
  const [q, setQ] = useState("")
  const [action, setAction] = useState("")
  const [outcome, setOutcome] = useState("")
  const [page, setPage] = useState(1)
  const { data } = useSWR<Paged<AuditEntry>>(
    `/api/security/audit${qs({ q, action, success: outcome, page, page_size: 15 })}`,
    { keepPreviousData: true, refreshInterval: 30_000 },
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle>Audit trail</CardTitle>
        <CardDescription>Every authentication event, data change, export and admin action.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        <div className="grid gap-2 sm:grid-cols-[1fr_200px_150px]">
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input className="pl-8" placeholder="Persal number, IP or detail…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} />
          </div>
          <NativeSelect aria-label="Event" value={action} placeholder="All events"
            options={Object.entries(ACTIONS).map(([value, label]) => ({ value, label }))}
            onChange={(e) => { setAction(e.target.value); setPage(1) }} />
          <NativeSelect aria-label="Outcome" value={outcome} placeholder="Any outcome"
            options={[{ value: "true", label: "Succeeded" }, { value: "false", label: "Failed" }]}
            onChange={(e) => { setOutcome(e.target.value); setPage(1) }} />
        </div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>When</TableHead><TableHead>Event</TableHead><TableHead>Who</TableHead>
                <TableHead>Detail</TableHead><TableHead>IP address</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items.length === 0 && <TableRow><TableCell colSpan={5} className="py-8 text-center text-muted-foreground">No matching events.</TableCell></TableRow>}
              {data?.items.map((a) => (
                <TableRow key={a.id}>
                  <TableCell className="whitespace-nowrap text-sm" title={fmtDateTime(a.created_at)}>{timeAgo(a.created_at)}</TableCell>
                  <TableCell>
                    <Status level={a.success ? "good" : a.action === "account_locked" ? "critical" : "warning"}>
                      {ACTIONS[a.action] ?? a.action}
                    </Status>
                  </TableCell>
                  <TableCell className="text-sm">
                    <div>{a.user_name ?? "Unknown"}</div>
                    <div className="font-mono text-xs text-muted-foreground">{a.persal_number}</div>
                  </TableCell>
                  <TableCell className="max-w-64 truncate text-sm text-muted-foreground" title={a.detail ?? ""}>{a.detail ?? "–"}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground" title={a.user_agent ?? ""}>{a.ip_address ?? "–"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        {data && <Pagination page={page} pageSize={15} total={data.total} onPage={setPage} />}
      </CardContent>
    </Card>
  )
}

export default function SecurityPage() {
  const { user } = useAuth()
  const { data: o, mutate } = useSWR<Overview>("/api/security/overview", { refreshInterval: 30_000 })
  const s = o?.stats

  async function unlock(u: User) {
    try {
      await api(`/api/users/${u.id}/unlock`, { method: "POST" })
      toast.success(`${u.first_name} unlocked`)
      mutate()
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  return (
    <>
      <PageHeader
        title="Security center"
        description={user?.role === "admin" ? `Authentication health for ${user.district}` : "Authentication health across the province"}
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Sign-ins (24h)" icon={LogInIcon} value={fmtNum(s?.logins_24h)} sub={`${fmtNum(s?.active_users)} active accounts`} />
        <KpiCard
          label="Failed sign-ins (24h)"
          icon={BanIcon}
          value={fmtNum(s?.failed_logins_24h)}
          sub={s && (s.failed_logins_24h > 10 ? <Status level="warning">Elevated</Status> : <Status level="good">Normal</Status>)}
        />
        <KpiCard
          label="Locked accounts"
          icon={LockIcon}
          value={fmtNum(s?.locked_accounts)}
          sub={s && (s.locked_accounts ? <Status level="critical">Needs attention</Status> : <Status level="good">None locked</Status>)}
        />
        <KpiCard
          label="Temp passwords pending"
          icon={KeyRoundIcon}
          value={fmtNum(s?.pending_password_change)}
          sub={`${fmtNum(s?.never_logged_in)} never signed in`}
        />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Sign-in activity</CardTitle>
            <CardDescription>Last 14 days{s ? ` · ${s.rate_limited_24h} rate-limited request(s) in 24h` : ""}</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={loginConfig} className="aspect-[16/7] w-full">
              <BarChart data={o?.logins_by_day ?? []} margin={{ left: 0, right: 4, top: 4 }} barGap={2}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="date" tickLine={false} axisLine={false} tickFormatter={(d) => fmtDate(d, { day: "numeric", month: "short" })} interval="preserveStartEnd" />
                <YAxis tickLine={false} axisLine={false} allowDecimals={false} width={28} />
                <ChartTooltip content={<ChartTooltipContent labelFormatter={(d) => fmtDate(String(d), { dateStyle: "medium" })} />} />
                <ChartLegend content={<ChartLegendContent />} />
                <Bar isAnimationActive={false} dataKey="success" fill="var(--color-success)" radius={[4, 4, 0, 0]} />
                <Bar isAnimationActive={false} dataKey="failed" fill="var(--color-failed)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><FingerprintIcon className="size-4" /> Security policy</CardTitle>
            <CardDescription>Controls currently enforced by the API</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2.5 text-sm">
            {o && [
              ["Password hashing", o.policy.hashing],
              ["Minimum password length", `${o.policy.password_min_length} chars, mixed case + number`],
              ["Lockout", `${o.policy.max_failed_logins} failures → ${o.policy.lockout_minutes} min`],
              ["IP rate limit", `${o.policy.login_rate_limit_per_minute} sign-ins / min`],
              ["Idle session timeout", `${o.policy.session_idle_minutes} min`],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3 border-b pb-2 last:border-0">
                <span className="text-muted-foreground">{k}</span>
                <span className="text-right font-medium">{v}</span>
              </div>
            ))}
            {o && (
              <div className="flex justify-between gap-3">
                <span className="text-muted-foreground">Secure (HTTPS-only) cookies</span>
                {o.policy.secure_cookies ? <Status level="good">On</Status> : <Status level="warning">Off (dev)</Status>}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><LockIcon className="size-4" /> Locked accounts</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            {o?.locked_users.length === 0 && <Status level="good">No accounts are locked.</Status>}
            {o?.locked_users.map((u) => (
              <div key={u.id} className="flex items-center justify-between gap-2 rounded-lg border p-2.5 text-sm">
                <div>
                  <div className="font-medium">{u.first_name} {u.last_name}</div>
                  <div className="text-xs text-muted-foreground">Until {fmtDateTime(u.locked_until)}</div>
                </div>
                <Button size="sm" variant="outline" onClick={() => unlock(u)}><LockOpenIcon /> Unlock</Button>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><UserXIcon className="size-4" /> Most failed Persal numbers (24h)</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            {o?.top_failing_persal.length === 0 && <Status level="good">No failed sign-ins.</Status>}
            {o?.top_failing_persal.map((p) => (
              <div key={p.persal_number} className="flex items-center justify-between text-sm">
                <span className="font-mono">{p.persal_number}</span>
                <Badge variant="outline">{p.count} failures</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><UsersIcon className="size-4" /> Accounts by role</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            {o?.users_by_role.map((r) => (
              <div key={r.role} className="grid gap-1 text-sm">
                <div className="flex justify-between"><span>{ROLE_LABEL[r.role]}</span><span className="tabular-nums">{r.count}</span></div>
                <div className="h-1.5 rounded-full bg-muted">
                  <div className="h-full rounded-full bg-chart-1" style={{ width: `${s?.total_users ? (100 * r.count) / s.total_users : 0}%` }} />
                </div>
              </div>
            ))}
            {o && o.pending_users.length > 0 && (
              <p className="pt-2 text-xs text-muted-foreground">
                <ShieldCheckIcon className="mr-1 inline size-3.5" />
                Awaiting first password change: {o.pending_users.map((u) => u.first_name).join(", ")}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-4">
        <AuditLog />
      </div>
    </>
  )
}
