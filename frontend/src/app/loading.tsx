import { Loader2 } from "lucide-react"

export default function RootLoading() {
  return (
    <div className="flex min-h-dvh w-full items-center justify-center bg-background">
      <Loader2 className="size-6 animate-spin text-muted-foreground" aria-label="Loading" />
    </div>
  )
}
