import type { UserSummary } from "@/types"

/**
 * Minimal markdown-subset renderer for note bodies: bold, italic, bullet
 * lines. HTML-escapes first, then applies limited regex transforms — the
 * escape must run before any tag injection so no user input can produce
 * raw HTML (never reorder these steps).
 */
export function renderNoteBody(body: string): string {
  const escaped = body
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")

  const withInline = escaped
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>")

  const lines = withInline.split("\n")
  const html: string[] = []
  let inList = false
  for (const line of lines) {
    const bulletMatch = /^-\s+(.+)$/.exec(line)
    if (bulletMatch) {
      if (!inList) {
        html.push("<ul>")
        inList = true
      }
      html.push(`<li>${bulletMatch[1]}</li>`)
      continue
    }
    if (inList) {
      html.push("</ul>")
      inList = false
    }
    html.push(line.length > 0 ? `<p>${line}</p>` : "<br/>")
  }
  if (inList) html.push("</ul>")
  return html.join("")
}

/** Resolves `@FullName` substrings against known org members into user ids. */
export function resolveMentions(body: string, members: UserSummary[]): string[] {
  return members.filter((member) => body.includes(`@${member.full_name}`)).map((member) => member.id)
}
