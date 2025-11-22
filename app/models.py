from pydantic import BaseModel
from typing import Any, Dict, Optional, List

class WebhookData(BaseModel):
    """Base webhook data structure - accepts any JSON structure"""
    __root__: Dict[str, Any]
    
    class Config:
        extra = "allow"  # Allow any additional fields
