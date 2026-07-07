from fastapi import APIRouter

from app.api.v1.endpoints import (
    assessment_analysis,
    assessment_sessions,
    assessment_transcripts,
    auth,
    campaigns,
    candidate_profile,
    candidates,
    dashboard,
    job_descriptions,
    organizations,
    rankings,
    resumes,
    scoring_rules,
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
    assessment_transcripts.router, prefix="/assessment/transcripts", tags=["assessment-transcripts"]
)
router.include_router(
    assessment_analysis.router, prefix="/assessment/analysis", tags=["assessment-analysis"]
)
router.include_router(resumes.router, tags=["resumes"])
router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
router.include_router(candidate_profile.router, prefix="/candidates", tags=["candidate-profile"])
router.include_router(job_descriptions.router, tags=["job-descriptions"])
router.include_router(scoring_rules.router, prefix="/scoring-rules", tags=["scoring-rules"])
router.include_router(rankings.router, tags=["rankings"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
