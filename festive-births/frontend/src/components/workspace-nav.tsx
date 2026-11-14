"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  ClipboardListIcon, FileBarChartIcon, HomeIcon, PlusCircleIcon, ShieldCheckIcon, UserCogIcon,
} from "lucide-react"
import { can, useAuth } from "@/lib/auth"
import { ROLE_LABEL, type User } from "@/lib/types"
import { cn } from "@/lib/utils"

const ITEMS: { href: string; label: string; icon: typeof HomeIcon; show: (u: User | null) => boolean; exact?: boolean }[] = [
  { href: "/app", label: "Overview", icon: HomeIcon, show: () => true, exact: true },
  { href: "/app/deliveries/new", label: "Capture birth", icon: PlusCircleIcon, show: can.edit, exact: true },
  { href: "/app/deliveries", label: "Delivery records", icon: ClipboardListIcon, show: () => true },
  { href: "/app/reports", label: "Reports & exports", icon: FileBarChartIcon, show: () => true },
  { href: "/app/users", label: "Users", icon: UserCogIcon, show: can.manageUsers },
  { href: "/app/security", label: "Security center", icon: ShieldCheckIcon, show: can.security },
]

export function WorkspaceNav() {
  const { user } = useAuth()
  const path = usePathname()
  const items = ITEMS.filter((i) => i.show(user))
  const isActive = (i: (typeof ITEMS)[number]) =>
    i.exact ? path === i.href : path.startsWith(i.href) && !(i.href === "/app/deliveries" && path === "/app/deliveries/new")

  return (
    <aside className="md:w-56 md:shrink-0">
      <div className="md:sticky md:top-28">
        {user && (
          <div className="mb-4 hidden rounded-xl border p-3 md:block">
            <div className="text-sm font-medium">{user.first_name} {user.last_name}</div>
            <div className="text-xs text-muted-foreground">{ROLE_LABEL[user.role]}</div>
            {(user.facility || user.district) && (
              <div className="mt-1 text-xs text-muted-foreground">{user.facility ?? user.district}</div>
            )}
          </div>
        )}
        <nav className="-mx-4 flex gap-1 overflow-x-auto px-4 pb-1 md:mx-0 md:flex-col md:px-0">
          {items.map((i) => (
            <Link
              key={i.href}
              href={i.href}
              className={cn(
                "flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                isActive(i) && "bg-muted font-medium text-foreground",
              )}
            >
              <i.icon className="size-4" />
              {i.label}
            </Link>
          ))}
        </nav>
      </div>
    </aside>
  )
}
