import { Briefcase, Mail, MapPin, Users } from "lucide-react"

import { Button } from "@/components/ui/button"
import { CampaignCard } from "@/components/ui/campaign-card"
import { CandidateCard } from "@/components/ui/candidate-card"
import { DashboardCard } from "@/components/ui/dashboard-card"
import { StatisticCard } from "@/components/ui/statistic-card"
import { Grid } from "@/components/layout/grid"
import { Section } from "../_components/section"

function CardsSection() {
  return (
    <Section
      id="cards"
      title="Cards"
      description="Dashboard, Statistic, Candidate, and Campaign cards are compositions over the base shadcn Card — not CVA variants, since their layouts differ structurally."
    >
      <Grid cols={1} colsMd={2} colsLg={4} gap="md">
        <StatisticCard
          label="Total candidates"
          value="1,204"
          icon={Users}
          trend={{ value: 12, direction: "up", label: "this month" }}
        />
        <StatisticCard
          label="Open campaigns"
          value="8"
          icon={Briefcase}
          trend={{ value: -3, direction: "down" }}
        />
        <DashboardCard
          title="Screening queue"
          description="Candidates awaiting review"
          icon={Users}
        >
          <p className="text-h3 font-semibold text-foreground">42</p>
        </DashboardCard>
        <DashboardCard title="Quick actions" icon={Briefcase}>
          <Button size="sm" className="w-full">
            Create campaign
          </Button>
        </DashboardCard>
      </Grid>

      <Grid cols={1} colsMd={2} gap="md">
        <CandidateCard
          name="Amara Okafor"
          role="Senior Product Designer"
          initials="AO"
          matchScore={92}
          status={{ label: "Shortlisted", variant: "shortlisted" }}
          meta={[
            { icon: Mail, label: "amara.okafor@example.com" },
            { icon: MapPin, label: "Lagos, Nigeria (Remote)" },
          ]}
          actions={
            <Button size="sm" variant="outline">
              View profile
            </Button>
          }
        />
        <CampaignCard
          title="Senior Frontend Engineer"
          description="Remote · Full-time"
          status={{ label: "Active", variant: "active" }}
          applicantCount={128}
          dateRange="Jun 1 – Jul 31"
          progress={64}
          actions={
            <Button size="sm" variant="ghost">
              Manage
            </Button>
          }
        />
      </Grid>
    </Section>
  )
}

export { CardsSection }
