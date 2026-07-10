export interface ScoreDistributionBucket {
  label: string
  count: number
}

export interface CompletionTrendPoint {
  date: string
  completed_count: number
}

export interface PerformerEntry {
  session_id: string
  candidate_name: string
  campaign_title: string
  overall_score: number
}

export interface AssessmentAnalytics {
  total_sessions: number
  completed_sessions: number
  completion_rate: number
  average_communication_score: number | null
  average_read_aloud_score: number | null
  average_listen_repeat_score: number | null
  total_invitations_sent: number
  invitations_accepted: number
  invitation_acceptance_rate: number
  top_performers: PerformerEntry[]
  lowest_performers: PerformerEntry[]
  score_distribution: ScoreDistributionBucket[]
  completion_trend: CompletionTrendPoint[]
}
