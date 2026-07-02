import { cn } from "@/lib/utils"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Grid } from "@/components/layout/grid"

function CardSkeleton() {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-2">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-7 w-16" />
        </div>
        <Skeleton className="size-10 shrink-0 rounded-lg" />
      </CardContent>
    </Card>
  )
}

function SummaryCardsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <Grid cols={1} colsSm={2} colsLg={4} gap="md">
      {Array.from({ length: count }).map((_, index) => (
        <CardSkeleton key={index} />
      ))}
    </Grid>
  )
}

function ChartSkeleton({ heightClassName = "h-64" }: { heightClassName?: string }) {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-32" />
      </CardHeader>
      <CardContent>
        <Skeleton className={cn("w-full", heightClassName)} />
      </CardContent>
    </Card>
  )
}

export { CardSkeleton, ChartSkeleton, SummaryCardsSkeleton }
