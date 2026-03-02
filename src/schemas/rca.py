"""根本原因分析（RCA）Pydanticスキーマ"""
from pydantic import BaseModel


class RCACandidateSchema(BaseModel):
    cause_category: str
    description: str
    confidence: float
    evidence: list[str]
    recommended_actions: list[str]


class RCAResultSchema(BaseModel):
    problem_id: str
    candidates: list[RCACandidateSchema]
    similar_incidents: list[str]
    affected_cis: list[str]
    analysis_summary: str
