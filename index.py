import json
from pathlib import Path

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# The JSON file is bundled with the deployment.
DATA_PATH = Path(__file__).resolve().parent.parent / "telemetry.json"
with DATA_PATH.open("r", encoding="utf-8") as f:
    TELEMETRY = json.load(f)


class MetricsRequest(BaseModel):
    regions: list[str]
    threshold_ms: float = 180


@app.post("/")
def calculate_metrics(request: MetricsRequest):
    result = {}

    for region in request.regions:
        rows = [
            row for row in TELEMETRY
            if row.get("region", "").lower() == region.lower()
        ]

        if not rows:
            result[region] = {
                "avg_latency": None,
                "p95_latency": None,
                "avg_uptime": None,
                "breaches": 0,
            }
            continue

        latencies = [float(row["latency_ms"]) for row in rows]
        uptimes = [float(row["uptime_pct"]) for row in rows]

        result[region] = {
            "avg_latency": float(np.mean(latencies)),
            "p95_latency": float(np.percentile(latencies, 95)),
            "avg_uptime": float(np.mean(uptimes)),
            "breaches": sum(x > request.threshold_ms for x in latencies),
        }

    return result
