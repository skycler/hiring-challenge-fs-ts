# AssetAPI -- Full Specification

## 1. Overview

AssetAPI is a read-only REST API that serves telemetry data from electrical substations. It exposes structured access to three domain entities -- **Assets** (physical substations), **Signals** (measurement channels on assets), and **Measurements** (timestamped readings from signals) -- along with computed **statistics** over measurement data.

The API is stateless and read-only. All data originates from flat files (JSON and CSV) provided at deployment time. The system is designed to be containerized, with data mounted as a read-only volume.

---

## 2. Domain Model

### 2.1 Asset

A physical installation (electrical substation) with a geographic location.

| Field         | Type    | Description                              |
|---------------|---------|------------------------------------------|
| `asset_id`    | integer | Unique identifier for the asset          |
| `latitude`    | float   | WGS 84 latitude                          |
| `longitude`   | float   | WGS 84 longitude                         |
| `description` | string  | Human-readable name (e.g. "UW Beznau")   |

### 2.2 Signal

A named measurement channel belonging to exactly one asset.

| Field          | Type    | Description                                          |
|----------------|---------|------------------------------------------------------|
| `signal_g_id`  | string  | Global unique identifier (UUID v4 format)            |
| `signal_id`    | integer | Numeric identifier, unique across all signals        |
| `signal_name`  | string  | Technical name of the signal channel                 |
| `asset_id`     | integer | Foreign key referencing the owning asset             |
| `unit`         | string  | Unit of measurement (e.g. `"kV"`, `"kW"`)           |

**Relationship**: Many signals belong to one asset. An asset may have zero or more signals.

### 2.3 Measurement

A single timestamped reading from a signal.

| Field        | Type     | Description                                  |
|--------------|----------|----------------------------------------------|
| `timestamp`  | datetime | ISO 8601 timestamp with sub-second precision |
| `signal_id`  | integer  | Foreign key referencing the signal            |
| `value`      | float    | The measured value in the signal's unit       |

**Relationship**: Many measurements belong to one signal. A signal may have zero or more measurements.

### 2.4 SignalStats

Computed aggregate statistics for a single signal over a requested time range. This is not a persisted entity; it is derived on the fly from measurements.

| Field       | Type           | Description                                          |
|-------------|----------------|------------------------------------------------------|
| `signal_id` | integer        | The signal these statistics describe                 |
| `from_date` | datetime       | Start of the requested time range (inclusive)        |
| `to_date`   | datetime       | End of the requested time range (inclusive)          |
| `count`     | integer        | Number of measurements in the range                  |
| `mean`      | float or null  | Arithmetic mean of values; `null` when count is 0    |
| `min`       | float or null  | Minimum value; `null` when count is 0                |
| `max`       | float or null  | Maximum value; `null` when count is 0                |
| `median`    | float or null  | Median value; `null` when count is 0                 |
| `std_dev`   | float or null  | Sample standard deviation; `null` when count is 0; `0.0` when count is 1 |

Numeric fields are rounded to 2 decimal places.

### 2.5 Response Format (Enum)

Measurement list endpoints support two serialization layouts, selectable via a `format` query parameter:

| Value     | Description                                          | Default |
|-----------|------------------------------------------------------|---------|
| `objects` | Array-of-objects format (backward-compatible)        | yes     |
| `flat`    | Parallel-arrays / columnar format (compact for large payloads) | no |

### 2.6 MeasurementList (Objects Format)

Paginated wrapper used when `format=objects` (the default). The two formats are **mutually exclusive** -- the response contains either `measurements` or the three parallel arrays, never both.

| Field          | Type              | Description                                        |
|----------------|-------------------|----------------------------------------------------|
| `total`        | integer           | Total matching measurements before pagination      |
| `count`        | integer           | Number of measurements in this page (`len(measurements)`) |
| `limit`        | integer           | The page size that was applied                     |
| `offset`       | integer           | The zero-based offset into the full result set     |
| `measurements` | Measurement array | The page of measurement objects                    |

### 2.7 FlatMeasurementList (Flat Format)

Paginated wrapper used when `format=flat`. Replaces the array of measurement objects with three parallel arrays of equal length, eliminating per-row key repetition for more compact payloads. The *i*-th element in each array corresponds to the same measurement.

