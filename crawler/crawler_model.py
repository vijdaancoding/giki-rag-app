from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
import json

class CrawlResults(BaseModel):
    url:str
    status_code: Optional[str]
    success: bool
    crawled_at: datetime = Field(default_factory=datetime.utcnow)
    markdown_path: Optional[str] = None
    html_path: Optional[str] = None
    pdf_path: Optional[str] = None
    metadata: Optional[dict] = None
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    memory_usage_mb: Optional[float] = None
