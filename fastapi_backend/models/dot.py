from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from database.connection import Base


class DOT(Base):
    __tablename__ = "dots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # Relationships
    parks = relationship("Park", back_populates="dot")
    users = relationship("User", back_populates="dot")
    revenue_journals = relationship("RevenueJournal", back_populates="dot")
    revenue_objectives = relationship("RevenueObjective", back_populates="dot")

    def __repr__(self):
        return f"<DOT(id={self.id}, name='{self.name}')>"

