from fastapi import APIRouter

from app.api.v1.endpoints import (
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
router.include_router(resumes.router, tags=["resumes"])
router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
router.include_router(candidate_profile.router, prefix="/candidates", tags=["candidate-profile"])
router.include_router(job_descriptions.router, tags=["job-descriptions"])
router.include_router(scoring_rules.router, prefix="/scoring-rules", tags=["scoring-rules"])
router.include_router(rankings.router, tags=["rankings"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
