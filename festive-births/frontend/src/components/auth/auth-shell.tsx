import Image from "next/image"
import { ShieldCheckIcon } from "lucide-react"
import { Brand } from "@/components/brand"
import { ThemeToggle } from "@/components/theme-toggle"

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      <div className="flex flex-col p-6">
        <div className="flex items-center justify-between">
          <Brand />
          <ThemeToggle />
        </div>
        <div className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-sm">{children}</div>
        </div>
      </div>
      <aside className="relative hidden overflow-hidden bg-primary lg:block">
        <Image
          src="/images/login-christmas-baby.jpg"
          alt="A smiling baby in a Santa suit and hat"
          fill
          priority
          sizes="50vw"
          className="object-cover object-[50%_30%]"
        />
        {/* Gradient keeps the caption readable over any part of the photo */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/25 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 p-10 text-white">
          <ShieldCheckIcon className="mb-4 size-8" />
          <h2 className="max-w-md text-3xl font-semibold tracking-tight">Every festive-season birth, counted and protected.</h2>
          <p className="mt-3 max-w-md text-white/80">
            Patient-level records are only visible to authorised staff in their own district or facility. All access is audited.
          </p>
          <p className="mt-6 text-[11px] text-white/60">
            Photo:{" "}
            <a className="underline underline-offset-2 hover:text-white" href="https://unsplash.com/@ozzzyphotos" target="_blank" rel="noopener noreferrer">
              Oswald Elsaboath
            </a>{" "}
            /{" "}
            <a className="underline underline-offset-2 hover:text-white" href="https://unsplash.com/photos/a-small-child-in-a-santa-suit-sitting-on-the-floor-5m5YP1oSJfE" target="_blank" rel="noopener noreferrer">
              Unsplash
            </a>
          </p>
        </div>
      </aside>
    </div>
  )
}
