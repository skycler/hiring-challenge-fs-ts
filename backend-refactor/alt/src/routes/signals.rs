use std::sync::Arc;

use axum::extract::{Path, Query, State};
use axum::Json;
use chrono::NaiveDateTime;
use serde::Deserialize;

use crate::errors::AppError;
use crate::models::Signal;
use crate::service::AssetService;

/// Query parameters for stats endpoint.
#[derive(Debug, Deserialize)]
pub struct StatsQuery {
    pub from: Option<String>,
    pub to: Option<String>,
}

/// Query parameters for signal measurements endpoint.
#[derive(Debug, Deserialize)]
pub struct MeasurementsQuery {
    pub from: Option<String>,
    pub to: Option<String>,
    pub limit: Option<i64>,
    pub offset: Option<i64>,
    pub format: Option<String>,
}

/// GET /signals
#[utoipa::path(
    get,
    path = "/signals",
    responses(
        (status = 200, description = "All signals", body = Vec<Signal>)
    )
)]
pub async fn get_signals(
    State(service): State<Arc<AssetService>>,
) -> Json<Vec<Signal>> {
    Json(service.get_all_signals())
}

/// GET /signals/{signal_id}
#[utoipa::path(
    get,
    path = "/signals/{signal_id}",
    params(
        ("signal_id" = i64, Path, description = "Signal ID")
    ),
    responses(
        (status = 200, description = "Signal details", body = Signal),
        (status = 404, description = "Signal not found")
    )
)]
pub async fn get_signal(
    State(service): State<Arc<AssetService>>,
    Path(signal_id): Path<i64>,
) -> Result<Json<Signal>, AppError> {
    let signal = service.get_signal(signal_id)?;
    Ok(Json(signal))
}

/// GET /signals/{signal_id}/stats
#[utoipa::path(
    get,
    path = "/signals/{signal_id}/stats",
    params(
        ("signal_id" = i64, Path, description = "Signal ID"),
        ("from" = String, Query, description = "Start datetime (ISO 8601)"),
        ("to" = String, Query, description = "End datetime (ISO 8601)")
    ),
    responses(
        (status = 200, description = "Signal statistics"),
        (status = 400, description = "Invalid date range"),
        (status = 404, description = "Signal not found"),
        (status = 422, description = "Missing parameters")
    )
)]
pub async fn get_signal_stats(
    State(service): State<Arc<AssetService>>,
    Path(signal_id): Path<i64>,
    Query(params): Query<StatsQuery>,
) -> Result<Json<serde_json::Value>, AppError> {
    let from_str = params
        .from
        .ok_or_else(|| AppError::UnprocessableEntity("Missing required parameter: 'from'".to_string()))?;
    let to_str = params
        .to
        .ok_or_else(|| AppError::UnprocessableEntity("Missing required parameter: 'to'".to_string()))?;

    let from = parse_datetime(&from_str)?;
    let to = parse_datetime(&to_str)?;

    let stats = service.get_signal_stats(signal_id, from, to)?;
    Ok(Json(serde_json::to_value(stats).unwrap()))
}

/// GET /signals/{signal_id}/measurements
#[utoipa::path(
    get,
    path = "/signals/{signal_id}/measurements",
    params(
        ("signal_id" = i64, Path, description = "Signal ID"),
        ("from" = String, Query, description = "Start datetime (ISO 8601)"),
        ("to" = String, Query, description = "End datetime (ISO 8601)"),
        ("limit" = Option<i64>, Query, description = "Page size (1-10000, default 1000)"),
        ("offset" = Option<i64>, Query, description = "Offset (default 0)"),
        ("format" = Option<String>, Query, description = "Response format: objects or flat")
    ),
    responses(
        (status = 200, description = "Paginated measurements"),
        (status = 400, description = "Invalid date range"),
        (status = 404, description = "Signal not found"),
        (status = 422, description = "Invalid parameters")
    )
)]
pub async fn get_signal_measurements(
    State(service): State<Arc<AssetService>>,
    Path(signal_id): Path<i64>,
    Query(params): Query<MeasurementsQuery>,
) -> Result<Json<serde_json::Value>, AppError> {
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

    let result = service.get_signal_measurements(signal_id, from, to, limit, offset, &format)?;
    Ok(Json(result))
}

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

