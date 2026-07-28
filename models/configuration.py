from dataclasses import dataclass, field
from typing import List

from models.test_definition import TestDefinition


@dataclass
class Configuration:
    """
    Represents the entire Excel configuration.
    It contains all the test definitions found in the workbook.
    """

    test_definitions: List[TestDefinition] = field(default_factory=list)

    def add_test_definition(self, test_definition: TestDefinition) -> None:
        """
        Adds a test definition to the configuration.
        """
        self.test_definitions.append(test_definition)