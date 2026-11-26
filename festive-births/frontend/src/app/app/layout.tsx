import { DataLockBanner } from "@/components/data-lock-banner"
import { SiteHeader } from "@/components/site-header"
import { WorkspaceNav } from "@/components/workspace-nav"

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SiteHeader />
      <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 px-4 py-6 md:flex-row">
        <WorkspaceNav />
        <main className="min-w-0 flex-1">
          <DataLockBanner />
          {children}
        </main>
      </div>
    </>
  )
}
