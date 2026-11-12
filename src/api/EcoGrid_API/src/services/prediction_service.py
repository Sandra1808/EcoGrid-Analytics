import logging
import os
from pathlib import Path
from typing import Any

import xgboost as xgb
import numpy as np
import pandas as pd
import requests

from src.config.settings import BASE_DIR

logger = logging.getLogger("EcoGrid.Prediction")

FEATURES = [
    "hour",
    "dayofweek",
    "month",
    "dayofyear",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "year_sin",
    "year_cos",
    "lag_24h",
    "lag_168h",
]


class DailyPredictionService:
    def __init__(self) -> None:
        self.api_base_url = os.getenv(
            "SPRING_API_BASE_URL",
            "http://127.0.0.1:8080",
        ).rstrip("/")
        self.api_key = os.getenv("SPRING_PREDICTIONS_API_KEY", "").strip()

        configured_path = Path(
            os.getenv(
                "PREDICTION_MODEL_PATH",
                r"models\modelo_xgboost_demanda.json",
            )
        ).expanduser()
        self.model_path = (
            configured_path
            if configured_path.is_absolute()
            else BASE_DIR / configured_path
        )
        self._model = None

    def _get_model(self):
     if self._model is None:
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"No se encuentra el modelo XGBoost: {self.model_path}"
            )

        self._model = xgb.XGBRegressor()
        self._model.load_model(str(self.model_path))
        
        return self._model

    def _get_model_id(self) -> int:
        raw_model_id = os.getenv("PREDICTION_MODEL_ID", "").strip()
        try:
            model_id = int(raw_model_id)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                "Configura PREDICTION_MODEL_ID con el ID existente en MODELOSML."
            ) from exc

        if model_id <= 0:
            raise RuntimeError("PREDICTION_MODEL_ID debe ser mayor que cero.")
        return model_id

    def predict_and_save(self) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError(
                "Falta SPRING_PREDICTIONS_API_KEY en el .env de EcoGrid_API."
            )

        now = pd.Timestamp.now(tz="UTC")
        params = {
            "ccaaId": 1,
            "desde": (now - pd.Timedelta(days=9)).isoformat(),
            "hasta": now.isoformat(),
        }

        history_response = requests.get(
            f"{self.api_base_url}/api/demanda/historica",
            params=params,
            timeout=30,
        )
        history_response.raise_for_status()

        rows = history_response.json()
        if not isinstance(rows, list):
            raise ValueError("Spring Boot no devolvió una lista de demanda histórica.")

        observations = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("La respuesta histórica contiene una fila no válida.")

            timestamp = pd.to_datetime(
                row.get("fechaHora"),
                utc=True,
                errors="coerce",
            )
            if pd.isna(timestamp):
                raise ValueError("La respuesta histórica contiene una fecha no válida.")

            raw_demand = row.get("demandaRealMw")
            if raw_demand is None:
                continue

            demand = pd.to_numeric(raw_demand, errors="coerce")
            if pd.isna(demand):
                continue

            demand_value = float(demand)
            if not np.isfinite(demand_value):
                raise ValueError("La demanda histórica contiene un valor no finito.")

            observations.append((timestamp, demand_value))

        if not observations:
            raise ValueError("No hay demanda real disponible para generar el pronóstico.")

        history = pd.Series(
            [value for _, value in observations],
            index=pd.DatetimeIndex([timestamp for timestamp, _ in observations]),
            dtype="float64",
        ).sort_index()
        history = history[~history.index.duplicated(keep="last")]

        last_observed_time = history.index.max()
        if last_observed_time < now - pd.Timedelta(hours=2):
            raise ValueError(
                f"La última demanda real es de {last_observed_time.isoformat()}; "
                "no se pronostica con datos de más de dos horas."
            )
        if last_observed_time != last_observed_time.floor("h"):
            raise ValueError("La última observación no está alineada a una hora UTC.")

        future_times = pd.date_range(
            start=last_observed_time + pd.Timedelta(hours=1),
            periods=24,
            freq="h",
        )
        lag24 = history.reindex(future_times - pd.Timedelta(hours=24))
        lag168 = history.reindex(future_times - pd.Timedelta(hours=168))

        missing = list(lag24[lag24.isna()].index) + list(lag168[lag168.isna()].index)
        if missing:
            raise ValueError(
                "Faltan valores reales necesarios para lag_24h o lag_168h; "
                f"no se generó el lote. Horas faltantes: {len(missing)}."
            )

        future = pd.DataFrame(index=future_times)
        future["hour"] = future.index.hour
        future["dayofweek"] = future.index.dayofweek
        future["month"] = future.index.month
        future["dayofyear"] = future.index.dayofyear
        future["hour_sin"] = np.sin(2 * np.pi * future["hour"] / 24)
        future["hour_cos"] = np.cos(2 * np.pi * future["hour"] / 24)
        future["dow_sin"] = np.sin(2 * np.pi * future["dayofweek"] / 7)
        future["dow_cos"] = np.cos(2 * np.pi * future["dayofweek"] / 7)
        future["year_sin"] = np.sin(2 * np.pi * future["dayofyear"] / 365.25)
        future["year_cos"] = np.cos(2 * np.pi * future["dayofyear"] / 365.25)
        future["lag_24h"] = lag24.to_numpy(dtype=float)
        future["lag_168h"] = lag168.to_numpy(dtype=float)

        predictions = np.asarray(
            self._get_model().predict(future[FEATURES]),
            dtype=float,
        ).reshape(-1)
        baseline = lag24.to_numpy(dtype=float)

        if len(predictions) != 24:
            raise ValueError(f"El modelo devolvió {len(predictions)} valores; se esperaban 24.")
        if not np.isfinite(predictions).all() or (predictions < 0).any():
            raise ValueError("El modelo devolvió predicciones negativas o no finitas.")
        if not np.isfinite(baseline).all() or (baseline < 0).any():
            raise ValueError("El baseline contiene valores no válidos.")

        payload = {
            "modeloId": self._get_model_id(),
            "predicciones": [
                {
                    "fechaHora": timestamp.isoformat().replace("+00:00", "Z"),
                    "demandaPredichaMw": float(predicted),
                    "demandaBaselineMw": float(base),
                }
                for timestamp, predicted, base in zip(
                    future_times,
                    predictions,
                    baseline,
                )
            ],
        }

        save_response = requests.post(
            f"{self.api_base_url}/api/predicciones/lote",
            headers={"X-API-Key": self.api_key},
            json=payload,
            timeout=30,
        )
        save_response.raise_for_status()

        result = save_response.json()
        if not isinstance(result, dict) or result.get("guardadas") != 24:
            raise RuntimeError(
                f"Spring Boot no confirmó el guardado de las 24 predicciones: {result}"
            )

        return {
            "guardadas": 24,
            "primera_hora_utc": payload["predicciones"][0]["fechaHora"],
            "ultima_hora_utc": payload["predicciones"][-1]["fechaHora"],
        }