from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    original_filename: str
    content_type: str | None
    size_bytes: int
    created_at: datetime
    updated_at: datetime