"""
Generate a real-world high-concurrency test Excel file.

This creates a test file targeting a public REST API (JSONPlaceholder)
with 100 concurrent workers and meaningful variable combinations.
"""
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.title = "HighLoadTest"

# Header row — matching WolkenLoadRunner's parser
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

# Test 1 — GET with query params, high concurrency
# JSONPlaceholder has 100 users and 100 posts — we'll test cross-product
ws.append([
    "https://jsonplaceholder.typicode.com/posts",
    "GET",
    "Accept: application/json\nUser-Agent: WolkenLoadRunner/1.0",
    "",  # GET has no body
    "sequential",
    "userId:1,2,3,4,5,6,7,8,9,10",  # 10 user IDs (no braces)
    None,
    100,  # 100 concurrent workers
    "userId,id,title,body",  # Expected JSON response keys
    "Enable",
])

# Test 2 — POST with JSON body, medium concurrency
# Create new posts with variable user IDs and titles
ws.append([
    "https://jsonplaceholder.typicode.com/posts",
    "POST",
    "Content-Type: application/json\nAccept: application/json",
    '{"userId": <userId>, "title": "<title>", "body": "Load test post from WolkenLoadRunner"}',
    "random",
    "userId:1,2,3,4,5, title:Test Post Alpha,Test Post Beta,Test Post Gamma",  # No braces
    None,
    50,  # 50 concurrent workers
    "id",  # POST returns the created resource with an ID
    "Enable",
])

# Test 3 — GET specific resource by ID, sequential check
ws.append([
    "https://jsonplaceholder.typicode.com/users/<userId>",
    "GET",
    "Accept: application/json",
    "",
    "sequential",
    "userId:1,2,3,4,5,6,7,8,9,10",  # Check first 10 users
    None,
    10,  # Lower concurrency for individual resource lookups
    "id,name,email,username",
    "Enable",
])

# Save the file
wb.save("input/high_load_test.xlsx")
print("Created input/high_load_test.xlsx")
print()
print("Test summary:")
print("  Test 1: GET /posts with 10 userIds → 100 concurrent workers")
print("  Test 2: POST /posts with 5 users × 3 titles → 50 workers, random")
print("  Test 3: GET /users/<id> for 10 users → 10 workers, sequential")
print()
print("Total expected requests: 10 + 15 + 10 = 35")
print("Max concurrency: 100 workers")
