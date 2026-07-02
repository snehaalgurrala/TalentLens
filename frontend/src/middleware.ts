import { NextResponse, type NextRequest } from "next/server"

import {
  DEFAULT_AUTHENTICATED_ROUTE,
  DEFAULT_LOGIN_ROUTE,
  PROTECTED_ROUTE_PREFIXES,
  PUBLIC_ROUTES,
  SESSION_COOKIE_NAME,
} from "@/lib/constants"

/**
 * Coarse, edge-level route guard. The backend only issues JWTs in a JSON
 * response body (no httpOnly cookies), so this middleware can't verify the
 * token itself — it only checks the non-sensitive `tl_session` marker cookie
 * set by the client after a successful login/refresh. The authoritative
 * check happens client-side in `layouts/protected-shell.tsx`, which verifies
 * the session against the API before rendering protected content.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const hasSession = request.cookies.has(SESSION_COOKIE_NAME)

  const isProtectedRoute = PROTECTED_ROUTE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  )
  const isPublicAuthRoute = PUBLIC_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  )

  if (isProtectedRoute && !hasSession) {
    const loginUrl = new URL(DEFAULT_LOGIN_ROUTE, request.url)
    loginUrl.searchParams.set("redirect", pathname)
    return NextResponse.redirect(loginUrl)
  }

  if (isPublicAuthRoute && hasSession) {
    return NextResponse.redirect(new URL(DEFAULT_AUTHENTICATED_ROUTE, request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|manifest.webmanifest).*)",
  ],
}
