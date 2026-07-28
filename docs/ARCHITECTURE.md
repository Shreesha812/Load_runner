# WolkenLoadRunner — Architecture & Implementation Guide

> A complete reference for the design, components, data flow, and runtime
> behaviour of WolkenLoadRunner — an async HTTP load testing tool driven
> by Excel configuration.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Directory Structure](#3-directory-structure)
4. [Architecture Overview](#4-architecture-overview)
5. [Data Flow — End to End](#5-data-flow--end-to-end)
6. [Module Reference](#6-module-reference)
7. [Excel Input Format](#7-excel-input-format)
8. [Concurrency Model](#8-concurrency-model)
9. [Variable System](#9-variable-system)
10. [Metrics & Percentiles](#10-metrics--percentiles)
11. [CLI Reference](#11-cli-reference)
12. [Output Formats](#12-output-formats)
13. [Design Decisions & Trade-offs](#13-design-decisions--trade-offs)
14. [Frontend UI — Planned Spec](#14-frontend-ui--planned-spec)

---

## 1. Project Overview

WolkenLoadRunner is a Python-based async HTTP load testing tool.
You define test cases in an Excel spreadsheet — URLs, methods, headers,
request templates, variables, concurrency — and the tool reads that file,
generates all request combinations, fires them concurrently using async
workers, and produces a full performance report.

**Core capabilities:**
- Excel-driven test configuration (no code changes needed to add tests)
- Variable substitution in request bodies using `<variable>` placeholders
- Two combination strategies: **sequential** (every permutation) and
  **random** (random sampling)
- Configurable concurrency per test definition (N async workers)
- Full latency metrics: min, max, avg, P50, P95, P99
- Output to console, JSON file, or CSV file
- CLI flags for input path, output path, timeouts, pool size, log level

---

## 2. Technology Stack

| Component       | Library          | Version | Why                                              |
|-----------------|------------------|---------|--------------------------------------------------|
| Async runtime   | Python `asyncio` | stdlib  | Cooperative concurrency — no GIL issues          |
| HTTP client     | `aiohttp`        | 3.14.2  | Non-blocking HTTP with persistent connection pool |
| Excel parsing   | `openpyxl`       | 3.1.5   | Read `.xlsx` without Excel installed             |
| CLI             | `argparse`       | stdlib  | Standard Python CLI argument parsing             |
| Logging         | `logging`        | stdlib  | Structured, levelled log output                  |
| Data models     | `dataclasses`    | stdlib  | Typed value objects with no boilerplate          |

---

## 3. Directory Structure

```
Load_runner/
├── main.py                           ← Entry point, CLI, orchestration
│
├── parser/
│   ├── excel_parser.py               ← Reads Excel → WorkbookModel
│   ├── excel_test_definition_row.py  ← Raw row dataclass (no processing)
│   ├── workbook_model.py             ← Holds sheet name + all rows
│   ├── variable_value_parser.py      ← Parses "var:{a,b,c}" syntax
│   └── variable_order_parser.py      ← Parses "var1, var2" order lists
│
├── validator/
│   ├── row_validator.py              ← Validates individual Excel rows
│   └── configuration_validator.py   ← Validates the whole Configuration
│
├── factory/
│   └── configuration_factory.py     ← Validates + maps rows → Configuration
│
├── mapper/
│   └── test_definition_mapper.py    ← ExcelTestDefinitionRow → TestDefinition
│
├── models/
│   ├── configuration.py             ← List of TestDefinitions
│   ├── test_definition.py           ← One test: URL, method, vars, concurrency…
│   ├── variable.py                  ← name + list of values
│   └── http_response.py             ← status, body, latency
│
├── execution/
│   ├── execution_job.py             ← Ready-to-send job: url/method/headers/body
│   └── execution_job_factory.py     ← Builds ExecutionJob from TestDefinition
│
├── generator/
│   ├── combination_generator.py     ← Routes to sequential or random strategy
│   ├── sequential_strategy.py       ← Cartesian product generator (finite)
│   ├── random_strategy.py           ← Infinite random-sampling generator
│   └── combination_counter.py       ← Product of all variable value lengths
│
├── renderer/
│   └── template_renderer.py         ← Substitutes <var> in body template
│
├── scheduler/
│   └── scheduler.py                 ← Producer/consumer orchestrator
│
├── workers/
│   └── worker.py                    ← render → build job → send → record
│
├── client/
│   └── http_client.py               ← Shared aiohttp session + connection pool
│
├── metrics/
│   └── metrics.py                   ← Latency collection + percentile calc
│
├── report/
│   ├── console_report.py            ← Prints summary table to stdout
│   └── file_report.py               ← Writes JSON or CSV report
│
├── input/
│   └── WolkenLoadRunner_input.xlsx  ← Default test configuration file
│
├── output/                          ← Report files written here
├── requirements.txt
└── docs/
    └── ARCHITECTURE.md              ← This file
```

---

## 4. Architecture Overview

The system is a linear pipeline with clear separation of concerns:

```
Excel File
    │
    ▼
[ExcelParser]            reads rows by header name (not column index)
    │ WorkbookModel
    ▼
[ConfigurationFactory]   validates each row, maps valid rows → TestDefinitions
    │ Configuration
    ▼
[ConfigurationValidator] checks at least one enabled test exists
    │
    ▼  (for each enabled TestDefinition)
[CombinationGenerator]   produces a lazy stream of variable combinations
    │ generator / iterator
    ▼
[Scheduler]              opens shared HttpClient, spawns producer + N workers
    │
    ├── [Producer coroutine]   feeds combinations into bounded asyncio.Queue
    │
    └── [Worker × N]           pulls from queue, renders, sends, records
            │
            ├── [TemplateRenderer]      substitutes <var> placeholders
            ├── [ExecutionJobFactory]   assembles ExecutionJob
            ├── [HttpClient.send()]     async HTTP via shared aiohttp session
            └── [Metrics.record()]      async-safe latency + status tracking
                        │
                        ▼
                [ConsoleReport]   prints to stdout
                [FileReport]      writes JSON / CSV
```

Every stage produces a typed value object consumed by the next stage.
No global state is used anywhere in the execution path.

---

## 5. Data Flow — End to End

### Step 1 — Parse

`ExcelParser.parse()` opens the `.xlsx` file with `openpyxl` and reads
the first row as headers. It builds an `index → field_name` mapping via
`COLUMN_MAP` — a dict that maps all known header name variants
(case-insensitive) to canonical internal field names. Column order in
the Excel file does not matter; multiple naming conventions are supported.

Each data row becomes an `ExcelTestDefinitionRow` dataclass — all fields
remain raw strings or `None`. No conversion or validation happens here.

### Step 2 — Validate & Map

`ConfigurationFactory.build()` loops over every raw row:

1. **`RowValidator.validate(row)`** — checks URL is present, method is
   a recognised HTTP verb, concurrency is a positive number, and the
   Enable column is `"Enable"` or `"Disable"`. Invalid rows are logged
   and skipped; they do not abort the run.

2. **`TestDefinitionMapper.map(row)`** — converts the raw row into a
   `TestDefinition`:
   - Multi-line headers string → `dict[str, str]`
   - Strategy string → `"sequential"` or `"random"` (handles legacy
     `"random/sequential"` format)
   - `variable_values` column (multi-value syntax) → `list[Variable]`
   - `fixed_variables` column (single-value syntax) → merged in; fixed
     values override multi-value entries on name collision
   - `variable_order` column → reorders the variable list if it contains
     real variable names (not a strategy keyword)
   - Concurrency → `int` (handles float strings like `"100.0"`)
   - Enabled → `bool`

### Step 3 — Validate Configuration

`ConfigurationValidator.validate()` checks the assembled `Configuration`
has at least one valid test definition and at least one that is enabled.

### Step 4 — Generate Combinations

`CombinationGenerator.generate()` returns a Python **generator** (lazy
iterator — nothing is pre-computed in memory):

- **Sequential**: `SequentialStrategy` uses `itertools.product` to yield
  every combination of variable values. For `query:{a,b,c}` ×
  `user_id:{1,2,3}` that is 9 combinations total.
- **Random**: `RandomStrategy` yields an infinite stream of random
  combinations. The scheduler imposes a hard cap via `CombinationCounter`.

### Step 5 — Schedule & Execute

`Scheduler.run()`:

1. Counts total combinations via `CombinationCounter`
2. Sets the request limit (random: `max(concurrency, total_combinations)`)
3. Opens a single `HttpClient` as an async context manager — one
   `aiohttp.ClientSession` backed by a `TCPConnector` with a configurable
   connection pool
4. Creates a bounded `asyncio.Queue(maxsize = concurrency × 2)`
5. Spawns a **producer coroutine** that feeds combinations into the queue,
   then pushes `N` sentinel `None` values to signal workers to stop
6. Spawns **N worker tasks** (one per concurrent slot)
7. Awaits `queue.join()` then `asyncio.gather()` for clean teardown
8. `HttpClient.__aexit__` closes the session and connection pool

### Step 6 — Worker Loop

Each `Worker.run()` loop per item:

1. `await queue.get()` — cooperative yield
2. Sentinel `None` → `queue.task_done()` then exit
3. `renderer.render()` — replace `<variable>` tokens in body template
4. `job_factory.build()` — assemble `ExecutionJob`
5. `await client.send(job)` — HTTP call, latency measured with
   `time.perf_counter()`
6. `_validate_response_structure()` — if `response_structure` is set,
   assert expected JSON keys are present (dot-notation supported)
7. `await metrics.record(response)` — update counters under asyncio.Lock
8. `queue.task_done()` in `finally` — always called, prevents deadlock

Errors are caught, logged, and recorded as failed requests so one bad
response never crashes a worker or stalls the queue.

### Step 7 — Report

After `scheduler.run()` returns:
- `ConsoleReport.print_report()` prints the summary table
- `FileReport.write()` appends the result to JSON or CSV (if `--output`
  was supplied)

---

## 6. Module Reference

### 6.1 Entry Point — `main.py`

Responsibilities: CLI parsing, logging setup, top-level orchestration.

- `build_arg_parser()` — defines all CLI flags (see §11)
- `configure_logging(level)` — `basicConfig` with timestamp + level +
  module name
- `main()` — async function that runs the full pipeline sequentially
  across all enabled test definitions

### 6.2 Parser Layer

**`ExcelParser`**
- Maps header names to fields via `COLUMN_MAP` (case-insensitive aliases)
- Key aliases: `"HTTP Method"` → `method`, `"variable list Order"` →
  `variable_strategy`, `"List Of values"` → `variable_values`,
  `"variables"` → `fixed_variables`, `"Total concurrent request"` →
  `concurrency`, `"Enable"` → `enabled`
- Skips entirely blank rows
- Returns `WorkbookModel(sheet_name, headers, rows)`

**`VariableValueParser`** — regex-based parser for:
```
variable1:{hello world, how are you}, variable2:{101,102}, variable3:fixed
```
Pattern: `(\w+)\s*:\s*(?:\{([^}]*)\}|([^,\s]+))`
Handles both braced multi-value and unbraced single-value forms.

**`VariableOrderParser`** — splits `"var1, var2, var3"` → `["var1","var2","var3"]`

### 6.3 Validation Layer

**`RowValidator`**
- URL: non-empty
- Method: one of `GET POST PUT DELETE PATCH HEAD OPTIONS`
- Concurrency: positive number (handles `"100.0"` float strings)
- Enable: `"Enable"` or `"Disable"`
- Request template: warns but does not fail if empty for POST/PUT/PATCH

**`ConfigurationValidator`**
- At least one `TestDefinition` must exist
- At least one must be `enabled=True`

### 6.4 Factory & Mapper

**`ConfigurationFactory`** — the assembly point that combines validation
and mapping. Invalid rows are skipped with a log message.

**`TestDefinitionMapper`** — most complex mapping step:
- Merges `variable_values` (multi-value) + `fixed_variables` (single-value)
- Fixed values override multi-value entries on name collision
- Reorders variables list if `variable_order` contains real names
- Normalises the `"random/sequential"` legacy strategy string

### 6.5 Models

All models are `@dataclass` — typed value objects, no business logic.

| Model | Key Fields |
|-------|-----------|
| `Configuration` | `test_definitions: List[TestDefinition]` |
| `TestDefinition` | url, method, strategy, headers, request_template, variables, concurrency, enabled, response_structure |
| `Variable` | name: str, values: list[str] |
| `HttpResponse` | status: int\|None, body: str, latency: float |
| `ExecutionJob` | url, method, headers, body |

### 6.6 Generator Layer

**`SequentialStrategy`** — `itertools.product` over all variable value lists:
```
[query:[a,b], user_id:[1,2]]  →  4 combinations
```

**`RandomStrategy`** — infinite `while True` loop, `random.choice` per variable.
Scheduler caps via `CombinationCounter`.

**`CombinationCounter`** — product of all value-list lengths:
```
[query:{a,b,c}, user_id:{1,2}]  →  3 × 2 = 6
```

### 6.7 Renderer

**`TemplateRenderer.render(template, variables, validate_json=False)`**

Substitutes `<variable_name>` tokens, then normalises `""` → `"`.
`validate_json` is `False` by default — supports any content type.
Pass `True` to enforce valid JSON output (raises `ValueError` on failure).

### 6.8 Scheduler

Core concurrency engine — producer/consumer pattern:

```
Producer ──puts──► asyncio.Queue(maxsize=concurrency×2) ──gets──► Worker × N
```

- **Bounded queue**: back-pressure keeps memory flat for large combination sets
- **Sentinel pattern**: `N` × `None` signals workers to exit cleanly
- **Single shared HttpClient**: one connection pool for the whole test run
- **Graceful teardown**: `queue.join()` then `asyncio.gather()`

### 6.9 Worker

Hot path — executes for every single request.
Error handling wraps the full render→send→record cycle so one failure
never stalls the queue (`queue.task_done()` always runs in `finally`).

### 6.10 HTTP Client

```python
async with HttpClient(timeout=30, connect_timeout=10, pool_size=100) as client:
    response = await client.send(job)
```

- `TCPConnector(limit=pool_size, ttl_dns_cache=300)` — persistent pool, DNS cache
- `ClientTimeout(total=..., connect=...)` — both TCP and total deadlines
- Specific handlers: `ClientConnectorError`, `ServerTimeoutError`, catch-all
- All errors return `HttpResponse(status=None)` instead of raising

### 6.11 Metrics

```python
async with self._lock:          # asyncio.Lock — forward-compatible
    self._latencies.append(response.latency)
    ...
```

Computed properties: `average_latency`, `requests_per_second`,
`execution_time`, `p50`, `p95`, `p99`.

Success = `200 ≤ status < 400`. Network errors (`status=None`) = failure.

### 6.12 Reports

**`ConsoleReport`** — fixed-width summary table with all 11 metrics.

**`FileReport`**:
- `.json` — appends to a JSON array; reads + rewrites the file each time
- `.csv` — appends a row; writes header only on first write
- Creates output directory automatically

---

## 7. Excel Input Format

The parser recognises these column headers (case-insensitive, any order):

| Accepted header variants | Internal field | Description |
|--------------------------|---------------|-------------|
| `URL` | `url` | Target endpoint URL |
| `HTTP Method`, `method` | `method` | GET / POST / PUT / DELETE / PATCH / HEAD / OPTIONS |
| `Headers` | `headers` | One `Key: Value` per line |
| `Request message Template`, `Request Template` | `request_template` | Body with `<variable>` placeholders |
| `variable list Order`, `Variable Strategy` | `variable_strategy` | `sequential` or `random` |
| `variable order` | `variable_order` | Comma-separated variable names for iteration order |
| `List Of values`, `Variable Values` | `variable_values` | Multi-value: `v1:{a,b,c}, v2:{x,y}` |
| `variables` | `fixed_variables` | Single-value: `v1:abc, v2:123` |
| `Total concurrent request`, `concurrency` | `concurrency` | Number of parallel workers |
| `Response Structure` | `response_structure` | Comma-separated JSON keys to assert in response |
| `Enable`, `enabled` | `enabled` | `Enable` or `Disable` |

### Variable syntax examples

**Multi-value (braced):**
```
query:{hello world, how are you, what is AI}, user_id:{101, 102, 103}
```

**Single-value (unbraced):**
```
env:staging, version:v2
```

Both columns can coexist in the same row — `List Of values` holds
multi-value variables and `variables` holds fixed/single-value ones.
The mapper merges them with fixed values taking precedence on collision.

---

## 8. Concurrency Model

WolkenLoadRunner uses Python's `asyncio` — **cooperative, single-threaded
concurrency**. No threads or processes are used.

```
Event Loop (single thread)
  │
  ├── producer coroutine   awaits queue.put()
  ├── worker-1 coroutine   awaits queue.get()  →  awaits client.send()
  ├── worker-2 coroutine   awaits queue.get()  →  awaits client.send()
  └── worker-N coroutine   awaits queue.get()  →  awaits client.send()
```

Every `await` is a yield point where the event loop can switch to another
coroutine. Since the bottleneck is network I/O — while one worker waits
for an HTTP response, all others continue executing — `asyncio` is the
ideal fit. The GIL is not a concern because virtually all time is spent
waiting on I/O, not executing Python bytecode.

**Queue sizing**: `maxsize = concurrency × 2` means the producer stays
at most 2 batches ahead of the workers. This is intentional back-pressure —
RAM stays flat even for tests with millions of combinations.

**Why not `multiprocessing`?**
CPU utilisation during an HTTP load test is negligible. Adding processes
would add serialisation overhead and inter-process coordination with no
throughput benefit.

---

## 9. Variable System

Variables are the "load" dimension of a test. Multiple values per variable
automatically generate all the request variants to test.

### Sequential strategy

Produces the full Cartesian product of all variable values.
Deterministic and exhaustive.

```
query: [a, b]   ×   user_id: [1, 2]
→ {query:a, user_id:1}
→ {query:a, user_id:2}
→ {query:b, user_id:1}
→ {query:b, user_id:2}
Total = 2 × 2 = 4 requests
```

### Random strategy

Picks one value per variable at random on each iteration. The generator
is infinite — the scheduler caps it at
`max(concurrency, total_combinations)` requests. Useful for
non-exhaustive load tests that need a representative random sample.

### Variable ordering

When `variable_order` contains a comma-separated list of real variable
names (not a strategy keyword), the variable list is reordered before the
Cartesian product is computed. This controls which variable "rotates
fastest" in the sequential output.

---

## 10. Metrics & Percentiles

### What is collected

Every HTTP response (including errors) contributes to:
- `latency` — time from first byte sent to full response body received,
  in milliseconds, measured with `time.perf_counter()`
- `status` — HTTP status code, or `None` for network errors / timeouts

### Percentile calculation

```python
sorted_lats = sorted(self._latencies)
idx = max(0, int(len(sorted_lats) * p / 100) - 1)
return sorted_lats[min(idx, len(sorted_lats) - 1)]
```

| Metric | Meaning |
|--------|---------|
| **P50** | Median — half of requests finished faster than this |
| **P95** | 95% of requests finished faster; the "slow tail" |
| **P99** | Worst 1%; what the slowest users experience |

P95 and P99 are more meaningful than average for API performance because
averages hide tail latency that real users feel.

---

## 11. CLI Reference

```
python main.py [OPTIONS]

  --input,  -i  PATH    Excel input file
                        (default: input/WolkenLoadRunner_input.xlsx)

  --output, -o  PATH    Report output file — .json or .csv. Optional.

  --log-level, -l       DEBUG | INFO | WARNING | ERROR
                        (default: INFO)

  --timeout     INT     Total HTTP request timeout in seconds
                        (default: 30)

  --connect-timeout INT TCP connect timeout in seconds
                        (default: 10)

  --pool-size   INT     Max simultaneous HTTP connections
                        (default: 100)
```

**Examples:**
```bash
# Run with defaults
python main.py

# Custom input, save JSON report
python main.py --input input/my_tests.xlsx --output output/results.json

# CSV report, verbose logging, tight timeouts
python main.py -i input/my_tests.xlsx -o output/results.csv \
               -l DEBUG --timeout 10 --connect-timeout 3 --pool-size 50
```

---

## 12. Output Formats

### Console (always printed after each test)

```
=================================
Execution Summary
=================================
Total Requests  : 9
Successful      : 9
Failed          : 0
Avg Latency     : 323.42 ms
Min Latency     : 244.98 ms
Max Latency     : 425.19 ms
P50 Latency     : 313.95 ms
P95 Latency     : 393.61 ms
P99 Latency     : 393.61 ms
RPS             : 8.70
Execution Time  : 1.03 s
=================================
```

### JSON (`--output results.json`)

Array of result objects, one per test definition. Appends across runs:

```json
[
  {
    "test_name": "Test 1: POST https://api.example.com/endpoint",
    "total_requests": 9,
    "successful_requests": 9,
    "failed_requests": 0,
    "avg_latency_ms": 323.418,
    "min_latency_ms": 244.984,
    "max_latency_ms": 425.186,
    "p50_latency_ms": 313.951,
    "p95_latency_ms": 393.607,
    "p99_latency_ms": 393.607,
    "requests_per_second": 8.69,
    "execution_time_s": 1.036
  }
]
```

### CSV (`--output results.csv`)

Same fields, one row per test definition.
Header written once; subsequent runs append rows.
Easily opened in Excel or imported into dashboards.

---

## 13. Design Decisions & Trade-offs

| Decision | Why | Trade-off |
|----------|-----|-----------|
| Excel input | Non-technical users define tests without writing code | Harder to version-control than YAML/JSON; column renames can break parsing |
| `asyncio` over threads | Zero OS context-switch overhead; perfect fit for I/O-bound HTTP testing | No true parallelism — CPU-bound work won't benefit (not relevant here) |
| Single shared `aiohttp.ClientSession` | Reuses TCP connections; skips repeated DNS + TLS handshake per request | Session must be explicitly closed; failure leaks file descriptors |
| Bounded queue (`maxsize = concurrency×2`) | Constant memory regardless of combination count | Producer may block on `queue.put()` if workers are slow — intentional back-pressure |
| Infinite random generator capped externally | Generator stays simple; no awareness of execution limit | Requires `CombinationCounter` to be called separately to determine the cap |
| Opt-in JSON validation in renderer | Renderer works with any content type: JSON, XML, plain text, form-encoded | JSON errors are not caught at render time unless `validate_json=True` |
| Append-mode file reports | Multiple test definitions in one run all go into one file | Stale entries from previous runs accumulate — delete the file before a clean run |
| `asyncio.Lock` on `Metrics.record()` | Forward-compatible if workers move to `ThreadPoolExecutor` | Tiny lock acquire/release overhead per request — negligible at real concurrency |
| Header-name column mapping | Excel column order does not matter; multiple naming conventions supported | COLUMN_MAP must be kept up to date when new header variants are added |

---

## 14. Frontend UI — Planned Spec

A web-based UI is planned to make WolkenLoadRunner accessible without
a terminal. This section documents the intended scope.

### Goals

- Upload or configure an Excel test file through a browser
- Visualise test progress in real time (request count, success/failure
  rate, live RPS counter)
- Display post-run metrics with charts (latency histogram, P50/P95/P99)
- Allow editing test definitions without touching the Excel file directly
- Download results as JSON or CSV

### Proposed Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| Backend API | FastAPI (Python) | Same language as runner; async-native; auto-generates OpenAPI docs |
| Real-time push | FastAPI WebSocket | Push live metrics from running workers to browser without polling |
| Frontend | React + TypeScript | Component model; wide chart library ecosystem |
| Charts | Recharts | Easy latency histograms and time-series; React-native |
| Styling | Tailwind CSS | Utility-first; fast to build clean dashboards |
| File upload | FastAPI `UploadFile` | Receives `.xlsx`, saves to `input/`, triggers run |

### Planned API Surface

```
POST  /api/run                       start a test run (xlsx file + config)
GET   /api/run/{run_id}              run status + final metrics
GET   /api/runs                      list all past runs
WS    /api/run/{run_id}/live         real-time metrics stream
GET   /api/results/{run_id}/json     download JSON report
GET   /api/results/{run_id}/csv      download CSV report
```

### UI Screens

1. **Upload & Configure** — drag-drop Excel file, override concurrency /
   timeout / pool-size per run
2. **Live Dashboard** — progress bar, running RPS counter, success/error
   rates updating in real time via WebSocket
3. **Results View** — metrics table + latency distribution histogram +
   P50/P95/P99 bar chart
4. **History** — list of past runs with sortable metrics table

---

*End of document — WolkenLoadRunner v1.0*
