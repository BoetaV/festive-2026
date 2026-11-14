"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"
import { KeyRoundIcon, Loader2Icon } from "lucide-react"
import { toast } from "sonner"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { AuthShell } from "@/components/auth/auth-shell"
import { PASSWORD_RULES, PasswordStrength } from "@/components/auth/password-strength"
import { Field } from "@/components/form-controls"
import { api, ApiError } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import type { User } from "@/lib/types"

export default function ChangePasswordPage() {
  const router = useRouter()
  const { user, mutate } = useAuth()
  const [form, setForm] = useState({ current: "", next: "", confirm: "" })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const strong = PASSWORD_RULES.every((r) => r.test(form.next))

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (form.next !== form.confirm) return setErrors({ confirm: "Passwords do not match." })
    setBusy(true)
    setErrors({})
    try {
      const u = await api<User>("/api/auth/change-password", {
        method: "POST",
        json: { current_password: form.current, new_password: form.next },
      })
      await mutate(u, { revalidate: false })
      toast.success("Password changed. Other devices have been signed out.")
      router.replace("/app")
    } catch (err) {
      const apiErr = err as ApiError
      setErrors(Object.keys(apiErr.fieldErrors).length ? apiErr.fieldErrors : { form: apiErr.message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell>
      <form onSubmit={submit} className="grid gap-5">
        <div className="grid gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">Change password</h1>
          <p className="text-sm text-muted-foreground">Choose a strong password you don&apos;t use anywhere else.</p>
        </div>
        {user?.must_change_password && (
          <Alert>
            <KeyRoundIcon />
            <AlertTitle>Temporary password</AlertTitle>
            <AlertDescription>For security, you must set your own password before continuing.</AlertDescription>
          </Alert>
        )}
        {errors.form && <p className="text-sm text-destructive">{errors.form}</p>}
        <Field
          label={user?.must_change_password ? "Temporary password" : "Current password"}
          htmlFor="current"
          error={errors.current_password}
        >
          <Input
            id="current"
            type="password"
            autoComplete="current-password"
            required
            value={form.current}
            aria-invalid={!!errors.current_password}
            onChange={(e) => setForm({ ...form, current: e.target.value })}
          />
        </Field>
        <Field label="New password" htmlFor="new" error={errors.new_password}>
          <Input
            id="new"
            type="password"
            autoComplete="new-password"
            required
            value={form.next}
            aria-invalid={!!errors.new_password}
            onChange={(e) => setForm({ ...form, next: e.target.value })}
          />
        </Field>
        <PasswordStrength password={form.next} />
        <Field label="Confirm new password" htmlFor="confirm" error={errors.confirm}>
          <Input
            id="confirm"
            type="password"
            autoComplete="new-password"
            required
            value={form.confirm}
            aria-invalid={!!errors.confirm}
            onChange={(e) => setForm({ ...form, confirm: e.target.value })}
          />
        </Field>
        <Button type="submit" size="lg" disabled={busy || !strong || !form.current}>
          {busy && <Loader2Icon className="animate-spin" />} Update password
        </Button>
      </form>
    </AuthShell>
  )
}
