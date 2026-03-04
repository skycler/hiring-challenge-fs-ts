use std::sync::Arc;

use axum::extract::{Query, State};
use axum::Json;
use serde::Deserialize;

use crate::errors::AppError;
use crate::routes::signals::{parse_datetime, validate_limit, validate_offset};
use crate::service::AssetService;

const MAX_SIGNAL_IDS: usize = 100;

/// Query parameters for multi-signal measurements endpoint.
#[derive(Debug, Deserialize)]
pub struct MultiMeasurementsQuery {
    pub signal_ids: Option<String>,
    pub from: Option<String>,
    pub to: Option<String>,
    pub limit: Option<i64>,
    pub offset: Option<i64>,
    pub format: Option<String>,
}

/// GET /measurements
#[utoipa::path(
    get,
    path = "/measurements",
    params(
        ("signal_ids" = String, Query, description = "Comma-separated signal IDs"),
        ("from" = String, Query, description = "Start datetime (ISO 8601)"),
        ("to" = String, Query, description = "End datetime (ISO 8601)"),
        ("limit" = Option<i64>, Query, description = "Page size (1-10000, default 1000)"),
        ("offset" = Option<i64>, Query, description = "Offset (default 0)"),
        ("format" = Option<String>, Query, description = "Response format: objects or flat")
    ),
    responses(
        (status = 200, description = "Paginated measurements"),
        (status = 400, description = "Invalid parameters"),
        (status = 404, description = "Signal not found"),
        (status = 422, description = "Missing parameters")
    )
)]
pub async fn get_measurements(
    State(service): State<Arc<AssetService>>,
    Query(params): Query<MultiMeasurementsQuery>,
) -> Result<Json<serde_json::Value>, AppError> {
    // Validate signal_ids presence
    let signal_ids_str = params
        .signal_ids
        .ok_or_else(|| AppError::UnprocessableEntity("Missing required parameter: 'signal_ids'".to_string()))?;

    // Parse signal_ids with the specific validation order from spec:
    // 1. Empty check (400)
    // 2. Max count check (400)
    // 3. Integer parse validation (400)
    // 4. Existence checks (404) - done in service
    // 5. Date range validation (400) - done in service

    let segments: Vec<&str> = signal_ids_str
        .split(',')
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .collect();

    if segments.is_empty() {
        return Err(AppError::BadRequest(
            "At least one signal ID is required".to_string(),
        ));
    }

    if segments.len() > MAX_SIGNAL_IDS {
        return Err(AppError::BadRequest(format!(
            "Too many signal_ids (max {})",
            MAX_SIGNAL_IDS
        )));
    }

    let parsed_ids: Result<Vec<i64>, _> = segments.iter().map(|s| s.parse::<i64>()).collect();
    let signal_ids = parsed_ids.map_err(|_| {
        AppError::BadRequest("signal_ids must be valid integers".to_string())
    })?;

    // Validate from/to presence
    let from_str = params
        .from
        .ok_or_else(|| AppError::UnprocessableEntity("Missing required parameter: 'from'".to_string()))?;
    let to_str = params
        .to
        .ok_or_else(|| AppError::UnprocessableEntity("Missing required parameter: 'to'".to_string()))?;

    let format = params.format.unwrap_or_else(|| "objects".to_string());
    if format != "objects" && format != "flat" {
        return Err(AppError::UnprocessableEntity(format!(
            "Invalid format '{}'. Must be 'objects' or 'flat'",
            format
        )));
    }

    let limit = validate_limit(params.limit)?;
    let offset = validate_offset(params.offset)?;

    let from = parse_datetime(&from_str)?;
    let to = parse_datetime(&to_str)?;

    let result =
        service.get_multi_signal_measurements(&signal_ids, from, to, limit, offset, &format)?;
    Ok(Json(result))
}
