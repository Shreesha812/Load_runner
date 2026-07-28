import asyncio
import json
import logging
import uuid

from client.http_client import HttpClient
from execution.execution_job_factory import ExecutionJobFactory
from models.http_response import HttpResponse
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

                # Optional response structure validation
                if test_definition.response_structure and response.body:
                    _validate_response_structure(
                        response.body,
                        test_definition.response_structure,
                    )

                await self.metrics.record(response)

            except Exception as e:
                logger.error("Worker error: %s", e)
                await self.metrics.record(
                    HttpResponse(
                        status=None,
                        body=str(e),
                        latency=0.0,
                        request_id=str(uuid.uuid4())[:12],
                        combination=combination if combination else {},
                    )
                )
            finally:
                queue.task_done()


def _validate_response_structure(body: str, structure: str) -> None:
    """
    Validates that each key listed in the response_structure column
    is present in the JSON response body.

    structure format: comma-separated key names, e.g. "id, name, status"
    Keys may use dot-notation for nested fields, e.g. "data.id"
    """
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        logger.warning("Response body is not JSON — skipping structure validation.")
        return

    expected_keys = [k.strip() for k in structure.split(",") if k.strip()]

    for key_path in expected_keys:
        parts = key_path.split(".")
        node = parsed
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                logger.warning(
                    "Response structure mismatch: expected key '%s' not found in response.",
                    key_path,
                )
                break
            node = node[part]
