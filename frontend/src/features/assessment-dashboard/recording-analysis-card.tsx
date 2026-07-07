import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { AssessmentRecordingDetail, RecordingType } from "@/types"

export interface RecordingAnalysisCardProps {
  recordingType: RecordingType
  detail: AssessmentRecordingDetail | undefined
}

const TITLE_BY_TYPE: Record<RecordingType, string> = {
  READ_ALOUD: "Read Aloud",
  LISTEN_REPEAT: "Listen & Repeat",
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-caption text-muted-foreground">{label}</span>
      <span className="text-sm font-medium tabular-nums text-foreground">{value}</span>
    </div>
  )
}

function RecordingAnalysisCard({ recordingType, detail }: RecordingAnalysisCardProps) {
  const title = TITLE_BY_TYPE[recordingType]

  if (!detail) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          This candidate hasn&rsquo;t recorded this section yet.
        </CardContent>
      </Card>
    )
  }

  const { reference_sentence: referenceSentence, transcript, analysis } = detail

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-caption text-muted-foreground">
            {recordingType === "READ_ALOUD" ? "Reference Sentence" : "Original Sentence"}
          </span>
          <p className="text-sm text-foreground">{referenceSentence}</p>
        </div>

        <div className="flex flex-col gap-1">
          <span className="text-caption text-muted-foreground">Transcript</span>
          {!transcript || transcript.status === "PENDING" || transcript.status === "PROCESSING" ? (
            <Badge variant="pending" className="w-fit">
              Transcription in progress
            </Badge>
          ) : transcript.status === "FAILED" ? (
            <Badge variant="destructive" className="w-fit">
              {transcript.error_message ?? "Transcription failed"}
            </Badge>
          ) : (
            <p className="text-sm text-foreground">{transcript.transcript || "(empty transcript)"}</p>
          )}
        </div>

        {!analysis ? (
          <Badge variant="pending" className="w-fit">
            Awaiting analysis
          </Badge>
        ) : analysis.status === "PENDING" ? (
          <Badge variant="pending" className="w-fit">
            Analysis pending
          </Badge>
        ) : analysis.status === "FAILED" ? (
          <Badge variant="destructive" className="w-fit">
            {analysis.error_message ?? "Analysis failed"}
          </Badge>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {recordingType === "READ_ALOUD" ? (
              <>
                <MetricRow label="Word Accuracy" value={`${analysis.word_accuracy ?? "—"}%`} />
                <MetricRow label="Reading Speed" value={`${analysis.reading_speed_wpm ?? "—"} wpm`} />
              </>
            ) : (
              <>
                <MetricRow
                  label="Semantic Similarity"
                  value={`${analysis.semantic_similarity ?? "—"}%`}
                />
                <MetricRow label="Keyword Coverage" value={`${analysis.keyword_coverage ?? "—"}%`} />
              </>
            )}
            <MetricRow label="Completion" value={`${analysis.completion_percentage ?? "—"}%`} />
            <MetricRow label="Overall Score" value={`${analysis.overall_score ?? "—"}%`} />
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export { RecordingAnalysisCard }
