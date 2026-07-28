"""One-shot script to generate input/sample_test.xlsx for the demo run."""
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.title = "LoadTest"

headers = [
    "URL",
    "HTTP Method",
    "Headers",
    "Request message Template",
    "variable list Order",
    "List Of values",
    "variables",
    "Total concurrent request",
    "Response Structure",
    "Enable",
]
ws.append(headers)

# Test 1 — POST with 3x3 = 9 combinations, 3 concurrent workers
ws.append([
    "https://postman-echo.com/post",
    "POST",
    "Content-Type: application/json",
    '{"query": "<query>", "user_id": "<user_id>"}',
    "sequential",
    "query:{hello world,how are you,what is AI}, user_id:{101,102,103}",
    None,
    3,
    "json",
    "Enable",
])

# Test 2 — GET, random, 2 concurrent
ws.append([
    "https://postman-echo.com/get",
    "GET",
    None,
    "",
    "random",
    None,
    "env:staging",
    2,
    "url",
    "Enable",
])

wb.save("input/sample_test.xlsx")
print("Saved input/sample_test.xlsx")
