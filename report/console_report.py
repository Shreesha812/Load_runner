import logging

from metrics.metrics import Metrics

logger = logging.getLogger(__name__)


class ConsoleReport:

    def print_report(self, metrics: Metrics) -> None:
        """Prints the execution summary to stdout."""
        min_lat = metrics.min_latency if metrics.total_requests > 0 else 0.0

        print("=================================")
        print("Execution Summary")
        print("=================================")
        print(f"Total Requests  : {metrics.total_requests}")
        print(f"Successful      : {metrics.successful_requests}")
        print(f"Failed          : {metrics.failed_requests}")
        print(f"Avg Latency     : {metrics.average_latency:.2f} ms")
        print(f"Min Latency     : {min_lat:.2f} ms")
        print(f"Max Latency     : {metrics.max_latency:.2f} ms")
        print(f"P50 Latency     : {metrics.p50:.2f} ms")
        print(f"P95 Latency     : {metrics.p95:.2f} ms")
        print(f"P99 Latency     : {metrics.p99:.2f} ms")
        print(f"RPS             : {metrics.requests_per_second:.2f}")
        print(f"Execution Time  : {metrics.execution_time:.2f} s")
        print("=================================")
