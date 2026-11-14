"use client"

import Link from "next/link"
import {
  ClipboardListIcon, FileBarChartIcon, FingerprintIcon, HistoryIcon, KeyRoundIcon, LockIcon, PlusCircleIcon,
  ShieldCheckIcon, TimerIcon, UserCogIcon, UsersIcon,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { can, useAuth } from "@/lib/auth"
import { ROLE_LABEL, type Role, type User } from "@/lib/types"
import { cn } from "@/lib/utils"

const AREAS: {
  href: string
  title: string
  desc: string
  icon: typeof UsersIcon
  allowed: (u: User | null) => boolean
  roles: string
}[] = [
  { href: "/app/deliveries/new", title: "Capture a birth", desc: "Record a delivery or a NIL report for a time slot.", icon: PlusCircleIcon, allowed: can.edit, roles: "Facility users, district admins, superusers" },
  { href: "/app/deliveries", title: "Delivery records", desc: "Search, edit and export records in your scope.", icon: ClipboardListIcon, allowed: (u) => !!u, roles: "All signed-in users" },
  { href: "/app/reports", title: "Reports & exports", desc: "Abnormal birth weights, NIL reports, Excel & PDF.", icon: FileBarChartIcon, allowed: (u) => !!u, roles: "All signed-in users" },
  { href: "/app/users", title: "User management", desc: "Create accounts, reset passwords, unlock users.", icon: UserCogIcon, allowed: can.manageUsers, roles: "Superusers, province, district users" },
  { href: "/app/security", title: "Security center", desc: "Sign-in activity, lockouts and the audit trail.", icon: ShieldCheckIcon, allowed: can.security, roles: "Superusers, province, district users" },
]

const ROLES: { role: Role; scope: string; abilities: string }[] = [
  { role: "superuser", scope: "Whole province", abilities: "Everything, including all user accounts and the user export." },
  { role: "province", scope: "Whole province", abilities: "View all records and reports; create and manage district users." },
  { role: "admin", scope: "One district", abilities: "Capture & edit district data; create and manage that district's facility users." },
  { role: "user", scope: "One facility", abilities: "Capture, edit and see births, NIL reports and reports for their facility only." },
]

const CONTROLS = [
  { icon: FingerprintIcon, title: "Argon2id password hashing", desc: "Memory-hard hashing; passwords are never stored or logged." },
  { icon: LockIcon, title: "Account lockout", desc: "5 failed sign-ins locks the account for 15 minutes; IP rate limiting on top." },
  { icon: KeyRoundIcon, title: "Forced password change", desc: "New and reset accounts start on the default password and must set a strong one at first sign-in." },
  { icon: TimerIcon, title: "30-minute idle sessions", desc: "httpOnly, SameSite cookies with CSRF protection; sign out everywhere anytime." },
  { icon: HistoryIcon, title: "Full audit trail", desc: "Every sign-in, change, export and admin action is recorded." },
  { icon: ShieldCheckIcon, title: "Least-privilege scoping", desc: "Records are filtered server-side to your district or facility." },
]

export function AccessSection() {
  const { user } = useAuth()

  return (
    <section id="access" className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Access & security</h2>
          <p className="text-sm text-muted-foreground">
            {user
              ? `Signed in as ${user.first_name} ${user.last_name} · ${ROLE_LABEL[user.role]}${user.facility ? ` · ${user.facility}` : user.district ? ` · ${user.district}` : ""}`
              : "The dashboard above is public and shows aggregates only. Patient-level data requires sign-in."}
          </p>
        </div>
        {!user && (
          <Link href="/login" className={buttonVariants()}>
            Sign in with your Persal number
          </Link>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {AREAS.map((a) => {
          const ok = a.allowed(user)
          const inner = (
            <Card className={cn("h-full gap-2 p-4 transition-colors", ok ? "hover:bg-muted/50" : "opacity-60")}>
              <div className="flex items-center justify-between">
                <a.icon className="size-5 text-primary" />
                {!ok && <LockIcon className="size-3.5 text-muted-foreground" aria-label="Locked" />}
              </div>
              <div className="font-medium">{a.title}</div>
              <p className="text-xs text-muted-foreground">{a.desc}</p>
              <p className="mt-auto pt-1 text-[11px] text-muted-foreground">{a.roles}</p>
            </Card>
          )
          return ok ? (
            <Link key={a.href} href={a.href} className="rounded-xl outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
              {inner}
            </Link>
          ) : user ? (
            <div key={a.href} aria-disabled>{inner}</div>
          ) : (
            <Link key={a.href} href={`/login?next=${encodeURIComponent(a.href)}`} className="rounded-xl">
              {inner}
            </Link>
          )
        })}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Roles & permissions</CardTitle>
            <CardDescription>Authorisation is enforced by the API, not just hidden in the UI.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            {ROLES.map((r) => (
              <div key={r.role} className={cn("flex gap-3 rounded-lg border p-3", user?.role === r.role && "border-primary bg-primary/5")}>
                <UsersIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                <div className="grid gap-0.5">
                  <div className="flex flex-wrap items-center gap-2 text-sm font-medium">
                    {ROLE_LABEL[r.role]}
                    <Badge variant="outline">{r.scope}</Badge>
                    {user?.role === r.role && <Badge>Your role</Badge>}
                  </div>
                  <p className="text-xs text-muted-foreground">{r.abilities}</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Authentication & security controls</CardTitle>
            <CardDescription>How accounts and patient data are protected.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            {CONTROLS.map((c) => (
              <div key={c.title} className="flex gap-3">
                <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
                  <c.icon className="size-4" />
                </span>
                <div>
                  <div className="text-sm font-medium">{c.title}</div>
                  <p className="text-xs text-muted-foreground">{c.desc}</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </section>
  )
}
