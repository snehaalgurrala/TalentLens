from fastapi import APIRouter

router = APIRouter()

# Endpoint routers will be included here as features are built, e.g.:
# from app.api.v1.endpoints import candidates, jobs, auth
# router.include_router(auth.router,       prefix="/auth",       tags=["auth"])
# router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
# router.include_router(jobs.router,       prefix="/jobs",       tags=["jobs"])
