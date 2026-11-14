import type { LucideIcon } from "lucide-react"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"

/** Stat tile in the ECDoH campaign style: gold top edge, heavy green figure, tracked capitals label. */
export function KpiCard({
  label,
  value,
  sub,
  icon: Icon,
  className,
  emphasis = false,
}: {
  label: string
  value: React.ReactNode
  sub?: React.ReactNode
  icon?: LucideIcon
  className?: string
  emphasis?: boolean
}) {
  return (
    <Card
      className={cn(
        "gap-1.5 border-t-4 border-t-gold px-4 py-4",
        emphasis && "bg-primary text-primary-foreground ring-0",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className={cn("text-[11px] font-bold tracking-[0.12em] uppercase", emphasis ? "text-gold" : "text-muted-foreground")}>
          {label}
        </span>
        {Icon && (
          <span
            className={cn(
              "grid size-7 shrink-0 place-items-center rounded-full",
              emphasis ? "bg-white/15 text-gold" : "bg-secondary text-primary dark:text-gold",
            )}
          >
            <Icon className="size-3.5" />
          </span>
        )}
      </div>
      <div
        className={cn(
          "font-black tabular-nums tracking-tight",
          emphasis ? "text-4xl" : "text-3xl text-primary dark:text-foreground",
        )}
      >
        {value}
      </div>
      {sub && <div className={cn("text-xs font-medium", emphasis ? "text-primary-foreground/80" : "text-muted-foreground")}>{sub}</div>}
    </Card>
  )
}
