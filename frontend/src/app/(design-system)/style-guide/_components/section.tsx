import * as React from "react"

export interface SectionProps {
  id: string
  title: string
  description?: string
  children: React.ReactNode
}

function Section({ id, title, description, children }: SectionProps) {
  return (
    <section id={id} className="flex scroll-mt-20 flex-col gap-4">
      <div className="flex flex-col gap-1 border-b border-border pb-3">
        <h2 className="text-h4 text-foreground">{title}</h2>
        {description && (
          <p className="text-body text-muted-foreground">{description}</p>
        )}
      </div>
      <div className="flex flex-col gap-6">{children}</div>
    </section>
  )
}

/** Small labeled preview row used by the colors + typography sections. */
function Row({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      <span className="w-32 shrink-0 text-caption text-muted-foreground">
        {label}
      </span>
      {children}
    </div>
  )
}

export { Section, Row }
