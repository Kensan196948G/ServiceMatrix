"""予測的インシデント分析サービス"""

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class PredictiveAnalyticsService:
    """
    インシデント発生予測サービス。
    本番では Prophet を使用。フォールバックは線形回帰（numpy）。
    """

    def predict_weekly_incidents(
        self,
        historical_data: list[dict],
        forecast_days: int = 7,
    ) -> dict[str, Any]:
        """
        過去データから今後N日間のインシデント件数を予測。

        Args:
            historical_data: [{"date": "2026-01-01", "count": 5}, ...]
            forecast_days: 予測日数

        Returns:
            {"predictions": [{"date": "...", "predicted_count": N, "lower": N, "upper": N}],
            "model": "prophet"|"linear"}
        """
        if len(historical_data) < 3:
            return self._empty_forecast(forecast_days)

        try:
            return self._prophet_forecast(historical_data, forecast_days)
        except Exception:
            return self._linear_forecast(historical_data, forecast_days)

    def _empty_forecast(self, days: int) -> dict[str, Any]:
        today = datetime.now(UTC).date()
        predictions = []
        for i in range(1, days + 1):
            d = today + timedelta(days=i)
            predictions.append({"date": str(d), "predicted_count": 0, "lower": 0, "upper": 0})
        return {"predictions": predictions, "model": "insufficient_data"}

    def _linear_forecast(self, data: list[dict], forecast_days: int) -> dict[str, Any]:
        """シンプルな線形回帰で予測（numpy のみ使用）"""
        try:
            import numpy as np  # noqa: PLC0415

            counts = [d["count"] for d in data[-14:]]  # 直近14日
            x = np.arange(len(counts))
            y = np.array(counts, dtype=float)
            # 最小二乗法
            if len(x) > 1:
                slope = np.polyfit(x, y, 1)[0]
                last_count = float(y[-1])
            else:
                slope = 0.0
                last_count = float(y[0]) if len(y) > 0 else 0.0

            today = datetime.now(UTC).date()
            predictions = []
            for i in range(1, forecast_days + 1):
                d = today + timedelta(days=i)
                predicted = max(0, round(last_count + slope * i))
                predictions.append(
                    {
                        "date": str(d),
                        "predicted_count": predicted,
                        "lower": max(0, predicted - 2),
                        "upper": predicted + 2,
                    }
                )
            return {"predictions": predictions, "model": "linear"}
        except Exception as e:
            logger.error("linear_forecast_failed", error=str(e))
            return self._empty_forecast(forecast_days)

    def _prophet_forecast(self, data: list[dict], forecast_days: int) -> dict[str, Any]:
        """Prophet による予測（オプション依存）"""
        import pandas as pd  # noqa: PLC0415
        from prophet import Prophet  # noqa: PLC0415

        df = pd.DataFrame([{"ds": d["date"], "y": d["count"]} for d in data])
        model = Prophet(yearly_seasonality=False, weekly_seasonality=True, daily_seasonality=False)
        model.fit(df)
        future = model.make_future_dataframe(periods=forecast_days)
        forecast = model.predict(future)
        tail = forecast.tail(forecast_days)

        predictions = []
        for _, row in tail.iterrows():
            predictions.append(
                {
                    "date": str(row["ds"].date()),
                    "predicted_count": max(0, round(float(row["yhat"]))),
                    "lower": max(0, round(float(row["yhat_lower"]))),
                    "upper": max(0, round(float(row["yhat_upper"]))),
                }
            )
        return {"predictions": predictions, "model": "prophet"}


predictive_analytics_service = PredictiveAnalyticsService()
