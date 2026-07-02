"use client"

import * as React from "react"
import { Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Row, Section } from "../_components/section"

function ButtonsSection() {
  const [loading, setLoading] = React.useState(false)

  return (
    <Section
      id="buttons"
      title="Buttons"
      description="CVA variants extending shadcn's base Button — default (primary), secondary, outline, ghost, success, danger, destructive, link."
    >
      <Row label="Variants">
        <Button variant="default">Primary</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="outline">Outline</Button>
        <Button variant="ghost">Ghost</Button>
        <Button variant="success">Success</Button>
        <Button variant="danger">Danger</Button>
        <Button variant="destructive">Destructive</Button>
        <Button variant="link">Link</Button>
      </Row>

      <Row label="Sizes">
        <Button size="xs">Extra small</Button>
        <Button size="sm">Small</Button>
        <Button size="default">Default</Button>
        <Button size="lg">Large</Button>
      </Row>

      <Row label="Icon">
        <Button size="icon" aria-label="Add">
          <Plus />
        </Button>
        <Button variant="outline" size="icon-sm" aria-label="Add">
          <Plus />
        </Button>
        <Button variant="secondary">
          <Plus />
          With icon
        </Button>
      </Row>

      <Row label="Loading">
        <Button isLoading>Saving</Button>
        <Button
          variant="outline"
          isLoading={loading}
          onClick={() => {
            setLoading(true)
            setTimeout(() => setLoading(false), 1500)
          }}
        >
          Click to load
        </Button>
      </Row>

      <Row label="Disabled">
        <Button disabled>Primary</Button>
        <Button variant="outline" disabled>
          Outline
        </Button>
      </Row>
    </Section>
  )
}

export { ButtonsSection }
