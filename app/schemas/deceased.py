from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class FamilyRelationBase(BaseModel):
    relation: str = Field(..., max_length=50)
    contact_phone: str = Field(..., max_length=20)
    contact_address: Optional[str] = None
    is_primary: int = 0


class FamilyRelationCreate(FamilyRelationBase):
    user_id: int


class FamilyRelationResponse(FamilyRelationBase):
    id: int
    user_id: int
    deceased_id: int

    class Config:
        from_attributes = True


class DeceasedBase(BaseModel):
    name: str = Field(..., max_length=100)
    gender: str = Field(..., max_length=10)
    birth_date: Optional[date] = None
    death_date: date
    death_cause: Optional[str] = None
    id_card: str = Field(..., max_length=18)
    nationality: Optional[str] = None
    ethnicity: Optional[str] = None
    address: str = Field(..., max_length=255)
    death_place: str = Field(..., max_length=255)
    remark: Optional[str] = None

    @field_validator("id_card")
    def validate_id_card(cls, v):
        if len(v) not in (15, 18):
            raise ValueError("身份证号必须为15位或18位")
        return v

    @field_validator("gender")
    def validate_gender(cls, v):
        if v not in ("男", "女"):
            raise ValueError("性别必须为'男'或'女'")
        return v


class DeceasedCreate(DeceasedBase):
    family_relations: List[FamilyRelationCreate]


class DeceasedUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    death_date: Optional[date] = None
    death_cause: Optional[str] = None
    id_card: Optional[str] = None
    nationality: Optional[str] = None
    ethnicity: Optional[str] = None
    address: Optional[str] = None
    death_place: Optional[str] = None
    remark: Optional[str] = None


class DeceasedResponse(DeceasedBase):
    id: int
    is_archived: bool
    archived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    family_relations: List[FamilyRelationResponse] = []

    class Config:
        from_attributes = True


class DeceasedArchive(BaseModel):
    archived: bool = True
