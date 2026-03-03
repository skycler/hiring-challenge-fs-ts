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
- add logging and monitoring if necessary
- add documentation if necessary (e.g. API docs, code comments, etc.)

# Time Spent

## Planning (5min)
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
