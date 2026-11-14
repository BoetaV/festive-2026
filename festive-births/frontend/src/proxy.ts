import { NextResponse, type NextRequest } from "next/server"

/**
 * Optimistic route guard: bounce visitors without a session cookie to /login.
 * The real authorisation check happens in the API on every request.
 */
export function proxy(request: NextRequest) {
  if (!request.cookies.has("fb_session")) {
    const url = new URL("/login", request.url)
    url.searchParams.set("next", request.nextUrl.pathname)
    return NextResponse.redirect(url)
  }
  return NextResponse.next()
}

export const config = {
  matcher: ["/app/:path*", "/change-password"],
}
