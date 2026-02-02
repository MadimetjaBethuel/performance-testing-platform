import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

const PUBLIC_PATHS = ["/login", "/signup"] as const
const PUBLIC_API_PREFIXES = ["/api/auth"] as const

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Allow public paths
  if (PUBLIC_PATHS.includes(pathname as any)) {
    return NextResponse.next()
  }

  // Allow public API routes
  if (PUBLIC_API_PREFIXES.some(prefix => pathname.startsWith(prefix))) {
    return NextResponse.next()
  }

  // Check session
  const sessionToken = request.cookies.get("better-auth.session_token")
  const hasSession = !!sessionToken?.value

  if (!hasSession) {
    const loginUrl = new URL("/login", request.url)
    loginUrl.searchParams.set("from", pathname)
    
    const response = NextResponse.redirect(loginUrl)
    
    // Optional: Add security headers
    response.headers.set("X-Redirect-Reason", "unauthorized")
    
    return response
  }

  // Optional: Add security headers to authenticated requests
  const response = NextResponse.next()
  response.headers.set("X-Authenticated", "true")
  
  return response
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt|.*\\.(?:png|jpg|jpeg|gif|svg|webp|ico|woff|woff2|ttf|eot)$).*)",
  ],
}