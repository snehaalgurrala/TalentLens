import { Skeleton } from "@/components/ui/skeleton"

export default function AuthRouteLoading() {
  return (
    <div className="flex w-full flex-col gap-4">
      <Skeleton className="h-6 w-32 self-center" />
      <Skeleton className="h-40 w-full rounded-xl" />
    </div>
  )
}
