from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from typing import Optional

class WebhookPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    message_id: str = Field(..., min_length=1)
    from_match: str = Field(..., alias="from", pattern=r"^\+\d+$") # E.164 regex
    to: str = Field(..., pattern=r"^\+\d+$")
    ts: datetime
    text: Optional[str] = Field(None, max_length=4096)