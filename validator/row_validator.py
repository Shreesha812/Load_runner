import logging

from parser.excel_test_definition_row import ExcelTestDefinitionRow

logger = logging.getLogger(__name__)

ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
BODY_METHODS = {"POST", "PUT", "PATCH"}


class RowValidator:

    def validate(self, row: ExcelTestDefinitionRow) -> list[str]:
        errors = []

        # URL
        if not row.url or str(row.url).strip() == "":
            errors.append("URL cannot be empty")

        # HTTP Method
        method = str(row.method).strip().upper() if row.method else ""
        if method not in ALLOWED_METHODS:
            errors.append(f"Invalid HTTP method: '{row.method}'. Allowed: {sorted(ALLOWED_METHODS)}")

        # Concurrency
        if row.concurrency is None:
            errors.append("Concurrency is required")
        else:
            try:
                val = int(float(row.concurrency))
                if val <= 0:
                    errors.append("Concurrency must be greater than 0")
            except (ValueError, TypeError):
                errors.append(f"Concurrency must be a number, got: '{row.concurrency}'")

        # Enable
        enabled_val = str(row.enabled).strip().lower() if row.enabled else ""
        if enabled_val not in {"enable", "disable"}:
            errors.append(f"Enable column must be 'Enable' or 'Disable', got: '{row.enabled}'")

        # Request Template — only required for body-bearing methods
        if method in BODY_METHODS:
            if not row.request_template or str(row.request_template).strip() == "":
                logger.warning("Request template is empty for %s %s", method, row.url)
                # Warn but don't block — an empty body may be intentional

        return errors
