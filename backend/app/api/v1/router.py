from fastapi import APIRouter

from app.api.v1.endpoints import (
    assessment_analysis,
    assessment_analytics,
    assessment_config,
    assessment_invitations,
    assessment_sessions,
    assessment_transcripts,
    audit_log,
    auth,
    billing,
    campaigns,
    candidate_profile,
    candidates,
    communication_assessment,
    dashboard,
    data_export,
    job_descriptions,
    notification_preferences,
    notifications,
    organizations,
    platform_ai_config,
    platform_email_config,
    rankings,
    recruitment_settings,
    resumes,
    scoring_rules,
    sessions,
    system,
    users,
)

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
router.include_router(
    assessment_sessions.router, prefix="/assessment/session", tags=["assessment-sessions"]
)
router.include_router(
    assessment_invitations.router,
    prefix="/assessment/invitations",
    tags=["assessment-invitations"],
)
router.include_router(
    assessment_transcripts.router, prefix="/assessment/transcripts", tags=["assessment-transcripts"]
)
router.include_router(
    assessment_analysis.router, prefix="/assessment/analysis", tags=["assessment-analysis"]
)
router.include_router(
    communication_assessment.router,
    prefix="/assessment/communication",
    tags=["communication-assessment"],
)
router.include_router(
    assessment_analytics.router, prefix="/assessment/analytics", tags=["assessment-analytics"]
)
router.include_router(resumes.router, tags=["resumes"])
router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
router.include_router(candidate_profile.router, prefix="/candidates", tags=["candidate-profile"])
router.include_router(job_descriptions.router, tags=["job-descriptions"])
router.include_router(scoring_rules.router, prefix="/scoring-rules", tags=["scoring-rules"])
router.include_router(rankings.router, tags=["rankings"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])

# ── Settings & Admin Portal ────────────────────────────────────────────────
router.include_router(
    recruitment_settings.router, prefix="/recruitment-settings", tags=["recruitment-settings"]
)
router.include_router(
    assessment_config.router, prefix="/assessment-config", tags=["assessment-config"]
)
router.include_router(
    platform_ai_config.router, prefix="/platform/ai-config", tags=["platform-ai-config"]
)
router.include_router(
    platform_email_config.router, prefix="/platform/email-config", tags=["platform-email-config"]
)
router.include_router(
    notification_preferences.router,
    prefix="/notification-preferences",
    tags=["notification-preferences"],
)
router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
router.include_router(system.router, prefix="/system", tags=["system"])
router.include_router(billing.router, prefix="/billing", tags=["billing"])
router.include_router(audit_log.router, prefix="/audit-log", tags=["audit-log"])
router.include_router(data_export.router, prefix="/exports", tags=["data-export"])
