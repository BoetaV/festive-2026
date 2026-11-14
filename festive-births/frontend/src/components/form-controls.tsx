import * as React from "react"
import { ChevronDownIcon } from "lucide-react"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"

/** Styled native <select>: reliable for long cascading lists and great on mobile. */
export function NativeSelect({
  className,
  options,
  placeholder,
  ...props
}: React.ComponentProps<"select"> & { options: (string | { value: string; label: string })[]; placeholder?: string }) {
  return (
    <div className={cn("relative", className)}>
      <select
        className="h-8 w-full appearance-none rounded-lg border border-input bg-transparent py-1 pr-8 pl-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:bg-input/30 [&>option]:bg-popover [&>option]:text-popover-foreground"
        {...props}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((o) => {
          const { value, label } = typeof o === "string" ? { value: o, label: o } : o
          return (
            <option key={value} value={value}>
              {label}
            </option>
          )
        })}
      </select>
      <ChevronDownIcon className="pointer-events-none absolute top-1/2 right-2 size-4 -translate-y-1/2 text-muted-foreground" />
    </div>
  )
}

export function Field({
  label,
  htmlFor,
  error,
  hint,
  className,
  children,
}: {
  label: string
  htmlFor?: string
  error?: string
  hint?: React.ReactNode
  className?: string
  children: React.ReactNode
}) {
  return (
    <div className={cn("grid gap-1.5", className)}>
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {error ? (
        <p role="alert" className="text-xs text-destructive">{error}</p>
      ) : hint ? (
        <p className="text-xs text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  )
}
