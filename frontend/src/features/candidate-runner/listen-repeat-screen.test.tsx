import { act, fireEvent, render, screen } from "@testing-library/react"

import { AssessmentRunnerProvider } from "./assessment-runner-context"
import { ListenRepeatScreen } from "./listen-repeat-screen"

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}))

function renderScreen() {
  return render(
    <AssessmentRunnerProvider>
      <ListenRepeatScreen />
    </AssessmentRunnerProvider>
  )
}

describe("ListenRepeatScreen", () => {
  const originalSpeechSynthesis = (window as unknown as { speechSynthesis?: unknown })
    .speechSynthesis
  const originalUtterance = (window as unknown as { SpeechSynthesisUtterance?: unknown })
    .SpeechSynthesisUtterance

  let speakMock: jest.Mock
  let cancelMock: jest.Mock
  let lastUtterance: { text: string; onend?: () => void; onerror?: () => void } | undefined

  beforeEach(() => {
    speakMock = jest.fn((utterance) => {
      lastUtterance = utterance
    })
    cancelMock = jest.fn()
    ;(window as unknown as { speechSynthesis: unknown }).speechSynthesis = {
      speak: speakMock,
      cancel: cancelMock,
    }
    ;(window as unknown as { SpeechSynthesisUtterance: unknown }).SpeechSynthesisUtterance =
      function SpeechSynthesisUtteranceMock(this: { text: string }, text: string) {
        this.text = text
      }
  })

  afterEach(() => {
    ;(window as unknown as { speechSynthesis: unknown }).speechSynthesis = originalSpeechSynthesis
    ;(window as unknown as { SpeechSynthesisUtterance: unknown }).SpeechSynthesisUtterance =
      originalUtterance
    lastUtterance = undefined
  })

  it("speaks the sentence via the Web Speech API and flips to Played once speech ends", () => {
    renderScreen()

    expect(
      screen.getByRole("button", { name: /Play Sentence/i })
    ).not.toBeDisabled()

    fireEvent.click(screen.getByRole("button", { name: /Play Sentence/i }))

    expect(speakMock).toHaveBeenCalledTimes(1)
    expect(lastUtterance?.text).toContain(
      "Innovation distinguishes between a leader and a follower"
    )
    expect(screen.getByRole("button", { name: /Playing…/i })).toBeDisabled()

    act(() => {
      lastUtterance?.onend?.()
    })

    expect(screen.getByRole("button", { name: /Played/i })).toBeDisabled()
  })

  it("still flips to Played if speech synthesis errors out mid-utterance", () => {
    renderScreen()

    fireEvent.click(screen.getByRole("button", { name: /Play Sentence/i }))
    act(() => {
      lastUtterance?.onerror?.()
    })

    expect(screen.getByRole("button", { name: /Played/i })).toBeDisabled()
  })

  it("falls back to showing the sentence as text when speech synthesis is unsupported", () => {
    ;(window as unknown as { speechSynthesis?: unknown }).speechSynthesis = undefined

    renderScreen()

    expect(screen.getByText(/Innovation distinguishes/i)).toBeInTheDocument()
    expect(speakMock).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole("button", { name: /I've read the sentence/i }))

    expect(screen.getByRole("button", { name: /Ready/i })).toBeDisabled()
  })
})
