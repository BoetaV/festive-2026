"use client"

import { BarChart3Icon, TableIcon } from "lucide-react"
import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { fmtNum } from "@/lib/format"
import { cn } from "@/lib/utils"

export interface Column<T> {
  key: string
  label: string
  numeric?: boolean
  render?: (row: T) => React.ReactNode
}

/** A card holding a chart with an accessible table view of the same numbers. */
export function ChartCard<T extends object>({
  title,
  description,
  className,
  chart,
  rows,
  columns,
  total,
  emptyText = "No data for this selection.",
}: {
  title: string
  description?: string
  className?: string
  chart?: React.ReactNode
  rows: T[]
  columns: Column<T>[]
  total?: Record<string, React.ReactNode>
  emptyText?: string
}) {
  const [view, setView] = useState<"chart" | "table">(chart ? "chart" : "table")
  const empty = rows.length === 0

  return (
    <Card className={cn("gap-3", className)}>
      <CardHeader className="flex flex-row items-start justify-between gap-2">
        <div className="grid gap-1 border-l-4 border-gold pl-3">
          <CardTitle className="font-extrabold text-brand-deep">{title}</CardTitle>
          {description && <CardDescription>{description}</CardDescription>}
        </div>
        {chart && !empty && (
          <div className="flex shrink-0 rounded-lg border p-0.5" role="group" aria-label="View">
            {(["chart", "table"] as const).map((v) => (
              <button
                key={v}
                type="button"
                aria-pressed={view === v}
                aria-label={v === "chart" ? "Chart view" : "Table view"}
                onClick={() => setView(v)}
                className={cn(
                  "grid size-6 place-items-center rounded-md text-muted-foreground transition-colors",
                  view === v && "bg-primary text-primary-foreground",
                )}
              >
                {v === "chart" ? <BarChart3Icon className="size-3.5" /> : <TableIcon className="size-3.5" />}
              </button>
            ))}
          </div>
        )}
      </CardHeader>
      <CardContent className="min-w-0">
        {empty ? (
          <p className="py-10 text-center text-sm text-muted-foreground">{emptyText}</p>
        ) : view === "chart" && chart ? (
          chart
        ) : (
          <div className="max-h-96 overflow-auto">
            <Table>
              <TableHeader className="sticky top-0 bg-secondary [&_th]:font-bold [&_th]:text-brand-deep">
                <TableRow>
                  {columns.map((c) => (
                    <TableHead key={c.key} className={cn(c.numeric && "text-right")}>{c.label}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r, i) => (
                  <TableRow key={i}>
                    {columns.map((c) => (
                      <TableCell key={c.key} className={cn(c.numeric && "text-right tabular-nums")}>
                        {c.render ? c.render(r) : c.numeric ? fmtNum((r as Record<string, number>)[c.key]) : String((r as Record<string, unknown>)[c.key] ?? "–")}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
              {total && (
                <TableFooter>
                  <TableRow>
                    {columns.map((c) => (
                      <TableCell key={c.key} className={cn("font-semibold", c.numeric && "text-right tabular-nums")}>
                        {total[c.key] ?? ""}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableFooter>
              )}
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
