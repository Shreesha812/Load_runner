import asyncio
import logging
from typing import Optional

from client.http_client import HttpClient
from workers.worker import Worker

logger = logging.getLogger(__name__)


class Scheduler:
    """
    Orchestrates a test run using an async producer/consumer pattern.

    cancel_event: optional asyncio.Event — set it externally to stop the run
    gracefully. The producer stops feeding the queue; workers drain and exit.
    """

    async def run(
        self,
        test_definition,
        combinations,
        metrics,
        http_timeout: int = 30,
        http_connect_timeout: int = 10,
        http_pool_size: int = 100,
        cancel_event: Optional[asyncio.Event] = None,
    ) -> None:
        from generator.combination_counter import CombinationCounter

        counter = CombinationCounter()
        total_combinations = counter.count(test_definition.variables)

        if test_definition.strategy.lower() == "random":
            limit = max(test_definition.concurrency, total_combinations)
        else:
            limit = total_combinations

        logger.info(
            "Starting run: %d worker(s), %d request(s), strategy=%s",
            test_definition.concurrency, limit, test_definition.strategy,
        )

        queue: asyncio.Queue = asyncio.Queue(maxsize=test_definition.concurrency * 2)

        async def producer() -> None:
            try:
                count = 0
                for combination in combinations:
                    # Respect cancellation — stop feeding the queue
                    if cancel_event and cancel_event.is_set():
                        logger.info("Cancellation requested — producer stopping early.")
                        break
                    if count >= limit:
                        break
                    await queue.put(combination)
                    count += 1
            except Exception as e:
                logger.error("Producer error: %s", e)
            finally:
                # Always send sentinels so workers can exit cleanly
                for _ in range(test_definition.concurrency):
                    await queue.put(None)

        async with HttpClient(
            timeout=http_timeout,
            connect_timeout=http_connect_timeout,
            pool_size=http_pool_size,
        ) as client:
            workers = [
                asyncio.create_task(
                    Worker(metrics, client).run(queue, test_definition)
                )
                for _ in range(test_definition.concurrency)
            ]

            producer_task = asyncio.create_task(producer())

            await queue.join()
            await asyncio.gather(*workers, producer_task)

        logger.info("Run complete.")
