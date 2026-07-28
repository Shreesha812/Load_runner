import asyncio
import logging
from typing import Optional

from client.http_client import HttpClient
from workers.worker import Worker

logger = logging.getLogger(__name__)


class RampController:
    """
    Tracks how many workers are currently active and handles gradual ramp-up.

    When ramp_up_seconds > 0, workers are added one at a time spaced evenly
    over the ramp period.  When ramp_up_seconds == 0, all workers start
    immediately (original behaviour).

    Thread/coroutine safe: active_workers is an int updated only by the
    single event-loop thread.
    """

    def __init__(self, total_workers: int, ramp_up_seconds: int):
        self.total_workers    = total_workers
        self.ramp_up_seconds  = ramp_up_seconds
        self.active_workers   = 0               # incremented as workers spin up
        self._worker_ready    = asyncio.Event() # signals next worker to start

    @property
    def interval(self) -> float:
        """Seconds between each worker being added during ramp-up."""
        if self.ramp_up_seconds <= 0 or self.total_workers <= 1:
            return 0.0
        return self.ramp_up_seconds / self.total_workers

    async def ramp(self) -> None:
        """
        Coroutine run alongside workers — releases one worker token at a time.
        If ramp_up_seconds == 0, releases all at once immediately.
        """
        interval = self.interval
        for _ in range(self.total_workers):
            self.active_workers += 1
            self._worker_ready.set()
            self._worker_ready.clear()
            if interval > 0:
                await asyncio.sleep(interval)

    async def wait_for_slot(self, worker_index: int) -> None:
        """
        Each worker calls this before starting its loop.
        Workers beyond the first wait until the ramp controller releases them.
        """
        if self.ramp_up_seconds <= 0:
            # No ramp — all start immediately
            self.active_workers += 1
            return
        # Wait until this worker's turn comes
        while self.active_workers <= worker_index:
            await self._worker_ready.wait()
            # Recheck in case of spurious wakes
            await asyncio.sleep(0)


class Scheduler:
    """
    Orchestrates a test run using an async producer/consumer pattern.

    cancel_event     — set externally to stop the run gracefully.
    ramp_controller  — exposed so runner.py can read active_workers for live metrics.
    """

    def __init__(self):
        self.ramp_controller: Optional[RampController] = None

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

        ramp_up = getattr(test_definition, "ramp_up_seconds", 0) or 0
        concurrency = test_definition.concurrency

        counter = CombinationCounter()
        total_combinations = counter.count(test_definition.variables)

        if test_definition.strategy.lower() == "random":
            limit = max(concurrency, total_combinations)
        else:
            limit = total_combinations

        logger.info(
            "Starting run: %d worker(s), %d request(s), strategy=%s, ramp_up=%ds",
            concurrency, limit, test_definition.strategy, ramp_up,
        )

        # Create and expose the ramp controller so the runner can read it
        self.ramp_controller = RampController(
            total_workers=concurrency,
            ramp_up_seconds=ramp_up,
        )

        queue: asyncio.Queue = asyncio.Queue(maxsize=concurrency * 2)

        async def producer() -> None:
            try:
                count = 0
                for combination in combinations:
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
                for _ in range(concurrency):
                    await queue.put(None)

        async with HttpClient(
            timeout=http_timeout,
            connect_timeout=http_connect_timeout,
            pool_size=http_pool_size,
        ) as client:

            if ramp_up > 0:
                # Ramp mode — each worker waits for its slot before starting
                async def ramped_worker(index: int) -> None:
                    await self.ramp_controller.wait_for_slot(index)
                    logger.info("Worker %d/%d started (ramp-up).", index + 1, concurrency)
                    await Worker(metrics, client).run(queue, test_definition)

                worker_tasks = [
                    asyncio.create_task(ramped_worker(i))
                    for i in range(concurrency)
                ]
                ramp_task = asyncio.create_task(self.ramp_controller.ramp())
            else:
                # Immediate mode — all workers start at once (original behaviour)
                self.ramp_controller.active_workers = concurrency
                worker_tasks = [
                    asyncio.create_task(
                        Worker(metrics, client).run(queue, test_definition)
                    )
                    for _ in range(concurrency)
                ]
                ramp_task = None

            producer_task = asyncio.create_task(producer())

            await queue.join()
            await asyncio.gather(*worker_tasks, producer_task)
            if ramp_task and not ramp_task.done():
                ramp_task.cancel()
                try:
                    await ramp_task
                except asyncio.CancelledError:
                    pass

        logger.info("Run complete.")
