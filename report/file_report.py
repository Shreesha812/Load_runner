import csv
import json
import logging
import os
from pathlib import Path

from metrics.metrics import Metrics

logger = logging.getLogger(__name__)


class FileReport:
    """
    Writes the execution summary to a file.

    Supported formats are determined by the file extension:
        - .json  →  JSON
        - .csv   →  CSV
    """

    def write(self, metrics: Metrics, output_path: str, test_name: str = "") -> None:
        path = Path(output_path)
        ext = path.suffix.lower()

        os.makedirs(path.parent, exist_ok=True)

        if ext == ".json":
            self._write_json(metrics, path, test_name)
        elif ext == ".csv":
            self._write_csv(metrics, path, test_name)
        else:
            raise ValueError(
                f"Unsupported output format '{ext}'. Use .json or .csv."
            )

        logger.info("Report written to %s", path)

    # ------------------------------------------------------------------ #

    def _build_record(self, metrics: Metrics, test_name: str) -> dict:
        min_lat = metrics.min_latency if metrics.total_requests > 0 else 0.0
        return {
            "test_name": test_name,
            "total_requests": metrics.total_requests,
            "successful_requests": metrics.successful_requests,
            "failed_requests": metrics.failed_requests,
            "avg_latency_ms": round(metrics.average_latency, 3),
            "min_latency_ms": round(min_lat, 3),
            "max_latency_ms": round(metrics.max_latency, 3),
            "p50_latency_ms": round(metrics.p50, 3),
            "p95_latency_ms": round(metrics.p95, 3),
            "p99_latency_ms": round(metrics.p99, 3),
            "requests_per_second": round(metrics.requests_per_second, 3),
            "execution_time_s": round(metrics.execution_time, 3),
        }

    def _write_json(self, metrics: Metrics, path: Path, test_name: str) -> None:
        records: list[dict] = []

        # Append to existing file if it already has content
        if path.exists() and path.stat().st_size > 0:
            with open(path, "r", encoding="utf-8") as f:
                try:
                    records = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Existing JSON report is malformed — overwriting.")

        records.append(self._build_record(metrics, test_name))

        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

    def _write_csv(self, metrics: Metrics, path: Path, test_name: str) -> None:
        record = self._build_record(metrics, test_name)
        write_header = not path.exists() or path.stat().st_size == 0

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(record.keys()))
            if write_header:
                writer.writeheader()
            writer.writerow(record)
