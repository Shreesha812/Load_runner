"""Generate a ramp-up test Excel file for Sprint 3 verification."""
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.title = "RampUpTest"

headers = [
    "URL", "HTTP Method", "Headers", "Request message Template",
    "variable list Order", "List Of values", "variables",
    "Total concurrent request", "Response Structure", "Enable",
    "ramp up seconds",
]
ws.append(headers)

# Test 1 — 20 workers ramped over 10 seconds, sequential
ws.append([
    "https://jsonplaceholder.typicode.com/posts",
    "GET",
    "Accept: application/json",
    "",
    "sequential",
    "userId:1,2,3,4,5,6,7,8,9,10",
    None,
    20,
    "id",
    "Enable",
    10,   # ramp_up_seconds
])

# Test 2 — 10 workers, no ramp (baseline comparison)
ws.append([
    "https://jsonplaceholder.typicode.com/posts",
    "GET",
    "Accept: application/json",
    "",
    "sequential",
    "userId:1,2,3,4,5",
    None,
    10,
    "id",
    "Enable",
    0,    # no ramp
])

wb.save("input/rampup_test.xlsx")
print("Created input/rampup_test.xlsx")
print("  Test 1: 20 workers, 10s ramp, 10 requests")
print("  Test 2: 10 workers, no ramp, 5 requests")
