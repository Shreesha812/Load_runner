import argparse
import asyncio
import logging
import os
import sys

from factory.configuration_factory import ConfigurationFactory
from generator.combination_generator import CombinationGenerator
from metrics.metrics import Metrics
from parser.excel_parser import ExcelParser
from report.console_report import ConsoleReport
from report.file_report import FileReport
from scheduler.scheduler import Scheduler
from validator.configuration_validator import ConfigurationValidator


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="WolkenLoadRunner — async HTTP load testing tool driven by Excel."
    )
    parser.add_argument(
        "--input", "-i",
        default=os.path.join("input", "WolkenLoadRunner_input.xlsx"),
        help="Path to the Excel input file (default: input/WolkenLoadRunner_input.xlsx).",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help=(
            "Optional path for the report output file. "
            "Extension determines format: .json or .csv."
        ),
    )
    parser.add_argument(
        "--log-level", "-l",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP request timeout in seconds (default: 30).",
    )
    parser.add_argument(
        "--connect-timeout",
        type=int,
        default=10,
        help="TCP connect timeout in seconds (default: 10).",
    )
    parser.add_argument(
        "--pool-size",
        type=int,
        default=100,
        help="Maximum number of simultaneous HTTP connections (default: 100).",
    )
    return parser


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


async def main() -> None:
    args = build_arg_parser().parse_args()
    configure_logging(args.log_level)

    logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------ #
    # 1. Parse input file                                                  #
    # ------------------------------------------------------------------ #
    if not os.path.exists(args.input):
        logger.error("Excel file not found: %s", args.input)
        sys.exit(1)

    logger.info("Parsing Excel file: %s", args.input)
    parser = ExcelParser(args.input)
    workbook = parser.parse()

    # ------------------------------------------------------------------ #
    # 2. Build and validate configuration                                  #
    # ------------------------------------------------------------------ #
    logger.info("Building configuration...")
    factory = ConfigurationFactory()
    configuration = factory.build(workbook)

    logger.info("Validating configuration...")
    validator = ConfigurationValidator()
    errors = validator.validate(configuration)

    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error("  - %s", error)
        sys.exit(1)

    enabled_tests = [td for td in configuration.test_definitions if td.enabled]
    logger.info("Found %d enabled test definition(s).", len(enabled_tests))

    # ------------------------------------------------------------------ #
    # 3. Run each enabled test definition                                  #
    # ------------------------------------------------------------------ #
    generator = CombinationGenerator()
    scheduler = Scheduler()
    console_reporter = ConsoleReport()
    file_reporter = FileReport() if args.output else None

    for idx, test_def in enumerate(enabled_tests, 1):
        test_name = f"Test {idx}: {test_def.method} {test_def.url}"

        logger.info("=================================")
        logger.info("Executing %s", test_name)
        logger.info(
            "Concurrency: %d | Strategy: %s",
            test_def.concurrency, test_def.strategy,
        )
        logger.info("=================================")

        combinations = generator.generate(test_def)
        metrics = Metrics()

        await scheduler.run(
            test_def,
            combinations,
            metrics,
            http_timeout=args.timeout,
            http_connect_timeout=args.connect_timeout,
            http_pool_size=args.pool_size,
        )

        console_reporter.print_report(metrics)

        if file_reporter and args.output:
            file_reporter.write(metrics, args.output, test_name=test_name)


if __name__ == "__main__":
    asyncio.run(main())
