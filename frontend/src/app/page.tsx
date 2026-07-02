import Link from "next/link"

import { Button } from "@/components/ui/button"

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-center">
      <h1 className="text-h2 text-foreground">TalentLens</h1>
      <p className="max-w-md text-body text-muted-foreground">
        Business pages land in Phase 4. For now, browse the design system
        component library.
      </p>
      <Button asChild>
        <Link href="/style-guide">View style guide</Link>
      </Button>
    </main>
  )
}
