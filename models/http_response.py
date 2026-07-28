from dataclasses import dataclass, field


@dataclass
class HttpResponse:

    status: int | None

    body: str

    latency: float

    request_id: str = ""        # unique ID assigned per request
    combination: dict = field(default_factory=dict)   # variable values used