| Field          | Type            | Description                                         |
|----------------|-----------------|-----------------------------------------------------|
| `total`        | integer         | Total matching measurements before pagination       |
| `count`        | integer         | Number of measurements in this page                 |
| `limit`        | integer         | The page size that was applied                      |
| `offset`       | integer         | The zero-based offset into the full result set      |
| `timestamps`   | datetime array  | Measurement timestamps                              |
| `signal_ids`   | integer array   | Signal ID for each measurement                      |
| `values`       | float array     | Measurement values                                  |

---

## 3. Data Sources

All source data is supplied as flat files. These files are external to the application and mounted as a read-only volume at runtime. File paths are configurable.

### 3.1 Assets File

- **Format**: JSON array
- **Default path**: `data/assets.json`
- **Encoding**: UTF-8
- **Source field mapping**:

| Source Key   | Domain Field  | Notes                                      |
|--------------|---------------|--------------------------------------------|
| `AssetID`    | `asset_id`    | Stored as string in source; must parse to integer |
| `Latitude`   | `latitude`    | Stored as string in source; must parse to float   |
| `Longitude`  | `longitude`   | Stored as string in source; must parse to float   |
| `descri`     | `description` | Truncated key name (not `Description`)            |

**Example record**:
```json
{
  "AssetID": "1",
  "Latitude": "47.5568277613",
  "Longitude": "8.2338560914",
  "descri": "UW Beznau"
}
```

**Known data**: 3 assets (IDs: 1, 2, 3).

### 3.2 Signals File

- **Format**: JSON array
- **Default path**: `data/signal.json`
- **Encoding**: UTF-8
- **Source field mapping**:

| Source Key   | Domain Field    | Notes                                     |
|--------------|-----------------|-------------------------------------------|
| `SignalGId`  | `signal_g_id`   | UUID v4 string                            |
| `SignalId`   | `signal_id`     | Stored as string in source; must parse to integer |
| `SignalName` | `signal_name`   | Technical channel name                    |
| `AssetId`    | `asset_id`      | Stored as string in source; must parse to integer |
| `Unit`       | `unit`          | Unit string (e.g. `"kV"`, `"kW"`)        |

**Example record**:
```json
{
  "SignalGId": "045ad75f-d8c7-4c92-b252-05f515e4006f",
  "SignalId": "427038",
  "SignalName": "BEZOBF110BIRMENU_L12",
  "AssetId": "1",
  "Unit": "kV"
}
```

**Known data**: 4 signals.

| signal_id | asset_id | unit |
|-----------|----------|------|
| 427038    | 1        | kV   |
| 427659    | 2        | kV   |
| 427712    | 2        | kW   |
| 430247    | 3        | kV   |

### 3.3 Measurements File

- **Format**: Pipe-delimited CSV (`|` separator)
- **Default path**: `data/measurements.csv`
- **Encoding**: UTF-8 with BOM (`utf-8-sig`)
- **Decimal format**: European comma notation (e.g. `116,129` means `116.129`)
- **Source field mapping**:

| Source Column      | Domain Field  | Notes                                          |
|--------------------|---------------|-------------------------------------------------|
| `Ts`               | `timestamp`   | ISO 8601 datetime with sub-second precision     |
| `SignalId`         | `signal_id`   | Integer signal identifier                       |
| `MeasurementValue` | `value`       | European comma decimal; must convert `,` to `.` |

**Example rows**:
```
Ts|SignalId|MeasurementValue
2021-11-07 23:59:03.762|427038|116,129
2021-11-07 23:57:48.259|427038|115,9581
```

**Known data**: ~188,833 measurement rows spanning 2021-11-07 through 2022-02-07, across 4 signal IDs.

**Safety limit**: The CSV loader must enforce a maximum row limit (e.g. 10,000,000 rows) to prevent unbounded memory consumption from a maliciously large file. If the limit is exceeded, loading must fail with an error.

| signal_id | Approximate row count |
|-----------|-----------------------|
| 430247    | 124,183               |
| 427038    | 58,258                |
| 427712    | 3,872                 |
| 427659    | 2,521                 |

---

## 4. Configuration

The application must support the following configuration values, all overridable via environment variables:

