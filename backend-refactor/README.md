# Assignment

This application is a backend that provides endpoints around Signals data. A tech enthusiast on the business side has been maintaining this application, now the IT department has been tasked with taking it over. 

Initial Assessment: 
The code quality is low, the previous developer was copying/pasting from tutorials.

Todo: 
- Productionalise this application (This is purposely vague, implement what you think is necessary for this small application to work on prod)
- Spend around 4-6 hours on this, document how you spent your time.

# Planned Tasks

- make it run "as-is" in containerized environment
- understand the endpoints and the data model
- check for available tests, test-coverage?
- add tests if necessary (before changing any code)
- check for security issues (e.g. SQL injection, XSS, etc.)
- check for performance issues (e.g. slow queries, memory leaks, etc.)
- refactor code if necessary (after adding tests)
- add error handling and validation if necessary
- add logging and monitoring if necessary
- add documentation if necessary (e.g. API docs, code comments, etc.)

# Time Spent

## Planning (10min)
Checkout code, understand the structure, and plan the tasks.

## Containerization & Modernization (20min)
Created a Dockerfile to run the application in a container. Some changes needed (no-code, setup only)
- No python version mentioned: going for [version 3.11](https://devguide.python.org/versions/) because of the pinned dependencies in the requirements.txt file
- Missing dependencies added: pydantic-settings
- Move all code to new *src* folder to follow best practices and avoid potential issues with relative imports
- Use a modern base image (uv) that is optimized for Python applications and provides better performance and security
- Create *pyproject.toml* file to manage dependencies and build configuration, which is a modern standard for Python projects

Run the api locally with (after installing [uv](https://docs.astral.sh/uv/getting-started/installation/))
```
uv run --directory src main.py
```
or in a container with (after installing [docker-engine](https://docs.docker.com/engine/install/))
```
docker build -t asset-api .
docker run -d --rm --name asset-api -p 8000:8000 asset-api
```

- Introduce *uv.lock* file to lock dependencies and ensure reproducible builds. Update the dependencies with `uv lock` and commit the changes to version control.

## Understanding the Endpoints and Data Model (30min)
- Inspecting swagger page at http://localhost:8000/docs to understand the available endpoints and their functionality
- huge mess! duplication of endpoints, v1 vs v2, easter egg within the health endpoint, etc.
- /assets endpoint does not return the assets, but instead returns signal information.
- /measurements endpoint (returning a list of data points): does not work at all!
- data models are very simple, no default values, no validation, no documentation, etc. should all be done with pydantic models.
- data persistence: all data is read from files, which is not ideal for production. No typing at all, which makes it hard to understand the code and maintain it.
- almost no business logic - just reading json files and returning the data. No error handling, no validation, no logging, etc.
  
I see the following use-cases:
- get a health check (GET /health)
- get a list of all assets (GET /assets)
- get a list of all signals for an asset (GET /assets/{asset_id}/signals)
- get a list of all signals (GET /signals)
- get details for a signal (GET /signals/{signal_id})
- get stats for a signal (GET /signals/{signal_id}/stats)
- get a list of measurements for a signal (GET /signals/{signal_id}/measurements)
- get a list of measurements for a list of signals (GET /measurements?signal_ids=1,2,3)

*UPDATING THE INITIAL PLAN* not adding tests first (it's too messy and too simple), cleaning up first and then adding tests.

## Refactoring (120min)
- Remove the easter egg
- Simplify/cleanup settings class
- Write full pydantic models for all the data structures (assets, signals, measurements, etc.). Add new data model for Measurements (list of data points).
- Add test framework, including test coverage.

Run the tests locally with
```
uv run pytest -v
```

or in container with
```
docker compose run --build unit-tests
```

- Delete unused/obsolete code (utils, utilities, helpers)
- Move data files to a dedicated directory (e.g., `data/`)
- Seperate concerns between data, business, and actual application logic
- Change asset and signal ids to be ints instead of strings, which is more common and easier to work with

## Error Handling, Logging, integ tests, and Cleanup (60min)
- Add error handling for all endpoints, including validation errors, not found errors, and internal server errors.
- Add logging
- Do overall cleanup
- Add docker compose file to run the application and tests in a containerized environment
- Add integration tests for all endpoints, including edge cases and error cases. Use newman for this, which is a modern and easy-to-use tool for testing APIs.

Run the integration tests in docker with
```
docker compose run --build integration-tests
```

## Performance and Security (30min)
- New output format query parameter for measurements endpoint to return a flat list of data points instead of a nested structure. This is more efficient and easier to work with for clients.
- Add pagination to the measurements endpoint to avoid returning too much data at once, which can cause performance issues and make it harder for clients to work with the data.
- Improve search logic to get rid of O(n) complexity and use a more efficient data structure (e.g., a dictionary) to store the data in memory, which will significantly improve the performance of the endpoints.
- No Pydantic model for chached measurements, simple named tuple instead, which is more efficient and easier to work with for this use case.
- Add warmup logic to the application to pre-load the data into memory when the application starts, which will improve the performance of the endpoints and reduce the response time for clients.
- Concerning Security: since this is a simple API that reads data from files and does not have any user input or authentication, there are no major security issues to address. However, in a production environment, it would be important to implement proper access controls and authentication mechanisms to protect the data and prevent unauthorized access.
- Update FastAPI to 0.115.11 (known CVE)
- Add guardrails for the measurements endpoint to prevent potential performance issues (e.g., limit the number of signal ids that can be queried at once, limit the date range for queries, etc.)
- Sandboxing path env vars to prevent potential security issues (e.g., path traversal attacks, etc.)
- All other security concerns like rate limiting, CORS middleware are considered to be a deployment concern and should be handled by the infrastructure team (e.g., API gateway, load balancer, etc.) rather than the application itself.

## Documentation (20min)
- Compose specs.md file to document the API endpoints, data models, and any other relevant information about the application. This will help other developers understand how to use the API and maintain the codebase in the future.
- 