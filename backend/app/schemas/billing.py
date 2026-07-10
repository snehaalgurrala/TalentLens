from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class BillingUsageResponse(BaseModel):
    users_count: int
    storage_used_mb: float
    assessments_used: int
    embedding_operations_count: int
    plan_name: Literal["Coming Soon"] = "Coming Soon"
    period_start: datetime
    period_end: datetime
