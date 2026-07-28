from dataclasses import dataclass
from parser.excel_test_definition_row import ExcelTestDefinitionRow


@dataclass
class WorkbookModel:
    sheet_name: str
    headers: list[str]
    rows: list[ExcelTestDefinitionRow]