| Setting              | Type   | Default                    | Description                        |
|----------------------|--------|----------------------------|------------------------------------|
| `APP_NAME`           | string | `"AssetAPI"`               | Application display name           |
| `API_VERSION`        | string | `"v1"`                     | API version label                  |
| `DEBUG`              | bool   | `false`                    | Enable debug-level logging         |
| `DATA_DIR`           | string | `"data"`                   | Root directory for all data files  |
| `SIGNALS_PATH`       | string | `"data/signal.json"`       | Path to the signals JSON file      |
| `ASSETS_PATH`        | string | `"data/assets.json"`       | Path to the assets JSON file       |
| `MEASUREMENTS_PATH`  | string | `"data/measurements.csv"`  | Path to the measurements CSV file  |

An `.env` file at the project root should also be supported for local development.

### 4.1 Path-Traversal Protection

All configured file paths must be validated before use to prevent path-traversal attacks:

1. The `DATA_DIR` must resolve to a location **inside the project root**. If it resolves outside, loading must fail with an error.
2. Each individual file path (`SIGNALS_PATH`, `ASSETS_PATH`, `MEASUREMENTS_PATH`) must resolve to a location **inside the resolved `DATA_DIR`**. If any path escapes the data directory (e.g. via `../`), loading must fail with an error.

This ensures that even if an attacker can control environment variables, they cannot read arbitrary files from the host filesystem.

---

## 5. API Endpoints

All responses use JSON with `Content-Type: application/json`. All response bodies use **snake_case** field names (not the PascalCase aliases from source files).

Error responses follow the structure: `{"detail": "<human-readable message>"}`.

### 5.1 Health Check

#### `GET /health`

Returns the application's health status. Used by container orchestrators for liveness/readiness probes.

**Parameters**: None

**Response** `200 OK`:
```json
{
  "status": "ok"
}
```

---

### 5.2 Assets

#### `GET /assets`

Returns all assets.

**Parameters**: None

**Response** `200 OK`: Array of Asset objects.
```json
[
  {
    "asset_id": 1,
    "latitude": 47.5568277613,
    "longitude": 8.2338560914,
    "description": "UW Beznau"
  }
]
```

**Validation**:
- Response is an array
- Each element has keys: `asset_id` (number), `latitude` (number), `longitude` (number), `description` (string)

---

#### `GET /assets/{asset_id}/signals`

Returns all signals belonging to a specific asset.

**Path Parameters**:

| Parameter  | Type    | Required | Description           |
|------------|---------|----------|-----------------------|
| `asset_id` | integer | yes      | The ID of the asset   |

**Response** `200 OK`: Array of Signal objects. All returned signals have `asset_id` matching the path parameter.
```json
[
  {
    "signal_g_id": "045ad75f-d8c7-4c92-b252-05f515e4006f",
    "signal_id": 427038,
    "signal_name": "BEZOBF110BIRMENU_L12",
    "asset_id": 1,
    "unit": "kV"
  }
]
```

**Error Responses**:

| Status | Condition                        | Detail message            |
|--------|----------------------------------|---------------------------|
| `404`  | No asset exists with given ID    | Contains descriptive text |

---

### 5.3 Signals

#### `GET /signals`

Returns all signals across all assets.

**Parameters**: None

**Response** `200 OK`: Array of Signal objects.
```json
[
  {
    "signal_g_id": "045ad75f-d8c7-4c92-b252-05f515e4006f",
    "signal_id": 427038,
    "signal_name": "BEZOBF110BIRMENU_L12",
    "asset_id": 1,
    "unit": "kV"
  }
]
```

**Validation**:
- Response is an array
- Each element has keys: `signal_g_id` (string), `signal_id` (number), `signal_name` (string), `asset_id` (number), `unit` (string)

---

#### `GET /signals/{signal_id}`

Returns a single signal by its numeric ID.

**Path Parameters**:

| Parameter   | Type    | Required | Description            |
|-------------|---------|----------|------------------------|
| `signal_id` | integer | yes      | The ID of the signal   |

**Response** `200 OK`: A single Signal object.

**Error Responses**:

| Status | Condition                         | Detail message            |
|--------|-----------------------------------|---------------------------|
| `404`  | No signal exists with given ID    | Contains descriptive text |

---

#### `GET /signals/{signal_id}/stats`

Computes aggregate statistics for a signal's measurements within a time range.

**Path Parameters**:

| Parameter   | Type    | Required | Description            |
|-------------|---------|----------|------------------------|
| `signal_id` | integer | yes      | The ID of the signal   |

**Query Parameters**:

| Parameter | Type     | Required | Alias | Description                     |
|-----------|----------|----------|-------|---------------------------------|
| `from`    | datetime | yes      | --    | Start of time range (ISO 8601)  |
| `to`      | datetime | yes      | --    | End of time range (ISO 8601)    |

