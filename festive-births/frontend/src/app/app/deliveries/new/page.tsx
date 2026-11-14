import { DeliveryForm } from "@/components/delivery-form"
import { PageHeader } from "@/components/page-header"

export default function NewDeliveryPage() {
  return (
    <>
      <PageHeader title="Capture birth" description="Record a delivery, or a NIL report when no births occurred in a time slot." />
      <DeliveryForm />
    </>
  )
}
