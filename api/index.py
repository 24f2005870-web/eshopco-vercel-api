```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import os
import math
from collections import defaultdict

app = FastAPI()

# Enable CORS for all origins, methods, and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Path to telemetry.json in the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TELEMETRY_FILE = os.path.join(BASE_DIR, "telemetry.json")


class TelemetryRequest(BaseModel):
    regions: List[str]
    threshold_ms: float


def load_telemetry():
    """Load telemetry records from telemetry.json."""
    try:
        with open(TELEMETRY_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Support either a JSON array or an object containing records
        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            for key in ("data", "records", "telemetry"):
                if isinstance(data.get(key), list):
                    return data[key]

        return []

    except (FileNotFoundError, json.JSONDecodeError):
        return []


def percentile_95(values):
    """Calculate the 95th percentile using linear interpolation."""
    if not values:
        return 0.0

    values = sorted(values)

    if len(values) == 1:
        return float(values[0])

    position = (len(values) - 1) * 0.95
    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return float(values[lower])

    fraction = position - lower
    return float(
        values[lower] * (1 - fraction)
        + values[upper] * fraction
    )


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.post("/")
@app.post("/api")
@app.post("/api/")
def analyze_telemetry(request: TelemetryRequest):
    records = load_telemetry()
    results = {}

    for region in request.regions:
        region_records = [
            record
            for record in records
            if isinstance(record, dict)
            and record.get("region") == region
        ]

        latencies = [
            float(record["latency_ms"])
            for record in region_records
            if record.get("latency_ms") is not None
        ]

        uptimes = [
            float(record["uptime_pct"])
            for record in region_records
            if record.get("uptime_pct") is not None
        ]

        results[region] = {
            "avg_latency": (
                sum(latencies) / len(latencies)
                if latencies else 0.0
            ),
            "p95_latency": percentile_95(latencies),
            "avg_uptime": (
                sum(uptimes) / len(uptimes)
                if uptimes else 0.0
            ),
            "breaches": sum(
                1 for latency in latencies
                if latency > request.threshold_ms
            ),
        }

    return results
```
