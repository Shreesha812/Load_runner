from dataclasses import dataclass
from typing import Optional


@dataclass
class ExcelTestDefinitionRow:
    """
    Represents one raw row read from the Excel file.
    Values are kept exactly as read — not validated or converted.

    Column mapping (supports multiple header name variants):

        url               — target URL
        method            — HTTP method
        headers           — raw header lines  (key: value per line)
        request_template  — body template with <variable> placeholders
        variable_strategy — "sequential" or "random"
        variable_order    — comma-separated variable names defining order
        variable_values   — multi-value variables  e.g. "v1:{a,b}, v2:{x,y}"
        fixed_variables   — single-value variables e.g. "v1:abc, v2:123"
        concurrency       — number of concurrent workers
        response_structure — expected response keys (for assertion)
        enabled           — "Enable" / "Disable"
    """

    url: Optional[str]
    method: Optional[str]
    headers: Optional[str]
    request_template: Optional[str]
    variable_strategy: Optional[str]
    variable_order: Optional[str]
    variable_values: Optional[str]
    fixed_variables: Optional[str] = None   # single-value "variables" column
    concurrency: Optional[object] = None
    response_structure: Optional[str] = None
    enabled: Optional[str] = None
    ramp_up_seconds: Optional[object] = None  # gradual worker ramp-up duration
