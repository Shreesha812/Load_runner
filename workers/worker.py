import asyncio
import json
import logging
import uuid

from client.http_client import HttpClient
from execution.execution_job_factory import ExecutionJobFactory
from models.http_response import HttpResponse, ERROR_TYPE_UNKNOWN
from renderer.template_renderer import TemplateRenderer

logger = logging.getLogger(__name__)


class Worker:
    """
    Async worker that pulls combinations from a queue, renders the request
    template, dispatches the HTTP call, and records metrics.

    Accepts a shared HttpClient so the underlying aiohttp.ClientSession
    (and its connection pool) is reused across all workers in a test run.
    """

    def __init__(self, metrics, client: HttpClient):
        self.metrics = metrics
        self.renderer = TemplateRenderer()
        self.job_factory = ExecutionJobFactory()
        self.client = client

    async def run(
        self,
        queue: asyncio.Queue,
        test_definition,
    ) -> None:

        while True:
            combination = await queue.get()

            if combination is None:
                queue.task_done()
                break

            try:
                request_id = str(uuid.uuid4())[:12]

                rendered = self.renderer.render(
                    test_definition.request_template,
                    combination,
                )

                job = self.job_factory.build(test_definition, rendered, combination)
                response = await self.client.send(job)

                # Attach request identity so Metrics can build the lists
                response.request_id  = request_id
                response.combination = combination

                # Fix 1: Response structure validation now marks failures.
                # Previously this only logged a warning and the request was
                # counted as success regardless. Now a validation failure
                # sets error_type="validation_failed" and nulls the status
                # so Metrics.record() counts it as a failure.
                if test_definition.response_structure and response.body:
                    failed_rules = _validate_response_structure(
                        response.body,
                        test_definition.response_structure,
                    )
                    if failed_rules:
                        logger.warning(
                            "Validation failed for %s — rules not satisfied: %s",
                            request_id, failed_rules,
                        )
                        response.status     = None
                        response.error_type = "validation_failed"
                        response.validation_failures = failed_rules

                await self.metrics.record(response)

            except Exception as e:
                # Fix 5: worker exceptions now record error_type="unknown"
                # instead of the empty string default.
                logger.error("Worker error: %s", e)
                await self.metrics.record(
                    HttpResponse(
                        status=None,
                        body=str(e),
                        latency=0.0,
                        request_id=str(uuid.uuid4())[:12],
                        combination=combination if combination else {},
                        error_type=ERROR_TYPE_UNKNOWN,
                    )
                )
            finally:
                queue.task_done()


def _validate_response_structure(body: str, structure: str) -> list[str]:
    """
    Validates the response body against rules in the response_structure column.

    Supported rule formats (comma-separated):
        field:token              — field must exist in the JSON body
        field:status=success     — field value must equal "success"
        field:code~^\\d+$        — field value must match regex
        field:score>0            — field numeric value must be > number
        field:count>=10          — field numeric value must be >= number

    Dot-notation supported for nested fields: data.id, result.items.0

    Returns a list of failed rule strings. Empty list means all rules passed.
    """
    import re as _re

    failed: list[str] = []

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        logger.warning("Response body is not JSON — skipping structure validation.")
        return []

    rules = [r.strip() for r in structure.split(",") if r.strip()]

    for rule in rules:
        # Parse rule into field_path and optional operator+expected
        # Formats:  field:key,  field:key=val,  field:key~regex,  field:key>n,  field:key>=n
        match = _re.match(
            r'^([^:]+):([^=~><]+?)(?:(>=|<=|>|<|=|~)(.+))?$',
            rule.strip()
        )
        if not match:
            # Simple field-presence check: just "fieldname"
            field_path = rule.strip()
            operator   = None
            expected   = None
        else:
            _, field_path, operator, expected = match.groups()

        # Navigate dot-notation path
        parts = field_path.strip().split(".")
        node  = parsed
        found = True
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            elif isinstance(node, list):
                try:
                    node = node[int(part)]
                except (ValueError, IndexError):
                    found = False
                    break
            else:
                found = False
                break

        if not found:
            failed.append(f"missing:{field_path}")
            continue

        if operator is None:
            # Presence check only — passed
            continue

        # Value check
        actual = node
        if operator == "=":
            if str(actual) != str(expected):
                failed.append(f"{field_path}={expected} (got {actual!r})")
        elif operator == "~":
            if not _re.search(expected, str(actual)):
                failed.append(f"{field_path}~{expected} (got {actual!r})")
        elif operator in (">", "<", ">=", "<="):
            try:
                num_actual   = float(actual)
                num_expected = float(expected)
                ops = {">": num_actual > num_expected,  "<": num_actual < num_expected,
                       ">=": num_actual >= num_expected, "<=": num_actual <= num_expected}
                if not ops[operator]:
                    failed.append(f"{field_path}{operator}{expected} (got {actual!r})")
            except (TypeError, ValueError):
                failed.append(f"{field_path}{operator}{expected} (not numeric: {actual!r})")

    return failed
