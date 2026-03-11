"""AI異常検知サービス - IsolationForest ベース"""
import numpy as np
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class AnomalyDetectionService:
    """IsolationForest ベースの異常検知サービス"""

    def __init__(self):
        self._model = None
        self._is_trained = False

    def _build_features(self, incidents_data: list[dict]) -> np.ndarray:
        """インシデントデータから特徴量を構築"""
        features = []
        for d in incidents_data:
            # 特徴量: 時間帯、優先度スコア、週の曜日
            hour = d.get("hour", 12)
            priority_score = {"P1": 4, "P2": 3, "P3": 2, "P4": 1}.get(d.get("priority", "P3"), 2)
            day_of_week = d.get("day_of_week", 0)
            features.append([hour, priority_score, day_of_week])
        return np.array(features) if features else np.zeros((0, 3))

    def train(self, incidents_data: list[dict]) -> bool:
        """IsolationForest モデルを学習"""
        try:
            from sklearn.ensemble import IsolationForest  # noqa: PLC0415

            features = self._build_features(incidents_data)
            if len(features) < 10:
                logger.warning("insufficient_training_data", count=len(features))
                return False
            self._model = IsolationForest(
                n_estimators=100,
                contamination=0.1,
                random_state=42,
            )
            self._model.fit(features)
            self._is_trained = True
            logger.info("anomaly_model_trained", samples=len(features))
            return True
        except Exception as e:
            logger.error("anomaly_training_failed", error=str(e))
            return False

    def predict_anomaly_score(self, incident_data: dict) -> float:
        """異常スコアを返す (0.0〜1.0, 高いほど異常)"""
        if not self._is_trained or self._model is None:
            return 0.0
        try:
            features = self._build_features([incident_data])
            if len(features) == 0:
                return 0.0
            # IsolationForest: -1=異常, 1=正常。score_samplesは負の値
            raw_score = self._model.score_samples(features)[0]
            # 正規化: score は通常 -0.5〜0.1 の範囲
            normalized = max(0.0, min(1.0, (-raw_score - 0.1) / 0.6))
            return round(float(normalized), 4)
        except Exception as e:
            logger.error("anomaly_prediction_failed", error=str(e))
            return 0.0

    def is_anomaly(self, incident_data: dict, threshold: float = 0.6) -> bool:
        """閾値を超えた場合に異常と判定"""
        return self.predict_anomaly_score(incident_data) >= threshold

    @property
    def is_trained(self) -> bool:
        """モデルが学習済みかどうか"""
        return self._is_trained


# グローバルインスタンス（アプリケーション起動時に学習）
anomaly_service = AnomalyDetectionService()
