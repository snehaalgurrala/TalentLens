from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    campaigns,
    job_descriptions,
    rankings,
    resumes,
    scoring_rules,
    users,
)

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
router.include_router(resumes.router, tags=["resumes"])
router.include_router(job_descriptions.router, tags=["job-descriptions"])
router.include_router(scoring_rules.router, prefix="/scoring-rules", tags=["scoring-rules"])
router.include_router(rankings.router, tags=["rankings"])
