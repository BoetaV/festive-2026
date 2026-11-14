import { Suspense } from "react"
import { EcdohLogo } from "@/components/brand"
import { SiteHeader } from "@/components/site-header"
import { DashboardView } from "@/components/dashboard/dashboard-view"

export default function HomePage() {
  return (
    <>
      <SiteHeader />
      <main className="flex-1">
        <Suspense>
          <DashboardView />
        </Suspense>
      </main>
      <footer className="bg-gold text-gold-foreground">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-6">
          <span className="rounded-md bg-white px-2 py-1"><EcdohLogo /></span>
          <div className="text-right">
            <div className="text-lg font-black tracking-tight uppercase">Every birth counts</div>
            <div className="text-xs font-semibold">
              Festive Season Births · Aggregated figures only · © {new Date().getFullYear()} Eastern Cape Department of Health
            </div>
          </div>
        </div>
      </footer>
    </>
  )
}
