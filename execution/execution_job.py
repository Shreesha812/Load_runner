from dataclasses import dataclass, field


@dataclass
class ExecutionJob:

    url: str

    method: str

    headers: dict[str, str] = field(default_factory=dict)

    body: str = ""