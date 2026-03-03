"""変更管理リスク評価Pydanticスキーマ"""

from pydantic import BaseModel


class RiskFactorSchema(BaseModel):
    factor_name: str
    score: int
    description: str


class RiskAssessmentResultSchema(BaseModel):
    change_id: str
    total_score: int
    risk_level: str
    factors: list[RiskFactorSchema]
    recommendations: list[str]
    maintenance_window_required: bool
