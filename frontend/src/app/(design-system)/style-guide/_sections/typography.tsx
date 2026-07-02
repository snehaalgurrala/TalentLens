import { Row, Section } from "../_components/section"

const scale: { label: string; className: string; sample: string }[] = [
  { label: "Display", className: "text-display", sample: "Find great talent" },
  { label: "H1", className: "text-h1", sample: "Find great talent" },
  { label: "H2", className: "text-h2", sample: "Find great talent" },
  { label: "H3", className: "text-h3", sample: "Find great talent" },
  { label: "H4", className: "text-h4", sample: "Find great talent" },
  { label: "H5", className: "text-h5", sample: "Find great talent" },
  { label: "H6", className: "text-h6", sample: "Find great talent" },
  {
    label: "Subtitle",
    className: "text-subtitle",
    sample: "AI-powered recruitment intelligence",
  },
  {
    label: "Body",
    className: "text-body",
    sample: "TalentLens analyzes resumes and ranks candidates automatically.",
  },
  {
    label: "Caption",
    className: "text-caption",
    sample: "Last updated 2 minutes ago",
  },
]

function TypographySection() {
  return (
    <Section
      id="typography"
      title="Typography"
      description="Inter, with a Display through Caption scale defined in globals.css and mirrored in design-system/tokens/typography.ts."
    >
      <div className="flex flex-col gap-4">
        {scale.map(({ label, className, sample }) => (
          <Row key={label} label={label}>
            <p className={`${className} text-foreground`}>{sample}</p>
          </Row>
        ))}
      </div>
    </Section>
  )
}

export { TypographySection }
