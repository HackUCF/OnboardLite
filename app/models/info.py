from typing import List, Optional

# Import data types
from ..models.user import PublicContact
from pydantic import BaseModel


class InfoModel(BaseModel):
    name: Optional[str] = "Onboard"
    description: Optional[str] = None
    credits: List[PublicContact]
