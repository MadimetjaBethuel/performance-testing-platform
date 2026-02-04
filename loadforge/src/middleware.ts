import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

const PUBLIC_PATHS = ["/login", "/signup"]
const PUBLIC_API_PREFIXES = ["/api/auth"]

const SESSION_COOKIE = "better-auth.session" // ← adjust if needed

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // 1. Allow public pages
  if (PUBLIC_PATHS.includes(pathname)) {
    return NextResponse.next()
  }

  // 2. Allow auth APIs
  if (PUBLIC_API_PREFIXES.some(p => pathname.startsWith(p))) {
    return NextResponse.next()
  }

  // 3. Edge-safe session check (cookie presence ONLY)
  const sessionToken = request.cookies.get(SESSION_COOKIE)?.value

  if (!sessionToken) {
    const loginUrl = new URL("/login", request.url)
    loginUrl.searchParams.set("from", pathname)
    return NextResponse.redirect(loginUrl)
  }

  // 4. Authenticated
  return NextResponse.next()
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt|.*\\.(?:png|jpg|jpeg|gif|svg|webp|ico|woff|woff2|ttf|eot)$).*)",
  ],
}
