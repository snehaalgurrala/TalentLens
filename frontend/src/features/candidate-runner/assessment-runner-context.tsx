"use client"

import * as React from "react"

import { SECTION1_DURATION_SECONDS } from "./mock-data"
import type {
  DeviceCheckKey,
  DeviceCheckState,
  RecordingAnswer,
  RecordingUploadState,
} from "./types"

const initialUploadState: RecordingUploadState = { status: "idle", progress: 0, error: null }

interface AssessmentRunnerValue {
  sessionId: string | null
  setSessionId: (id: string | null) => void

  deviceCheck: DeviceCheckState
  setDeviceCheckPassed: (key: DeviceCheckKey, passed: boolean) => void
  allDeviceChecksPassed: boolean

  answers: Record<number, string>
  setAnswer: (questionId: number, optionId: string) => void
  section1Submitted: boolean
  submitSection1: () => void

  section1DeadlineAt: number | null
  ensureSection1Timer: () => void

  readAloudRecording: RecordingAnswer | null
  setReadAloudRecording: (recording: RecordingAnswer | null) => void
  readAloudCompleted: boolean
  completeReadAloud: () => void
  readAloudUpload: RecordingUploadState
  updateReadAloudUpload: (patch: Partial<RecordingUploadState>) => void

  listenRepeatRecording: RecordingAnswer | null
  setListenRepeatRecording: (recording: RecordingAnswer | null) => void
  listenRepeatCompleted: boolean
  completeListenRepeat: () => void
  listenRepeatUpload: RecordingUploadState
  updateListenRepeatUpload: (patch: Partial<RecordingUploadState>) => void

  resetAssessment: () => void
}

const initialDeviceCheck: DeviceCheckState = {
  browser: false,
  internet: false,
  speaker: false,
  microphone: false,
}

function revokeRecording(recording: RecordingAnswer | null) {
  if (recording) URL.revokeObjectURL(recording.url)
}

const AssessmentRunnerContext = React.createContext<AssessmentRunnerValue | null>(null)

function AssessmentRunnerProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = React.useState<string | null>(null)
  const [deviceCheck, setDeviceCheck] = React.useState<DeviceCheckState>(initialDeviceCheck)
  const [answers, setAnswers] = React.useState<Record<number, string>>({})
  const [section1Submitted, setSection1Submitted] = React.useState(false)
  const [section1DeadlineAt, setSection1DeadlineAt] = React.useState<number | null>(null)
  const [readAloudRecording, setReadAloudRecording] = React.useState<RecordingAnswer | null>(null)
  const [readAloudCompleted, setReadAloudCompleted] = React.useState(false)
  const [readAloudUpload, setReadAloudUpload] =
    React.useState<RecordingUploadState>(initialUploadState)
  const [listenRepeatRecording, setListenRepeatRecording] = React.useState<RecordingAnswer | null>(
    null
  )
  const [listenRepeatCompleted, setListenRepeatCompleted] = React.useState(false)
  const [listenRepeatUpload, setListenRepeatUpload] =
    React.useState<RecordingUploadState>(initialUploadState)

  const setDeviceCheckPassed = React.useCallback((key: DeviceCheckKey, passed: boolean) => {
    setDeviceCheck((prev) => ({ ...prev, [key]: passed }))
  }, [])

  const setAnswer = React.useCallback((questionId: number, optionId: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: optionId }))
  }, [])

  const submitSection1 = React.useCallback(() => {
    setSection1Submitted(true)
  }, [])

  const ensureSection1Timer = React.useCallback(() => {
    setSection1DeadlineAt((prev) => prev ?? Date.now() + SECTION1_DURATION_SECONDS * 1000)
  }, [])

  const completeReadAloud = React.useCallback(() => {
    setReadAloudCompleted(true)
  }, [])

  const completeListenRepeat = React.useCallback(() => {
    setListenRepeatCompleted(true)
  }, [])

  const updateReadAloudUpload = React.useCallback((patch: Partial<RecordingUploadState>) => {
    setReadAloudUpload((prev) => ({ ...prev, ...patch }))
  }, [])

  const updateListenRepeatUpload = React.useCallback((patch: Partial<RecordingUploadState>) => {
    setListenRepeatUpload((prev) => ({ ...prev, ...patch }))
  }, [])

  const resetAssessment = React.useCallback(() => {
    setSessionId(null)
    setDeviceCheck(initialDeviceCheck)
    setAnswers({})
    setSection1Submitted(false)
    setSection1DeadlineAt(null)
    setReadAloudRecording((prev) => {
      revokeRecording(prev)
      return null
    })
    setReadAloudCompleted(false)
    setReadAloudUpload(initialUploadState)
    setListenRepeatRecording((prev) => {
      revokeRecording(prev)
      return null
    })
    setListenRepeatCompleted(false)
    setListenRepeatUpload(initialUploadState)
  }, [])

  const allDeviceChecksPassed = Object.values(deviceCheck).every(Boolean)

  const value = React.useMemo<AssessmentRunnerValue>(
    () => ({
      sessionId,
      setSessionId,
      deviceCheck,
      setDeviceCheckPassed,
      allDeviceChecksPassed,
      answers,
      setAnswer,
      section1Submitted,
      submitSection1,
      section1DeadlineAt,
      ensureSection1Timer,
      readAloudRecording,
      setReadAloudRecording,
      readAloudCompleted,
      completeReadAloud,
      readAloudUpload,
      updateReadAloudUpload,
      listenRepeatRecording,
      setListenRepeatRecording,
      listenRepeatCompleted,
      completeListenRepeat,
      listenRepeatUpload,
      updateListenRepeatUpload,
      resetAssessment,
    }),
    [
      sessionId,
      deviceCheck,
      setDeviceCheckPassed,
      allDeviceChecksPassed,
      answers,
      setAnswer,
      section1Submitted,
      submitSection1,
      section1DeadlineAt,
      ensureSection1Timer,
      readAloudRecording,
      readAloudCompleted,
      completeReadAloud,
      readAloudUpload,
      updateReadAloudUpload,
      listenRepeatRecording,
      listenRepeatCompleted,
      completeListenRepeat,
      listenRepeatUpload,
      updateListenRepeatUpload,
      resetAssessment,
    ]
  )

  return (
    <AssessmentRunnerContext.Provider value={value}>{children}</AssessmentRunnerContext.Provider>
  )
}

function useAssessmentRunner(): AssessmentRunnerValue {
  const ctx = React.useContext(AssessmentRunnerContext)
  if (!ctx) {
    throw new Error("useAssessmentRunner must be used within an AssessmentRunnerProvider")
  }
  return ctx
}

export { AssessmentRunnerProvider, useAssessmentRunner }