**Date filtering**: Both bounds are **inclusive** (`>=` from, `<=` to).

**Response** `200 OK`: A SignalStats object.
```json
{
  "signal_id": 427038,
  "from_date": "2021-11-07T00:00:00",
  "to_date": "2021-12-01T00:00:00",
  "count": 1500,
  "mean": 115.82,
  "min": 110.50,
  "max": 120.30,
  "median": 115.79,
  "std_dev": 1.42
}
```

**When no measurements exist** in the range, the response has `count: 0` and all numeric aggregates are `null`:
```json
{
  "signal_id": 427038,
  "from_date": "2099-01-01T00:00:00",
  "to_date": "2099-12-31T00:00:00",
  "count": 0,
  "mean": null,
  "min": null,
  "max": null,
  "median": null,
  "std_dev": null
}
```

**Error Responses**:

| Status | Condition                                 | Detail message                     |
|--------|-------------------------------------------|------------------------------------|
| `404`  | No signal exists with given ID            | Contains descriptive text          |
| `400`  | `from` >= `to` (reversed/equal dates)     | Must mention "date range"          |
| `422`  | Missing required query parameters         | Framework validation error         |

---

#### `GET /signals/{signal_id}/measurements`

Returns paginated measurements for a single signal within a time range.

**Path Parameters**:

| Parameter   | Type    | Required | Description            |
|-------------|---------|----------|------------------------|
| `signal_id` | integer | yes      | The ID of the signal   |

**Query Parameters**:

| Parameter | Type           | Required | Default   | Constraints           | Description                                |
|-----------|----------------|----------|-----------|-----------------------|--------------------------------------------|
| `from`    | datetime       | yes      | --        | --                    | Start of time range (ISO 8601)             |
| `to`      | datetime       | yes      | --        | --                    | End of time range (ISO 8601)               |
| `limit`   | integer        | no       | 1000      | 1 <= limit <= 10000   | Maximum results per page                   |
| `offset`  | integer        | no       | 0         | offset >= 0           | Number of results to skip                  |
| `format`  | string (enum)  | no       | `objects` | `objects` or `flat`   | Response serialization layout (see 2.5)    |

**Date filtering**: Both bounds are **inclusive** (`>=` from, `<=` to).

**Response** `200 OK` (`format=objects`, default): A MeasurementList object.
```json
{
  "total": 1500,
  "count": 5,
  "limit": 5,
  "offset": 10,
  "measurements": [
    {
      "timestamp": "2021-11-07T23:59:03.762000",
      "signal_id": 427038,
      "value": 116.129
    }
  ]
}
```

**Response** `200 OK` (`format=flat`): A FlatMeasurementList object.
```json
{
  "total": 1500,
  "count": 5,
  "limit": 5,
  "offset": 10,
  "timestamps": ["2021-11-07T23:59:03.762000", "..."],
  "signal_ids": [427038, 427038, 427038, 427038, 427038],
  "values": [116.129, 115.9581, 116.0436, 115.8727, 115.7872]
}
```

**Format guarantees**:
- `objects` response has a `measurements` key and does **not** have `timestamps`, `signal_ids`, or `values` keys
- `flat` response has `timestamps`, `signal_ids`, and `values` keys and does **not** have a `measurements` key
- In `flat` format, all three parallel arrays have the same length, equal to `count`

**Pagination semantics**:
- `total` is the count of all measurements matching the signal and date filters, before pagination
- `count` is the number of measurements returned in this page (always `<= limit`)
- In `objects` format: `count` equals `len(measurements)`
- In `flat` format: `count` equals `len(timestamps)` equals `len(signal_ids)` equals `len(values)`
- The page contains at most `limit` items, starting from position `offset` in the filtered result set

**Error Responses**:

| Status | Condition                                 | Detail message                     |
|--------|-------------------------------------------|------------------------------------|
| `404`  | No signal exists with given ID            | Contains descriptive text          |
| `400`  | `from` >= `to` (reversed/equal dates)     | Contains descriptive text          |
| `422`  | Missing required query parameters         | Framework validation error         |
| `422`  | `format` is not `objects` or `flat`       | Framework validation error         |

---

### 5.4 Multi-Signal Measurements

#### `GET /measurements`

Returns paginated measurements for one or more signals within a time range.

**Query Parameters**:

