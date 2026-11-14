"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { KeyRoundIcon, LayoutDashboardIcon, LogInIcon, LogOutIcon, MonitorSmartphoneIcon } from "lucide-react"
import { toast } from "sonner"
import { buttonVariants } from "@/components/ui/button"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { api } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { ROLE_LABEL } from "@/lib/types"

export function UserMenu() {
  const { user, isLoading, mutate } = useAuth()
  const router = useRouter()

  if (isLoading) return <div className="h-8 w-24 animate-pulse rounded-lg bg-muted" />
  if (!user)
    return (
      <Link href="/login" className={buttonVariants({ size: "sm" })}>
        <LogInIcon /> Sign in
      </Link>
    )

  const initials = `${user.first_name[0] ?? ""}${user.last_name[0] ?? ""}`.toUpperCase()

  async function logout(everywhere = false) {
    await api(everywhere ? "/api/auth/logout-everywhere" : "/api/auth/logout", { method: "POST" })
    await mutate(null, { revalidate: false })
    toast.success(everywhere ? "Signed out on all devices" : "Signed out")
    router.push("/")
    router.refresh()
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="flex items-center gap-2 rounded-lg p-1 pr-2 outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50">
        <span className="grid size-7 place-items-center rounded-full bg-primary/15 text-xs font-semibold text-primary">
          {initials}
        </span>
        <span className="hidden text-sm sm:inline">{user.first_name}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-60">
        <DropdownMenuGroup>
          <DropdownMenuLabel>
            <div className="font-medium text-foreground">{user.first_name} {user.last_name}</div>
            <div className="text-xs font-normal">Persal {user.persal_number} · {ROLE_LABEL[user.role]}</div>
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => router.push("/app")}>
          <LayoutDashboardIcon /> Workspace
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push("/change-password")}>
          <KeyRoundIcon /> Change password
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => logout(true)}>
          <MonitorSmartphoneIcon /> Sign out everywhere
        </DropdownMenuItem>
        <DropdownMenuItem variant="destructive" onClick={() => logout()}>
          <LogOutIcon /> Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
