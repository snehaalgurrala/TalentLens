"use client"

import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Row, Section } from "../_components/section"

function FeedbackSection() {
  return (
    <Section
      id="feedback"
      title="Feedback"
      description="Toast notifications (sonner, mounted once via ToastProvider in the root layout) and Skeleton loaders."
    >
      <Row label="Toast">
        <Button variant="outline" onClick={() => toast("Candidate saved")}>
          Default
        </Button>
        <Button
          variant="outline"
          onClick={() => toast.success("Campaign published")}
        >
          Success
        </Button>
        <Button
          variant="outline"
          onClick={() => toast.warning("Resume missing skills section")}
        >
          Warning
        </Button>
        <Button
          variant="outline"
          onClick={() => toast.error("Failed to parse resume")}
        >
          Error
        </Button>
      </Row>

      <Row label="Skeleton">
        <div className="flex w-64 flex-col gap-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      </Row>
    </Section>
  )
}

export { FeedbackSection }
