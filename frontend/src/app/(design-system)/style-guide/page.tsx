import { PageWrapper } from "@/components/layout/page-wrapper"
import { ThemeToggle } from "./_components/theme-toggle"
import { BadgesSection } from "./_sections/badges"
import { ButtonsSection } from "./_sections/buttons"
import { CardsSection } from "./_sections/cards"
import { ChartsMotionSection } from "./_sections/charts-motion"
import { ColorsSection } from "./_sections/colors"
import { DataTableSection } from "./_sections/data-table"
import { FeedbackSection } from "./_sections/feedback"
import { FormControlsSection } from "./_sections/form-controls"
import { LayoutSection } from "./_sections/layout"
import { MediaSection } from "./_sections/media"
import { NavigationSection } from "./_sections/navigation"
import { OverlaysSection } from "./_sections/overlays"
import { TypographySection } from "./_sections/typography"

const sections = [
  { id: "colors", label: "Colors" },
  { id: "typography", label: "Typography" },
  { id: "buttons", label: "Buttons" },
  { id: "form-controls", label: "Form controls" },
  { id: "badges", label: "Badges" },
  { id: "cards", label: "Cards" },
  { id: "data-table", label: "Tables" },
  { id: "overlays", label: "Overlays" },
  { id: "navigation", label: "Navigation" },
  { id: "feedback", label: "Feedback" },
  { id: "media", label: "Media & uploads" },
  { id: "layout", label: "Layout" },
  { id: "charts-motion", label: "Charts & motion" },
]

export default function StyleGuidePage() {
  return (
    <PageWrapper
      title="TalentLens Design System"
      description="Reusable, brand-consistent components for every page built from Phase 4 onward. This route is internal only — not a business page."
      actions={<ThemeToggle />}
    >
      <nav
        aria-label="Style guide sections"
        className="flex flex-wrap gap-x-4 gap-y-1 border-b border-border pb-4 text-sm"
      >
        {sections.map(({ id, label }) => (
          <a
            key={id}
            href={`#${id}`}
            className="text-muted-foreground transition-colors hover:text-foreground"
          >
            {label}
          </a>
        ))}
      </nav>

      <div className="flex flex-col gap-12 py-4">
        <ColorsSection />
        <TypographySection />
        <ButtonsSection />
        <FormControlsSection />
        <BadgesSection />
        <CardsSection />
        <DataTableSection />
        <OverlaysSection />
        <NavigationSection />
        <FeedbackSection />
        <MediaSection />
        <LayoutSection />
        <ChartsMotionSection />
      </div>
    </PageWrapper>
  )
}
