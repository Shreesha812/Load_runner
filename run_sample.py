"""
Standalone runner for the sample test — bypasses CLI arg parsing.
Runs two tests against postman-echo.com and prints a full report.
"""
import asyncio
import logging
import sys

from factory.configuration_factory import ConfigurationFactory
from generator.combination_generator import CombinationGenerator
from metrics.metrics import Metrics
from parser.excel_parser import ExcelParser
from report.console_report import ConsoleReport
from report.file_report import FileReport
from scheduler.scheduler import Scheduler
from validator.configuration_validator import ConfigurationValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main():
    input_path = "input/sample_test.xlsx"
    output_path = "output/sample_results.json"

    logger.info("Parsing %s", input_path)
    parser = ExcelParser(input_path)
    workbook = parser.parse()

    factory = ConfigurationFactory()
    configuration = factory.build(workbook)

    errors = ConfigurationValidator().validate(configuration)
    if errors:
        for e in errors:
            logger.error(e)
        return

    enabled_tests = [td for td in configuration.test_definitions if td.enabled]
    logger.info("%d enabled test(s) found", len(enabled_tests))

    generator   = CombinationGenerator()
    scheduler   = Scheduler()
    console     = ConsoleReport()
    file_rep    = FileReport()

    for idx, test_def in enumerate(enabled_tests, 1):
        name = f"Test {idx}: {test_def.method} {test_def.url}"
        logger.info("─" * 60)
        logger.info("Running %s", name)
        logger.info("Concurrency=%d  Strategy=%s  Variables=%d",
                    test_def.concurrency, test_def.strategy, len(test_def.variables))
        logger.info("─" * 60)

        metrics = Metrics()
        await scheduler.run(
            test_def,
            generator.generate(test_def),
            metrics,
            http_timeout=20,
            http_connect_timeout=8,
            http_pool_size=20,
        )

        console.print_report(metrics)
        file_rep.write(metrics, output_path, test_name=name)
        logger.info("Results appended to %s", output_path)

    logger.info("All tests complete.")


if __name__ == "__main__":
    asyncio.run(main())
