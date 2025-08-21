from pydantic import BaseModel
from typing import Literal, Optional

Category = Literal["personal_id","personal_employment","personal_education","personal_health",
                   "family_marriage","family_kids","family_housing","family_taxes","family_vehicle","family_utilities",
                   "purchases_invoices","purchases_warranty","purchases_manuals","subscriptions",
                   "travel","activities","legal","misc"]

class RouteChoice(BaseModel):
    category: Category
    bucket: Optional[str] = None
    date: Optional[str] = None
    filename_hint: Optional[str] = None
