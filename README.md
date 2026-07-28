# LoadRunner

An async HTTP load testing tool driven by Excel configuration. Define your test cases in a spreadsheet, run them with up to hundreds of concurrent workers, and get detailed latency metrics with a real-time web dashboard.

Built with Python (asyncio + FastAPI) and React.

---

## What it does

- Reads test definitions from an Excel file — URLs, methods, headers, request bodies, variables, concurrency
- Substitutes `<variable>` placeholders in request bodies and URLs
- Generates all combinations (sequential) or samples randomly (random strategy)
- Fires requests with configurable concurrency using a shared async HTTP connection pool
- Streams live metrics to a web dashboard over WebSocket
- Reports min / max / avg / P50 / P95 / P99 latency, RPS, success/failure lists with request IDs
- Persists all run history to SQLite — survives server restarts
- Supports mid-run cancellation via a Stop button

---

## Stack

| Layer | Technology |
|---|---|
| Engine | Python 3.12+, asyncio, aiohttp |
| API | FastAPI, uvicorn, aiosqlite |
| Frontend | React, TypeScript, Tailwind CSS, Recharts |
| Storage | SQLite (via aiosqlite) |
| Input | openpyxl (.xlsx) |

---

## Project structure

```
Load_runner/
├── main.py                        # CLI entry point
├── backend/                       # FastAPI app
│   ├── main.py                    # App factory, lifespan, CORS
│   ├── api/routes.py              # All REST + WebSocket endpoints
│   ├── runner.py                  # Async run executor
│   ├── store.py                   # SQLite-backed run store
│   ├── cancel.py                  # Cancellation registry
│   ├── models.py                  # Pydantic API models
│   └── db/
│       └── database.py            # Schema, init_db, get_db
├── frontend/                      # React app (Vite)
│   └── src/
│       ├── pages/                 # Upload, Live, Results, History
│       └── components/            # MetricCard, LiveChart, LatencyChart, ...
├── scheduler/scheduler.py         # Producer/consumer orchestrator
├── workers/worker.py              # Per-request async worker
├── client/http_client.py          # Shared aiohttp session + pool
├── metrics/metrics.py             # Latency collector (P50/P95/P99)
├── generator/                     # Sequential + random combination strategies
├── parser/                        # Excel parser, variable parsers
├── renderer/template_renderer.py  # <variable> substitution
├── models/                        # Engine data models
├── report/                        # Console + file reports (JSON/CSV)
├── docs/ARCHITECTURE.md           # Full design and module reference
└── input/                         # Excel test files go here
```

---

## Getting started

### Prerequisites

- Python 3.12+
- Node.js 18+

### 1. Clone

```bash
git clone https://github.com/Shreesha812/Load_runner.git
cd Load_runner
```

### 2. Python setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Frontend setup

```bash
cd frontend
npm install
cd ..
```

### 4. Run

Open two terminals from the project root.

**Terminal 1 — Backend**
```bash
.venv/bin/uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend**
```bash
cd frontend && npm run dev
```

Then open `http://localhost:5173` in your browser.

---

## Excel input format

Create an `.xlsx` file with these columns (order doesn't matter):

| Column | Description |
|---|---|
| `URL` | Target endpoint, e.g. `https://api.example.com/chat` |
| `HTTP Method` | `GET`, `POST`, `PUT`, `DELETE`, `PATCH` |
| `Headers` | One `Key: Value` per line |
| `Request message Template` | Body with `<variable>` placeholders |
| `variable list Order` | `sequential` or `random` |
| `List Of values` | Multi-value vars — `v1:a,b,c` or `v1:{a,b,c}` |
| `variables` | Single-value vars — `v1:abc, v2:123` |
| `Total concurrent request` | Number of parallel workers |
| `Response Structure` | Comma-separated JSON keys to assert in response |
| `Enable` | `Enable` or `Disable` |

### Variable syntax

Braces are optional — both forms work:

```
# With braces
query:{hello world, how are you}, user_id:{101,102,103}

# Without braces (same result)
query:hello world, how are you, user_id:101,102,103
```

Sequential strategy generates the full Cartesian product. Random strategy samples indefinitely and is capped at `max(concurrency, total_combinations)` requests.

---

## Running from the CLI (no UI)

```bash
# Basic run
.venv/bin/python main.py --input input/your_test.xlsx

# With output report
.venv/bin/python main.py \
  --input input/your_test.xlsx \
  --output output/results.json \
  --log-level INFO \
  --timeout 30 \
  --pool-size 100
```

All CLI flags:

```
--input   -i   Path to Excel file         (default: input/WolkenLoadRunner_input.xlsx)
--output  -o   Report file (.json/.csv)   (optional)
--log-level    DEBUG|INFO|WARNING|ERROR   (default: INFO)
--timeout      Request timeout in seconds (default: 30)
--connect-timeout  TCP connect timeout    (default: 10)
--pool-size    Max HTTP connections       (default: 100)
```

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/run` | Upload Excel and start a run |
| `DELETE` | `/api/run/{id}` | Cancel a running test |
| `GET` | `/api/run/{id}` | Get run status and results |
| `GET` | `/api/runs` | List all past runs |
| `WS` | `/api/run/{id}/live` | Real-time metrics stream |
| `GET` | `/api/results/{id}/json` | Download JSON report |
| `GET` | `/api/results/{id}/csv` | Download CSV report |

Interactive API docs: `http://localhost:8000/docs`

---

## Metrics reported

| Metric | Description |
|---|---|
| Total / Success / Failed | Request counts |
| Avg latency | Mean response time in ms |
| Min / Max latency | Fastest and slowest request |
| P50 | Median — half of requests faster than this |
| P95 | 95th percentile — the slow tail |
| P99 | 99th percentile — worst 1% |
| RPS | Requests per second |
| Execution time | Total wall-clock time |
| Success list | Per-request IDs, status codes, latency, variables used |
| Failure list | Same, for failed requests |

---

## Sample test file

A sample high-concurrency test file is included at `input/high_load_test.xlsx`.

It targets [JSONPlaceholder](https://jsonplaceholder.typicode.com) (a free public test API) with three tests:

- `GET /posts` — 10 user IDs, 100 concurrent workers, sequential
- `POST /posts` — 5 users × 3 titles, 50 workers, random
- `GET /users/<id>` — 10 user IDs with URL variable substitution, 10 workers

---

## Roadmap (v2)

- [ ] Ramp-up mode — gradually increase workers over a configurable period
- [ ] Comparison view — diff two runs side by side
- [ ] In-browser enable/disable toggles for test definitions
- [ ] Error categorisation — timeout / connection error / 4xx / 5xx breakdown
- [ ] API authentication (opt-in)

---

## Documentation

Full architecture, module reference, data flow, and design decisions are in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## License

MIT
