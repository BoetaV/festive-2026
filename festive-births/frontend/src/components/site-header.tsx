"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Brand } from "@/components/brand"
import { ThemeToggle } from "@/components/theme-toggle"
import { UserMenu } from "@/components/user-menu"
import { can, useAuth } from "@/lib/auth"
import { cn } from "@/lib/utils"

export function SiteHeader() {
  const { user } = useAuth()
  const path = usePathname()
  const links = [
    { href: "/", label: "Dashboard", show: true },
    { href: "/app", label: "Workspace", show: !!user },
    { href: "/app/security", label: "Security", show: can.security(user) },
  ].filter((l) => l.show)

  return (
    <header className="sticky top-0 z-40 border-b-4 border-gold bg-card/95 backdrop-blur supports-backdrop-filter:bg-card/85">
      <div className="mx-auto flex h-18 max-w-7xl items-center gap-4 px-4 sm:h-22">
        <Brand />
        <nav className="ml-4 hidden items-center gap-1 md:flex">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={cn(
                "rounded-full px-3.5 py-1.5 text-sm font-semibold text-muted-foreground transition-colors hover:text-primary",
                (l.href === "/" ? path === "/" : path.startsWith(l.href)) && "bg-primary text-primary-foreground hover:text-primary-foreground",
              )}
            >
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-1">
          <ThemeToggle />
          <UserMenu />
        </div>
      </div>
    </header>
  )
}