| Parameter    | Type           | Required | Default   | Constraints            | Description                                        |
|--------------|----------------|----------|-----------|------------------------|----------------------------------------------------|
| `signal_ids` | string         | yes      | --        | max 100 IDs after parse | Comma-separated list of integer signal IDs         |
| `from`       | datetime       | yes      | --        | --                     | Start of time range (ISO 8601)                     |
| `to`         | datetime       | yes      | --        | --                     | End of time range (ISO 8601)                       |
| `limit`      | integer        | no       | 1000      | 1 <= limit <= 10000    | Maximum results per page                           |
| `offset`     | integer        | no       | 0         | offset >= 0            | Number of results to skip                          |
| `format`     | string (enum)  | no       | `objects` | `objects` or `flat`    | Response serialization layout (see 2.5)            |

**Date filtering**: Both bounds are **inclusive** (`>=` from, `<=` to).

**`signal_ids` parsing rules**:
1. Split the string by `,`
2. Trim whitespace from each segment
3. Discard empty segments
4. Parse each remaining segment as an integer

**Response** `200 OK`: A MeasurementList or FlatMeasurementList depending on the `format` parameter (same response shapes and format guarantees as described in section 5.3). Each measurement's `signal_id` identifies which signal it belongs to. All returned measurements belong to one of the requested signal IDs.

**Error Responses**:

| Status | Condition                                          | Detail message                                          |
|--------|----------------------------------------------------|---------------------------------------------------------|
| `400`  | `signal_ids` is empty after parsing                | Indicates at least one signal ID is required             |
| `400`  | More than 100 signal IDs after parsing             | Must mention "max" and the limit (e.g. "Too many signal_ids (max 100)") |
| `400`  | Any segment in `signal_ids` is not a valid integer | Must mention "integers"                                  |
| `400`  | `from` >= `to` (reversed/equal dates)              | Contains descriptive text                                |
| `404`  | Any requested signal ID does not exist             | Must include the unknown signal ID(s) in the message     |
| `404`  | Mix of known and unknown signal IDs                | Same as above; fail if **any** ID is unknown             |
| `422`  | Missing `signal_ids`, `from`, or `to`              | Framework validation error                               |
| `422`  | `format` is not `objects` or `flat`                | Framework validation error                               |

**Validation order**: `signal_ids` emptiness check (400) happens first, then max-count check (400), then integer-parse validation (400), then existence checks (404), then date range validation (400).

---

## 6. Architecture Requirements

### 6.1 Layered Design

The application must follow a layered architecture with clear separation of concerns:

1. **Routes / HTTP Layer**: Handles HTTP request parsing, response serialization, and HTTP-specific error mapping. Must be thin -- no business logic here.
2. **Service Layer**: Contains all business logic -- filtering, pagination, statistics computation, and input validation rules (e.g. date range validity).
3. **Data Provider Layer**: Abstracts data access behind an interface. Decouples the rest of the application from the specific storage mechanism (filesystem, database, remote API, etc.).

### 6.2 Data Provider Abstraction

The data provider must be defined as an abstract interface (contract) with three operations:

| Operation            | Returns                  | Description                |
|----------------------|--------------------------|----------------------------|
| `load_signals`       | Array of Signal          | Returns all signals        |
| `load_assets`        | Array of Asset           | Returns all assets         |
| `load_measurements`  | Array of Measurement data | Returns all measurements  |

Providers return **complete** datasets. Filtering, indexing, and aggregation are the service layer's responsibility. The `load_measurements` return type carries the same fields as the Measurement model (timestamp, signal_id, value); implementations may use a lightweight in-memory representation (e.g. named tuples) rather than the full API-facing model to reduce memory overhead for large datasets.

A **filesystem-based provider** serves as the concrete implementation, reading from the files described in section 3. The interface must allow alternative implementations (e.g. a database provider or an in-memory stub for testing) to be substituted without changes to services or routes.

### 6.3 Dependency Injection

Services and providers must be wired together using dependency injection. This enables:
- Substituting test doubles (e.g. an in-memory stub provider) without modifying application code
- Singleton lifecycle management for providers and services
- Lazy initialization of expensive resources (e.g. the measurement index)

### 6.4 Caching and Performance