pub fn parse_datetime(s: &str) -> Result<NaiveDateTime, AppError> {
    // Try multiple formats
    NaiveDateTime::parse_from_str(s, "%Y-%m-%dT%H:%M:%S%.f")
        .or_else(|_| NaiveDateTime::parse_from_str(s, "%Y-%m-%dT%H:%M:%S"))
        .or_else(|_| NaiveDateTime::parse_from_str(s, "%Y-%m-%d %H:%M:%S%.f"))
        .or_else(|_| NaiveDateTime::parse_from_str(s, "%Y-%m-%d %H:%M:%S"))
        .or_else(|_| {
            // Date-only: parse as NaiveDate and convert to NaiveDateTime at midnight
            chrono::NaiveDate::parse_from_str(s, "%Y-%m-%d")
                .map(|d| d.and_hms_opt(0, 0, 0).unwrap())
        })
        .map_err(|e| {
            AppError::UnprocessableEntity(format!("Invalid datetime format '{}': {}", s, e))
        })
}

pub fn validate_limit(limit: Option<i64>) -> Result<usize, AppError> {
    match limit {
        None => Ok(1000),
        Some(l) if l >= 1 && l <= 10000 => Ok(l as usize),
        Some(l) => Err(AppError::UnprocessableEntity(format!(
            "limit must be between 1 and 10000, got {}",
            l
        ))),
    }
}

pub fn validate_offset(offset: Option<i64>) -> Result<usize, AppError> {
    match offset {
        None => Ok(0),
        Some(o) if o >= 0 => Ok(o as usize),
        Some(o) => Err(AppError::UnprocessableEntity(format!(
            "offset must be >= 0, got {}",
            o
        ))),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_datetime_iso() {
        let dt = parse_datetime("2021-11-07T00:00:00").unwrap();
        assert_eq!(dt.to_string(), "2021-11-07 00:00:00");
    }

    #[test]
    fn test_parse_datetime_with_fraction() {
        let dt = parse_datetime("2021-11-07T23:59:03.762000").unwrap();
        assert_eq!(dt.format("%Y-%m-%d %H:%M:%S%.6f").to_string(), "2021-11-07 23:59:03.762000");
    }

    #[test]
    fn test_parse_datetime_date_only() {
        let dt = parse_datetime("2021-11-07").unwrap();
        assert_eq!(dt.to_string(), "2021-11-07 00:00:00");
    }

    #[test]
    fn test_parse_datetime_invalid() {
        let result = parse_datetime("not-a-date");
        assert!(matches!(result, Err(AppError::UnprocessableEntity(_))));
    }

    #[test]
    fn test_validate_limit_default() {
        assert_eq!(validate_limit(None).unwrap(), 1000);
    }

    #[test]
    fn test_validate_limit_valid() {
        assert_eq!(validate_limit(Some(5)).unwrap(), 5);
        assert_eq!(validate_limit(Some(10000)).unwrap(), 10000);
    }

    #[test]
    fn test_validate_limit_invalid() {
        assert!(validate_limit(Some(0)).is_err());
        assert!(validate_limit(Some(10001)).is_err());
        assert!(validate_limit(Some(-1)).is_err());
    }

    #[test]
    fn test_validate_offset_default() {
        assert_eq!(validate_offset(None).unwrap(), 0);
    }

    #[test]
    fn test_validate_offset_valid() {
        assert_eq!(validate_offset(Some(0)).unwrap(), 0);
        assert_eq!(validate_offset(Some(100)).unwrap(), 100);
    }

    #[test]
    fn test_validate_offset_invalid() {
        assert!(validate_offset(Some(-1)).is_err());
    }
}
