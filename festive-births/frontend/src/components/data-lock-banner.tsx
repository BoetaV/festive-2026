"use client"

import { LockIcon } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useAuth } from "@/lib/auth"

/** Shown across the workspace once the season's data is locked (read-only). */
export function DataLockBanner() {
  const { user } = useAuth()
  if (!user?.data_locked) return null
  return (
    <Alert className="mb-4">
      <LockIcon />
      <AlertDescription>
        The festive season database is locked. You can view reports and download exports, but births,
        NIL reports and user accounts can no longer be added, changed or deleted.
      </AlertDescription>
    </Alert>
  )
}
