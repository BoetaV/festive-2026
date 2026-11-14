"use client"

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"
import {
  ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent, type ChartConfig,
} from "@/components/ui/chart"
import type { MF } from "@/lib/types"
import { cn } from "@/lib/utils"

const sexConfig = {
  male: { label: "Male", color: "var(--chart-1)" },
  female: { label: "Female", color: "var(--chart-2)" },
} satisfies ChartConfig

/** Stacked Male/Female bars. Horizontal layout suits long category names. */
export function SexBarChart({
  data,
  horizontal = false,
  className,
  labelWidth = 120,
}: {
  data: MF[]
  horizontal?: boolean
  className?: string
  labelWidth?: number
}) {
  const height = horizontal ? Math.max(180, data.length * 30 + 50) : undefined
  return (
    <ChartContainer config={sexConfig} className={cn("w-full", !horizontal && "aspect-[16/9]", className)} style={{ height }}>
      <BarChart
        data={data}
        layout={horizontal ? "vertical" : "horizontal"}
        margin={{ left: 0, right: 8, top: 4 }}
        barCategoryGap={horizontal ? 6 : "20%"}
      >
        <CartesianGrid vertical={horizontal} horizontal={!horizontal} strokeDasharray="3 3" />
        {horizontal ? (
          <>
            <XAxis type="number" tickLine={false} axisLine={false} allowDecimals={false} />
            <YAxis type="category" dataKey="name" width={labelWidth} tickLine={false} axisLine={false} interval={0} />
          </>
        ) : (
          <>
            <XAxis dataKey="name" tickLine={false} axisLine={false} interval={0} tickMargin={6} />
            <YAxis tickLine={false} axisLine={false} allowDecimals={false} width={32} />
          </>
        )}
        <ChartTooltip cursor={{ fillOpacity: 0.4 }} content={<ChartTooltipContent />} />
        <ChartLegend content={<ChartLegendContent />} />
        {/* 2px surface-coloured stroke gives the gap between stacked segments */}
        <Bar isAnimationActive={false} dataKey="male" stackId="s" fill="var(--color-male)" stroke="var(--card)" strokeWidth={2} radius={horizontal ? [4, 0, 0, 4] : [0, 0, 4, 4]} />
        <Bar isAnimationActive={false} dataKey="female" stackId="s" fill="var(--color-female)" stroke="var(--card)" strokeWidth={2} radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]} />
      </BarChart>
    </ChartContainer>
  )
}

/** Single-series bar chart (one hue, no legend - the card title names it). */
export function SingleBarChart({
  data,
  dataKey,
  nameKey,
  label,
  className,
  tickFormatter,
}: {
  data: Record<string, unknown>[]
  dataKey: string
  nameKey: string
  label: string
  className?: string
  tickFormatter?: (v: string | number) => string
}) {
  const config = { [dataKey]: { label, color: "var(--chart-1)" } } satisfies ChartConfig
  return (
    <ChartContainer config={config} className={cn("aspect-[16/7] w-full", className)}>
      <BarChart data={data} margin={{ left: 0, right: 4, top: 4 }} barCategoryGap={2}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis dataKey={nameKey} tickLine={false} axisLine={false} tickFormatter={tickFormatter} interval="preserveStartEnd" />
        <YAxis tickLine={false} axisLine={false} allowDecimals={false} width={32} />
        <ChartTooltip
          cursor={{ fillOpacity: 0.4 }}
          content={<ChartTooltipContent labelFormatter={(v) => (tickFormatter ? tickFormatter(v as string) : String(v))} />}
        />
        <Bar isAnimationActive={false} dataKey={dataKey} fill={`var(--color-${dataKey})`} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ChartContainer>
  )
}
