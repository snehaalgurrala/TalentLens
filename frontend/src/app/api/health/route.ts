import { NextResponse } from "next/server"

/** Liveness check for the Next.js server itself — distinct from the backend's own /health. */
export function GET() {
  return NextResponse.json({ status: "ok" })
}
