import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"
import { auth } from "~/lib/auth" // server-side BetterAuth instance

const PUBLIC_PATHS = ["/login", "/signup"]
const PUBLIC_API_PREFIXES = ["/api/auth"]

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (PUBLIC_PATHS.includes(pathname)) {
    return NextResponse.next()
  }

  if (PUBLIC_API_PREFIXES.some(p => pathname.startsWith(p))) {
    return NextResponse.next()
  }

  const session = await auth.api.getSession({
    headers: request.headers,
  })

  if (!session) {
    const loginUrl = new URL("/login", request.url)
    loginUrl.searchParams.set("from", pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(png|jpg|jpeg|svg|ico)$).*)",
  ],
}
