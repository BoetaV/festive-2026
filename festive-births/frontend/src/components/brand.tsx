import Image from "next/image"
import Link from "next/link"
import { cn } from "@/lib/utils"

/** Official ECDoH logo. It sits on a white plate in dark mode so it stays legible. */
export function EcdohLogo({ className, priority }: { className?: string; priority?: boolean }) {
  return (
    <span className={cn("inline-flex shrink-0 items-center rounded-md dark:bg-white dark:px-1.5 dark:py-0.5", className)}>
      <Image
        src="/brand/ecdoh-logo.jpg"
        alt="Province of the Eastern Cape – Department of Health"
        width={378}
        height={112}
        priority={priority}
        className="h-12 w-auto sm:h-16"
      />
    </span>
  )
}

export function Brand() {
  return (
    <Link href="/" className="flex items-center gap-3" aria-label="Festive Births – home">
      <EcdohLogo priority />
      <span className="hidden border-l-2 border-gold pl-3 leading-none sm:block">
        <span className="block text-lg font-black tracking-tight text-brand-deep uppercase">Festive Births</span>
        <span className="eyebrow mt-1 block text-[10px] text-primary dark:text-gold">Season 2026/27</span>
      </span>
    </Link>
  )
}
