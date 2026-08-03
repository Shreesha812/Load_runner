import logging

from models.configuration import Configuration
from mapper.test_definition_mapper import TestDefinitionMapper
from parser.workbook_model import WorkbookModel
from validator.row_validator import RowValidator

logger = logging.getLogger(__name__)


class ConfigurationFactory:

    def __init__(self):
        self.mapper = TestDefinitionMapper()
        self.validator = RowValidator()

    def build(self, workbook: WorkbookModel) -> Configuration:

        configuration = Configuration()

        for row in workbook.rows:

            errors = self.validator.validate(row)

            if errors:
                logger.warning("Skipping row due to validation errors: %s", errors)
                continue

            test_definition = self.mapper.map(row)

            configuration.add_test_definition(test_definition)

        return configuration