- **Data loading**: Each data file must be read and parsed at most once. Subsequent calls return cached results.
- **Measurement indexing**: Measurements must be indexed by `signal_id` after initial load to enable efficient lookups without scanning the entire dataset on every request. Within each signal's index, measurements must be **sorted by timestamp** to enable efficient date-range filtering (e.g. binary search) rather than linear scans.
- **Service singletons**: Service instances should be created once and reused across requests to preserve their internal caches (e.g. the measurement index).
- **Eager cache warming**: At application startup, all data caches and indexes should be eagerly initialized so the first user request is not penalized by cold-start latency (file parsing, index construction).

### 6.5 Configuration Management

- All file paths and behavioral settings must be externally configurable (environment variables)
- A `.env` file should be supported for local development convenience
- Configuration must be loaded once and cached as a singleton

### 6.6 API Documentation

- If the web framework provides interactive API documentation endpoints (e.g. Swagger UI, ReDoc), these must be **disabled in production** (when `DEBUG=false`) and **enabled only in debug mode** (when `DEBUG=true`)
- The OpenAPI schema endpoint must follow the same rule

---

## 7. Error Handling

### 7.1 HTTP Status Codes

| Code  | Meaning               | When Used                                                            |
|-------|-----------------------|----------------------------------------------------------------------|
| `200` | OK                    | Successful request                                                   |
| `400` | Bad Request           | Invalid input that is syntactically received but semantically wrong (reversed dates, non-integer signal IDs, empty signal list, exceeding maximum signal ID count) |
| `404` | Not Found             | Referenced entity (asset or signal) does not exist                   |
| `422` | Unprocessable Entity  | Required query parameters are missing or malformed (framework-level) |
| `503` | Service Unavailable   | A required data file is missing or unreadable at runtime             |

### 7.2 Error Response Format

All application-level errors must return a JSON body with a `detail` field containing a human-readable message:

```json
{
  "detail": "Signal 999999 not found"
}
```

Specific requirements for error messages:
- **404 for signals via `/measurements`**: The `detail` must include the unknown signal ID(s) so the caller knows which IDs were invalid
- **400 for reversed dates**: The `detail` must contain the phrase "date range"
- **400 for non-integer signal_ids**: The `detail` must contain the word "integers"
- **400 for too many signal_ids**: The `detail` must mention "max" and the numeric limit

### 7.3 Data Loading Errors

If source data files are missing or malformed, the application should:
- Log the error with sufficient context (file path, parse error details)
- If the error occurs during startup, propagate it (the application cannot serve requests without its data)
- If a data file becomes unavailable at runtime (after startup), return `503 Service Unavailable` with a generic message (e.g. `"Service temporarily unavailable"`). The response must **not** expose internal file-system paths.

---

## 8. Logging

The application must support structured logging with the following requirements:

- **Log levels**: Configurable between `INFO` (default) and `DEBUG` (when `DEBUG=true`)
- **Log format**: Timestamp, log level, logger name, and message
- **Required log events**:
  - Application startup: app name, version, debug mode
  - Data loading: file path and record count on successful load of each dataset
  - Data loading errors: file path and error details on failure
  - Debug mode warning: when `DEBUG=true`, log a warning that debug mode should not be used in production
- **No sensitive data** in logs

---

## 9. Containerization

### 9.1 Build

The application must be built as a container image with:

- **Multi-stage build** with at least the following stages:
  - **Test stage**: Includes dev dependencies and test suite. Runs the full test suite (unit tests) as its default command. Must output a JUnit XML test report to a mountable volume at `/reports`.
  - **Production stage**: Contains only production dependencies and application source. Does **not** include test code or data files.

### 9.2 Production Container

- **Port**: Exposes port `8000`
- **Data volume**: Data files are **not baked into the image**. They must be mounted as a read-only volume at runtime (e.g. `./data:/app/data:ro`).
- **Non-root user**: The production container must run as a non-root user for security.
- **Health check**: The container must define a health check that polls `GET /health` periodically (e.g. every 30 seconds) and expects a `200` response.

### 9.3 Compose Services

A Docker Compose configuration must define three services:

1. **`api`**: Runs the production application.
   - Builds the production stage
   - Maps port 8000 to host
   - Mounts `./data` as a read-only volume

2. **`unit-tests`**: Runs the unit test suite.
   - Builds the test stage
   - Mounts `./reports` for test report output
   - Default command runs all unit tests with JUnit XML output

3. **`integration-tests`**: Runs the integration test suite against the live API.
   - Depends on the `api` service being healthy (waits for health check to pass)
   - Mounts the integration test collection (read-only) and `./reports` for output
   - Runs the Postman/Newman collection against `http://api:8000`
   - Produces a JUnit XML report

