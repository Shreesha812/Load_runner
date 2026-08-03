import logging
import time

import aiohttp

from models.http_response import (
    HttpResponse,
    ERROR_TYPE_NONE, ERROR_TYPE_TIMEOUT,
    ERROR_TYPE_CONNECTION, ERROR_TYPE_4XX,
    ERROR_TYPE_5XX, ERROR_TYPE_UNKNOWN,
)

logger = logging.getLogger(__name__)

DEFAULT_TOTAL_TIMEOUT   = 30
DEFAULT_CONNECT_TIMEOUT = 10
DEFAULT_POOL_SIZE       = 100


def _classify_status(status: int) -> str:
    """Return an error_type string for a completed HTTP response."""
    if 200 <= status < 400:
        return ERROR_TYPE_NONE
    if 400 <= status < 500:
        return ERROR_TYPE_4XX
    if 500 <= status < 600:
        return ERROR_TYPE_5XX
    return ERROR_TYPE_UNKNOWN


class HttpClient:
    """
    Async HTTP client backed by a shared aiohttp.ClientSession.
    Use as an async context manager:

        async with HttpClient(timeout=30, pool_size=50) as client:
            response = await client.send(job)
    """

    def __init__(
        self,
        timeout: int = DEFAULT_TOTAL_TIMEOUT,
        connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
        pool_size: int = DEFAULT_POOL_SIZE,
    ):
        self._timeout = aiohttp.ClientTimeout(total=timeout, connect=connect_timeout)
        self._connector = aiohttp.TCPConnector(
            limit=pool_size,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "HttpClient":
        self._session = aiohttp.ClientSession(
            connector=self._connector,
            timeout=self._timeout,
        )
        return self

    async def __aexit__(self, *args) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def send(self, job) -> HttpResponse:
        if self._session is None:
            raise RuntimeError("HttpClient must be used as an async context manager.")

        start = time.perf_counter()

        try:
            async with self._session.request(
                method=job.method,
                url=job.url,
                headers=job.headers,
                data=job.body or None,
            ) as response:
                body    = await response.text()
                latency = (time.perf_counter() - start) * 1000
                etype   = _classify_status(response.status)
                logger.debug("HTTP %s %s -> %s (%.1f ms)", job.method, job.url, response.status, latency)
                return HttpResponse(
                    status=response.status,
                    body=body,
                    latency=latency,
                    error_type=etype,
                )

        except aiohttp.ServerTimeoutError as e:
            latency = (time.perf_counter() - start) * 1000
            logger.warning("Timeout %s %s after %.1f ms", job.method, job.url, latency)
            return HttpResponse(status=None, body=str(e), latency=latency, error_type=ERROR_TYPE_TIMEOUT)

        except aiohttp.ClientConnectorError as e:
            latency = (time.perf_counter() - start) * 1000
            logger.warning("Connection error %s %s: %s", job.method, job.url, e)
            return HttpResponse(status=None, body=str(e), latency=latency, error_type=ERROR_TYPE_CONNECTION)

        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            logger.error("Unexpected error %s %s: %s", job.method, job.url, e)
            return HttpResponse(status=None, body=str(e), latency=latency, error_type=ERROR_TYPE_UNKNOWN)
