"use client"

import { useParams } from "next/navigation"
import useSWR from "swr"
import { Skeleton } from "@/components/ui/skeleton"
import { DeliveryForm } from "@/components/delivery-form"
import { PageHeader } from "@/components/page-header"
import { fmtDateTime } from "@/lib/format"
import type { Delivery } from "@/lib/types"

export default function EditDeliveryPage() {
  const { id } = useParams<{ id: string }>()
  const { data, error } = useSWR<Delivery>(`/api/deliveries/${id}`)

  return (
    <>
      <PageHeader
        title="Edit delivery record"
        description={data && `Captured by ${data.captured_by_name ?? "unknown"} · last updated ${fmtDateTime(data.updated_at)}`}
      />
      {error ? (
        <p className="text-sm text-destructive">{error.message}</p>
      ) : data ? (
        <DeliveryForm key={data.id} initial={data} />
      ) : (
        <Skeleton className="h-96" />
      )}
    </>
  )
}