---

## 10. Testing Requirements

### 10.1 Unit Tests

- **Coverage**: 100% line coverage across all application modules
- **Test isolation**: Use an in-memory stub provider (implementing the data provider interface) to avoid filesystem dependencies in tests
- **Route tests**: Use a test client with the stub provider injected via dependency override
- **Report format**: JUnit XML

### 10.2 Integration Tests

Integration tests run against a live instance of the API with real data mounted. They validate the full stack (HTTP -> routes -> services -> provider -> data files).

The integration test suite is defined as a Postman/Newman collection and must verify:

**Health** (2 assertions):
- `GET /health` returns `200` with `{"status": "ok"}`

**Assets** (5 assertions):
- `GET /assets` returns `200` with an array of 3 assets, each with correct field types
- `GET /assets/1/signals` returns `200` with signals all belonging to asset 1
- `GET /assets/999/signals` returns `404` with a `detail` message

**Signals** (4 assertions):
- `GET /signals` returns `200` with an array of 4 signals, each with correct field types
- `GET /signals/427038` returns `200` with `signal_id=427038`, `unit="kV"`, `asset_id=1`
- `GET /signals/999999` returns `404` with a `detail` message

**Signal Stats** (5 assertions):
- `GET /signals/427038/stats?from=...&to=...` returns `200` with all stats fields populated and count > 0
- Same endpoint with a future date range returns `200` with count=0 and null stats
- Unknown signal returns `404`
- Reversed dates return `400` with detail mentioning "date range"
- Missing params returns `422`

**Signal Measurements** (9 test requests):
- `GET /signals/427038/measurements?from=...&to=...` returns `200` with pagination fields (default limit=1000, offset=0), correct measurement field types
- With `limit=5&offset=10`: respects pagination, returns exactly 5 results
- With narrow date range: returns filtered data with count > 0
- Unknown signal returns `404`
- Reversed dates return `400`
- Missing params returns `422`
- With `format=flat`: returns `200` with `timestamps`, `signal_ids`, `values` arrays (no `measurements` key); all parallel arrays have length equal to `count`; all `signal_ids` entries match the requested signal
- With `format=objects`: returns `200` with `measurements` array (no `timestamps`/`signal_ids`/`values` keys)
- With `format=invalid`: returns `422`

**Multi-Signal Measurements** (13 test requests):
- `GET /measurements?signal_ids=427038,427659&from=...&to=...` returns `200`, all measurements belong to requested signals
- With `limit=3&offset=0`: respects pagination, returns exactly 3 results
- With narrow date range: returns filtered data
- Unknown signal_ids returns `404` with the unknown ID in the detail
- Mix of known + unknown returns `404`
- Non-integer signal_ids returns `400` with detail mentioning "integers"
- Empty signal_ids returns `400`
- Reversed dates return `400`
- Missing signal_ids param returns `422`
- Missing date params returns `422`
- With `format=flat`: returns `200` with `timestamps`, `signal_ids`, `values` arrays (no `measurements` key); parallel arrays have length equal to `count`; all `signal_ids` entries belong to the requested signals
- With `format=objects`: returns `200` with `measurements` array (no `timestamps`/`signal_ids`/`values` keys)
- With `format=invalid`: returns `422`

**Total: 34 integration test requests across all endpoints.**

---

## 11. Non-Functional Requirements

### 11.1 Performance

- Data files are loaded and parsed once at startup (or on first request), not on every API call
- Measurement lookup by signal ID must be indexed, not a linear scan of all measurements
- Date-range filtering within a signal's measurements must use efficient lookup (e.g. binary search on sorted timestamps), not a linear scan of all signal measurements
- Pagination must slice the filtered result set, not load unbounded data into responses

### 11.2 Security

- The production container runs as a non-root user
- Data files are mounted read-only
- No secrets or credentials are required (the API is read-only over flat files)
- All configured file paths must be validated against the data directory to prevent path-traversal attacks (see section 4.1)

### 11.3 Reliability

- The health check endpoint enables orchestrators to detect and restart unhealthy instances
- If data files fail to load, the error is logged and propagated (fail-fast)

### 11.4 Observability

- Structured logging with configurable verbosity
- Health endpoint for monitoring
- JUnit XML reports from both unit and integration test suites for CI/CD integration
