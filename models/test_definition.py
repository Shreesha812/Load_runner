from dataclasses import dataclass, field
from typing import Dict, List, Optional

from models.variable import Variable


@dataclass
class TestDefinition:

    url: str

    method: str

    strategy: str

    headers: Dict[str, str] = field(default_factory=dict)

    request_template: str = ""

    variables: List[Variable] = field(default_factory=list)

    concurrency: int = 1

    enabled: bool = True

    response_structure: Optional[str] = None

    ramp_up_seconds: int = 0   # 0 = no ramp, all workers start together