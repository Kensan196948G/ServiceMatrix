"""Change管理リスク自動評価サービス テスト"""
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio

from src.models.change import Change
from src.services.change_risk_service import ChangeRiskService, RiskFactor


@pytest.fixture
def service() -> ChangeRiskService:
    return ChangeRiskService()


async def _create_change(db_session, **kwargs) -> Change:
    """テスト用Changeオブジェクトを直接作成（SQLite対応）"""
    now = datetime.now(UTC)
    defaults = {
        "change_id": uuid.uuid4(),
        "change_number": f"CHG-TEST-{uuid.uuid4().hex[:6].upper()}",
        "title": "テスト変更",
        "description": "これはテスト変更の詳細な説明です。十分な長さのある説明文を記述しています。",
        "change_type": "Normal",
        "status": "Draft",
        "risk_score": 0,
        "risk_level": "Low",
        "test_plan": "テスト計画あり",
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    change = Change(**defaults)
    db_session.add(change)
    await db_session.flush()
    return change


@pytest.mark.asyncio
async def test_assess_risk_emergency_change(db_session):
    """Emergency変更 → 高スコア"""
    change = await _create_change(db_session, change_type="Emergency")
    service = ChangeRiskService()
    result = await service.assess_risk(db_session, str(change.change_id))

    assert result.total_score >= 25
    assert result.risk_level in ("Medium", "High", "Critical")
    factor_names = [f.factor_name for f in result.factors]
    assert "change_type" in factor_names


@pytest.mark.asyncio
async def test_assess_risk_standard_change(db_session):
    """Standard変更 → 低スコア（営業時間内・テスト計画あり・説明十分）"""
    scheduled = datetime(2025, 1, 13, 10, 0, 0, tzinfo=UTC)  # 月曜10時
    change = await _create_change(
        db_session,
        change_type="Standard",
        scheduled_start_at=scheduled,
        description="これは詳細な変更説明です。50文字以上の説明が含まれています。詳細情報をここに記述します。",
        test_plan="十分なテスト計画",
    )
    service = ChangeRiskService()
    result = await service.assess_risk(db_session, str(change.change_id))

    assert result.total_score <= 25
    assert result.risk_level == "Low"


@pytest.mark.asyncio
async def test_score_timing_weekend(service):
    """週末 → timing スコア20"""
    weekend = datetime(2025, 1, 11, 14, 0, 0)  # 土曜日
    factor = service._score_change_timing(weekend)
    assert factor.score == 20
    assert factor.factor_name == "timing"


@pytest.mark.asyncio
async def test_score_timing_offhours(service):
    """夜間 → timing スコア15"""
    night = datetime(2025, 1, 13, 23, 0, 0)  # 月曜23時
    factor = service._score_change_timing(night)
    assert factor.score == 15
    assert factor.factor_name == "timing"


@pytest.mark.asyncio
async def test_score_timing_business_hours(service):
    """営業時間内 → timing スコア0"""
    business = datetime(2025, 1, 13, 10, 0, 0)  # 月曜10時
    factor = service._score_change_timing(business)
    assert factor.score == 0
    assert factor.factor_name == "timing"


@pytest.mark.asyncio
async def test_determine_risk_level(service):
    """スコア別リスクレベル判定"""
    assert service._determine_risk_level(0) == "Low"
    assert service._determine_risk_level(25) == "Low"
    assert service._determine_risk_level(26) == "Medium"
    assert service._determine_risk_level(50) == "Medium"
    assert service._determine_risk_level(51) == "High"
    assert service._determine_risk_level(75) == "High"
    assert service._determine_risk_level(76) == "Critical"
    assert service._determine_risk_level(100) == "Critical"


@pytest.mark.asyncio
async def test_assess_risk_updates_change_model(db_session):
    """リスク評価後にChangeモデルのrisk_score・risk_levelが更新される"""
    change = await _create_change(db_session, change_type="Emergency", risk_score=0, risk_level=None)
    original_score = change.risk_score

    service = ChangeRiskService()
    result = await service.assess_risk(db_session, str(change.change_id))

    await db_session.refresh(change)
    assert change.risk_score == result.total_score
    assert change.risk_level == result.risk_level
    assert change.risk_score != original_score or result.total_score == 0
