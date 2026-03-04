use chrono::NaiveDateTime;
use serde::{Deserialize, Serialize};
use utoipa::ToSchema;

/// Custom serializer for NaiveDateTime that always outputs microsecond precision.
pub mod datetime_format {
    use chrono::NaiveDateTime;
    use serde::{self, Deserialize, Deserializer, Serializer};

    const FORMAT: &str = "%Y-%m-%dT%H:%M:%S%.6f";

    pub fn serialize<S>(date: &NaiveDateTime, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        let s = date.format(FORMAT).to_string();
        serializer.serialize_str(&s)
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<NaiveDateTime, D::Error>
    where
        D: Deserializer<'de>,
    {
        let s = String::deserialize(deserializer)?;
        NaiveDateTime::parse_from_str(&s, FORMAT).map_err(serde::de::Error::custom)
    }
}

/// Custom serializer for NaiveDateTime used in stats (no fractional seconds).
pub mod datetime_format_stats {
    use chrono::NaiveDateTime;
    use serde::{self, Deserialize, Deserializer, Serializer};

    const FORMAT: &str = "%Y-%m-%dT%H:%M:%S";

    pub fn serialize<S>(date: &NaiveDateTime, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        let s = date.format(FORMAT).to_string();
        serializer.serialize_str(&s)
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<NaiveDateTime, D::Error>
    where
        D: Deserializer<'de>,
    {
        let s = String::deserialize(deserializer)?;
        NaiveDateTime::parse_from_str(&s, FORMAT).map_err(serde::de::Error::custom)
    }
}

// ---------------------------------------------------------------------------
// Domain Models
// ---------------------------------------------------------------------------

/// A physical installation (electrical substation) with a geographic location.
#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct Asset {
    pub asset_id: i64,
    pub latitude: f64,
    pub longitude: f64,
    pub description: String,
}

/// A named measurement channel belonging to exactly one asset.
#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct Signal {
    pub signal_g_id: String,
    pub signal_id: i64,
    pub signal_name: String,
    pub asset_id: i64,
    pub unit: String,
}

/// A single timestamped reading from a signal.
#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct Measurement {
    #[serde(with = "datetime_format")]
    #[schema(value_type = String, example = "2021-11-07T23:59:03.762000")]
    pub timestamp: NaiveDateTime,
    pub signal_id: i64,
    pub value: f64,
}

/// Lightweight in-memory representation of a measurement (for provider layer).
#[derive(Debug, Clone)]
pub struct MeasurementRow {
    pub timestamp: NaiveDateTime,
    pub signal_id: i64,
    pub value: f64,
}

/// Computed aggregate statistics for a signal over a time range.
#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct SignalStats {
    pub signal_id: i64,
    #[serde(with = "datetime_format_stats")]
    #[schema(value_type = String)]
    pub from_date: NaiveDateTime,
    #[serde(with = "datetime_format_stats")]
    #[schema(value_type = String)]
    pub to_date: NaiveDateTime,
    pub count: usize,
    pub mean: Option<f64>,
    pub min: Option<f64>,
    pub max: Option<f64>,
    pub median: Option<f64>,
    pub std_dev: Option<f64>,
}

/// Paginated measurement list in objects format.
#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct MeasurementList {
    pub total: usize,
    pub count: usize,
    pub limit: usize,
    pub offset: usize,
    pub measurements: Vec<Measurement>,
}

/// Paginated measurement list in flat/columnar format.
#[derive(Debug, Clone, Serialize, Deserialize, ToSchema)]
pub struct FlatMeasurementList {
    pub total: usize,
    pub count: usize,
    pub limit: usize,
    pub offset: usize,
    #[schema(value_type = Vec<String>)]
    pub timestamps: Vec<String>,
    pub signal_ids: Vec<i64>,
    pub values: Vec<f64>,
}

// ---------------------------------------------------------------------------
// Source file deserialization models (PascalCase keys from JSON/CSV)
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize)]
pub struct RawAsset {
    #[serde(rename = "AssetID")]
    pub asset_id: String,
    #[serde(rename = "Latitude")]
    pub latitude: String,
    #[serde(rename = "Longitude")]
    pub longitude: String,
    pub descri: String,
}

#[derive(Debug, Deserialize)]
pub struct RawSignal {
    #[serde(rename = "SignalGId")]
    pub signal_g_id: String,
    #[serde(rename = "SignalId")]
    pub signal_id: String,
    #[serde(rename = "SignalName")]
    pub signal_name: String,
    #[serde(rename = "AssetId")]
    pub asset_id: String,
    #[serde(rename = "Unit")]
    pub unit: String,
}

/// Error response body.
#[derive(Debug, Serialize, Deserialize, ToSchema)]
pub struct ErrorResponse {
    pub detail: String,
}
