from dataclasses import dataclass, field

# Error type constants — assigned by HttpClient based on exception type
ERROR_TYPE_NONE       = ""               # successful response
ERROR_TYPE_TIMEOUT    = "timeout"        # ServerTimeoutError / connect timeout
ERROR_TYPE_CONNECTION = "connection_error"  # DNS failure, refused, unreachable
ERROR_TYPE_4XX        = "4xx"            # client error status
ERROR_TYPE_5XX        = "5xx"            # server error status
ERROR_TYPE_UNKNOWN    = "unknown"        # anything else


@dataclass
class HttpResponse:

    status: int | None
    body: str
    latency: float

    request_id: str  = ""
    combination: dict = field(default_factory=dict)
    error_type: str   = ERROR_TYPE_NONE   # one of the constants above
