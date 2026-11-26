import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

API_ROOT = Path(__file__).resolve().parent.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from src.services.prediction_service import DailyPredictionService


class TestDailyPredictionService(unittest.TestCase):
    def test_demanda_historica_and_predicciones_lote_send_api_key_header(self) -> None:
        now = pd.Timestamp.now(tz="UTC").floor("h")
        timestamps = pd.date_range(now - pd.Timedelta(hours=220), now, freq="h")
        history_rows = [
            {
                "fechaHora": timestamp.isoformat().replace("+00:00", "Z"),
                "demandaRealMw": 30000.0 + float(index),
            }
            for index, timestamp in enumerate(timestamps)
        ]

        history_response = MagicMock()
        history_response.raise_for_status.return_value = None
        history_response.json.return_value = history_rows

        save_response = MagicMock()
        save_response.raise_for_status.return_value = None
        save_response.json.return_value = {"guardadas": 24}

        mock_model = MagicMock()
        mock_model.predict.return_value = np.full(24, 30000.0)

        env = {
            "SPRING_API_BASE_URL": "http://127.0.0.1:8080",
            "SPRING_PREDICTIONS_API_KEY": "test-api-key",
            "PREDICTION_MODEL_ID": "1",
        }

        with patch.dict(os.environ, env, clear=False), \
             patch("src.services.prediction_service.requests.get", return_value=history_response) as get_mock, \
             patch("src.services.prediction_service.requests.post", return_value=save_response) as post_mock, \
             patch.object(DailyPredictionService, "_get_model", return_value=mock_model):
            result = DailyPredictionService().predict_and_save()

        expected_headers = {"X-API-Key": "test-api-key"}
        get_headers = get_mock.call_args.kwargs["headers"]
        post_headers = post_mock.call_args.kwargs["headers"]

        self.assertEqual(get_headers, expected_headers)
        self.assertEqual(post_headers, expected_headers)
        self.assertEqual(result["guardadas"], 24)


if __name__ == "__main__":
    unittest.main()
