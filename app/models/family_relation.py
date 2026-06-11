from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class FamilyRelation(Base):
    __tablename__ = "family_relations"

    id = Column(Integer, primary_key=True, index=True)
    deceased_id = Column(Integer, ForeignKey("deceased.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    relation = Column(String(50), nullable=False)
    contact_phone = Column(String(20), nullable=False)
    contact_address = Column(String(255), nullable=True)
    is_primary = Column(Integer, default=0)

    deceased = relationship("Deceased", back_populates="family_relations")
    user = relationship("User", back_populates="family_relations")
