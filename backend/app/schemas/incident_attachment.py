from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class IncidentAttachmentResponse(BaseModel):
    id: int
    incident_id: int
    file_name: str
    file_size: int
    mime_type: str
    uploaded_by_id: int
    created_at: datetime
    file_url: str

    model_config = ConfigDict(from_attributes=True)
