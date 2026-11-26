"use client"

import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useState } from "react"
import { AlertCircleIcon, EyeIcon, EyeOffIcon, Loader2Icon, LockIcon } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Field } from "@/components/form-controls"
import { api, ApiError } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import type { User } from "@/lib/types"

/**
 * Where to go after sign-in. Only paths inside the workspace are allowed: a bare "starts with /"
 * check let "/\evil.example" through, which browsers read as "//evil.example" (an open redirect).
 */
function safeNext(raw: string | null): string {
  if (!raw || !raw.startsWith("/") || /[\\\s]/.test(raw) || raw.startsWith("//")) return "/app"
  try {
    const url = new URL(raw, "https://placeholder.invalid")
    if (url.origin !== "https://placeholder.invalid") return "/app"
    const path = url.pathname + url.search + url.hash
    return path === "/app" || path.startsWith("/app/") || path.startsWith("/app?") ? path : "/app"
  } catch {
    return "/app"
  }
}

export function LoginForm() {
  const router = useRouter()
  const params = useSearchParams()
  const { mutate } = useAuth()
  const [persal, setPersal] = useState("")
  const [password, setPassword] = useState("")
  const [show, setShow] = useState(false)
  const [error, setError] = useState<{ message: string; locked?: boolean } | null>(null)
  const [busy, setBusy] = useState(false)

  const next = safeNext(params.get("next"))

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const user = await api<User>("/api/auth/login", { method: "POST", json: { persal_number: persal, password } })
      await mutate(user, { revalidate: false })
      router.replace(user.must_change_password ? "/change-password" : next)
      router.refresh()
    } catch (err) {
      const apiErr = err as ApiError
      setError({ message: apiErr.message, locked: apiErr.status === 423 || apiErr.status === 429 })
      setPassword("")
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-6">
      <div className="grid gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
        <p className="text-sm text-muted-foreground">Use your 8-digit Persal number and password.</p>
      </div>

      {error && (
        <Alert variant="destructive">
          {error.locked ? <LockIcon /> : <AlertCircleIcon />}
          <AlertDescription>{error.message}</AlertDescription>
        </Alert>
      )}

      <Field label="Persal number" htmlFor="persal">
        <Input
          id="persal"
          inputMode="numeric"
          autoComplete="username"
          placeholder="e.g. 12345678"
          maxLength={8}
          required
          autoFocus
          value={persal}
          onChange={(e) => setPersal(e.target.value.replace(/\D/g, ""))}
        />
      </Field>
      <Field label="Password" htmlFor="password">
        <div className="relative">
          <Input
            id="password"
            type={show ? "text" : "password"}
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="pr-9"
          />
          <button
            type="button"
            onClick={() => setShow((s) => !s)}
            aria-label={show ? "Hide password" : "Show password"}
            className="absolute top-1/2 right-2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          >
            {show ? <EyeOffIcon className="size-4" /> : <EyeIcon className="size-4" />}
          </button>
        </div>
      </Field>

      <Button type="submit" size="lg" disabled={busy || persal.length === 0 || !password}>
        {busy && <Loader2Icon className="animate-spin" />} Sign in
      </Button>

      <p className="text-center text-xs text-muted-foreground">
        Forgot your password or locked out? Contact your district administrator to reset it.
        <br />
        <Link href="/" className="mt-2 inline-block underline underline-offset-4 hover:text-foreground">
          Back to the public dashboard
        </Link>
      </p>
    </form>
  )
}
