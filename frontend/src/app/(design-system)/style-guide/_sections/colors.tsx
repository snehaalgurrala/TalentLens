import { Section } from "../_components/section"

const swatches: { label: string; bg: string; fg?: string }[] = [
  { label: "background", bg: "bg-background", fg: "text-foreground" },
  { label: "surface", bg: "bg-surface", fg: "text-foreground" },
  { label: "primary", bg: "bg-primary", fg: "text-primary-foreground" },
  { label: "secondary", bg: "bg-secondary", fg: "text-secondary-foreground" },
  { label: "success", bg: "bg-success", fg: "text-success-foreground" },
  { label: "warning", bg: "bg-warning", fg: "text-warning-foreground" },
  {
    label: "destructive",
    bg: "bg-destructive",
    fg: "text-destructive-foreground",
  },
  {
    label: "accent-purple",
    bg: "bg-accent-purple",
    fg: "text-accent-purple-foreground",
  },
  { label: "muted", bg: "bg-muted", fg: "text-muted-foreground" },
  { label: "accent", bg: "bg-accent", fg: "text-accent-foreground" },
  { label: "card", bg: "bg-card", fg: "text-card-foreground" },
]

function ColorsSection() {
  return (
    <Section
      id="colors"
      title="Colors"
      description="Semantic tokens backed by TalentSmart brand HSL values (src/app/globals.css). Never reference raw hex in components."
    >
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {swatches.map(({ label, bg, fg }) => (
          <div
            key={label}
            className={`flex h-20 flex-col justify-between rounded-lg border border-border p-3 ${bg} ${fg ?? ""}`}
          >
            <span className="text-caption font-medium">{label}</span>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-3">
        {[
          { label: "success-emphasis", className: "text-success-emphasis" },
          { label: "warning-emphasis", className: "text-warning-emphasis" },
          {
            label: "destructive-emphasis",
            className: "text-destructive-emphasis",
          },
          {
            label: "accent-purple-emphasis",
            className: "text-accent-purple-emphasis",
          },
        ].map(({ label, className }) => (
          <div
            key={label}
            className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2"
          >
            <span className={`${className} text-sm font-medium`}>
              text-{label}
            </span>
          </div>
        ))}
      </div>
    </Section>
  )
}

export { ColorsSection }
