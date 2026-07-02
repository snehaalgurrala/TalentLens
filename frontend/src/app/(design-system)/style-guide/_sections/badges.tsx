import { Badge } from "@/components/ui/badge"
import { Row, Section } from "../_components/section"

function BadgesSection() {
  return (
    <Section
      id="badges"
      title="Badges"
      description="Status variants use a tinted background + emphasis text color, verified WCAG AA — never a raw brand hue as text-on-tint."
    >
      <Row label="Status">
        <Badge variant="active">Active</Badge>
        <Badge variant="pending">Pending</Badge>
        <Badge variant="success">Success</Badge>
        <Badge variant="warning">Warning</Badge>
        <Badge variant="rejected">Rejected</Badge>
        <Badge variant="shortlisted">Shortlisted</Badge>
      </Row>
      <Row label="Base">
        <Badge variant="default">Default</Badge>
        <Badge variant="secondary">Secondary</Badge>
        <Badge variant="outline">Outline</Badge>
        <Badge variant="destructive">Destructive</Badge>
      </Row>
    </Section>
  )
}

export { BadgesSection }
