import { CheckIcon, XIcon } from "lucide-react"
import { cn } from "@/lib/utils"

export const PASSWORD_RULES: { label: string; test: (p: string) => boolean }[] = [
  { label: "At least 8 characters", test: (p) => p.length >= 8 },
  { label: "A lowercase letter", test: (p) => /[a-z]/.test(p) },
  { label: "An uppercase letter", test: (p) => /[A-Z]/.test(p) },
  { label: "A number", test: (p) => /\d/.test(p) },
]

export function PasswordStrength({ password }: { password: string }) {
  return (
    <ul className="grid grid-cols-2 gap-1 text-xs">
      {PASSWORD_RULES.map((r) => {
        const ok = r.test(password)
        return (
          <li key={r.label} className={cn("flex items-center gap-1.5", ok ? "text-foreground" : "text-muted-foreground")}>
            {ok ? <CheckIcon className="size-3.5 text-status-good" /> : <XIcon className="size-3.5" />}
            {r.label}
          </li>
        )
      })}
    </ul>
  )
}
