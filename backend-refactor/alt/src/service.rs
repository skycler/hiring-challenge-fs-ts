use std::collections::HashMap;
use std::sync::Arc;

use chrono::NaiveDateTime;
use tracing::info;

use crate::errors::AppError;
use crate::models::{
    Asset, FlatMeasurementList, Measurement, MeasurementList, MeasurementRow, Signal, SignalStats,
};
use crate::provider::DataProvider;

/// Core service layer holding cached data and measurement index.
pub struct AssetService {
    assets: Vec<Asset>,
    signals: Vec<Signal>,
    /// Measurements indexed by signal_id, sorted by timestamp within each group.
    measurement_index: HashMap<i64, Vec<MeasurementRow>>,
    /// Set of known signal IDs for O(1) existence checks.
    signal_ids: std::collections::HashSet<i64>,
    /// Set of known asset IDs for O(1) existence checks.
    asset_ids: std::collections::HashSet<i64>,
}

impl AssetService {
    /// Create a new service by loading all data from the provider and building indexes.
    /// This is the eager cache warming step.
    pub fn new(provider: Arc<dyn DataProvider>) -> Result<Self, String> {
        let assets = provider.load_assets()?;
        let signals = provider.load_signals()?;
        let measurements = provider.load_measurements()?;

        let asset_ids: std::collections::HashSet<i64> =
            assets.iter().map(|a| a.asset_id).collect();
        let signal_ids: std::collections::HashSet<i64> =
            signals.iter().map(|s| s.signal_id).collect();

        // Build measurement index: group by signal_id, sort by timestamp
        let mut measurement_index: HashMap<i64, Vec<MeasurementRow>> = HashMap::new();
        for m in measurements {
            measurement_index
                .entry(m.signal_id)
                .or_default()
                .push(m);
        }
        // Sort each group by timestamp for efficient binary search
        for group in measurement_index.values_mut() {
            group.sort_by_key(|m| m.timestamp);
        }

        info!(
            assets = assets.len(),
            signals = signals.len(),
            measurement_signals = measurement_index.len(),
            "Service initialized with cached data and indexes"
        );

        Ok(Self {
            assets,
            signals,
            measurement_index,
            signal_ids,
            asset_ids,
        })
    }

    // -----------------------------------------------------------------------
    // Asset operations
    // -----------------------------------------------------------------------

    pub fn get_all_assets(&self) -> Vec<Asset> {
        self.assets.clone()
    }

    pub fn get_signals_for_asset(&self, asset_id: i64) -> Result<Vec<Signal>, AppError> {
        if !self.asset_ids.contains(&asset_id) {
            return Err(AppError::NotFound(format!("Asset {asset_id} not found")));
        }
        Ok(self
            .signals
            .iter()
            .filter(|s| s.asset_id == asset_id)
            .cloned()
            .collect())
    }

    // -----------------------------------------------------------------------
    // Signal operations
    // -----------------------------------------------------------------------

    pub fn get_all_signals(&self) -> Vec<Signal> {
        self.signals.clone()
    }

    pub fn get_signal(&self, signal_id: i64) -> Result<Signal, AppError> {
        self.signals
            .iter()
            .find(|s| s.signal_id == signal_id)
            .cloned()
            .ok_or_else(|| AppError::NotFound(format!("Signal {signal_id} not found")))
    }

    // -----------------------------------------------------------------------
    // Stats
    // -----------------------------------------------------------------------

    pub fn get_signal_stats(
        &self,
        signal_id: i64,
        from: NaiveDateTime,
        to: NaiveDateTime,
    ) -> Result<SignalStats, AppError> {
        // Check signal exists
        if !self.signal_ids.contains(&signal_id) {
            return Err(AppError::NotFound(format!("Signal {signal_id} not found")));
        }

        // Validate date range
        if from >= to {
            return Err(AppError::BadRequest(
                "Invalid date range: 'from' must be before 'to'".to_string(),
            ));
        }

        let filtered = self.filter_measurements_for_signal(signal_id, from, to);

        if filtered.is_empty() {
            return Ok(SignalStats {
                signal_id,
                from_date: from,
                to_date: to,
                count: 0,
                mean: None,
                min: None,
                max: None,
                median: None,
                std_dev: None,
            });
        }

        let values: Vec<f64> = filtered.iter().map(|m| m.value).collect();
        let count = values.len();
        let sum: f64 = values.iter().sum();
        let mean = sum / count as f64;
        let min = values.iter().cloned().fold(f64::INFINITY, f64::min);
        let max = values.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let median = compute_median(&values);
        let std_dev = if count == 1 {
            0.0
        } else {
            let variance = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (count - 1) as f64;
            variance.sqrt()
        };

        Ok(SignalStats {
            signal_id,
            from_date: from,
            to_date: to,
            count,
            mean: Some(round2(mean)),
            min: Some(round2(min)),
            max: Some(round2(max)),
            median: Some(round2(median)),
            std_dev: Some(round2(std_dev)),
        })
    }

    // -----------------------------------------------------------------------
    // Single-signal measurements
    // -----------------------------------------------------------------------

    pub fn get_signal_measurements(
        &self,
        signal_id: i64,
        from: NaiveDateTime,
        to: NaiveDateTime,
        limit: usize,
        offset: usize,
        format: &str,
    ) -> Result<serde_json::Value, AppError> {
        if !self.signal_ids.contains(&signal_id) {
            return Err(AppError::NotFound(format!("Signal {signal_id} not found")));
        }
        if from >= to {
            return Err(AppError::BadRequest(
                "Invalid date range: 'from' must be before 'to'".to_string(),
            ));
        }

        let filtered = self.filter_measurements_for_signal(signal_id, from, to);
        self.paginate_and_format(filtered, signal_id, limit, offset, format)
    }

    // -----------------------------------------------------------------------
    // Multi-signal measurements
    // -----------------------------------------------------------------------

    pub fn get_multi_signal_measurements(
        &self,
        signal_ids: &[i64],
        from: NaiveDateTime,
        to: NaiveDateTime,
        limit: usize,
        offset: usize,
        format: &str,
    ) -> Result<serde_json::Value, AppError> {
        // Check all signal IDs exist
        let unknown: Vec<i64> = signal_ids
            .iter()
            .filter(|id| !self.signal_ids.contains(id))
            .cloned()
            .collect();
        if !unknown.is_empty() {
            let ids_str = unknown
                .iter()
                .map(|id| id.to_string())
                .collect::<Vec<_>>()
                .join(", ");
            return Err(AppError::NotFound(format!(
                "Signal(s) not found: {ids_str}"
            )));
        }

        if from >= to {
            return Err(AppError::BadRequest(
                "Invalid date range: 'from' must be before 'to'".to_string(),
            ));
        }

        // Collect measurements from all requested signals
        let mut all_filtered: Vec<&MeasurementRow> = Vec::new();
        for &sid in signal_ids {
            let filtered = self.filter_measurements_for_signal(sid, from, to);
            all_filtered.extend(filtered);
        }
        // Sort combined results by timestamp for consistent ordering
        all_filtered.sort_by_key(|m| m.timestamp);

        let total = all_filtered.len();
        let page = all_filtered
            .into_iter()
            .skip(offset)
            .take(limit)
            .collect::<Vec<_>>();
        let count = page.len();

        if format == "flat" {
            let timestamps: Vec<String> = page
                .iter()
                .map(|m| m.timestamp.format("%Y-%m-%dT%H:%M:%S%.6f").to_string())
                .collect();
            let sig_ids: Vec<i64> = page.iter().map(|m| m.signal_id).collect();
            let values: Vec<f64> = page.iter().map(|m| m.value).collect();
            Ok(serde_json::to_value(FlatMeasurementList {
                total,
                count,
                limit,
                offset,
                timestamps,
                signal_ids: sig_ids,
                values,
            })
            .unwrap())
        } else {
            let measurements: Vec<Measurement> = page
                .iter()
                .map(|m| Measurement {
                    timestamp: m.timestamp,
                    signal_id: m.signal_id,
                    value: m.value,
                })
                .collect();
            Ok(serde_json::to_value(MeasurementList {
                total,
                count,
                limit,
                offset,
                measurements,
            })
            .unwrap())
        }
    }

    // -----------------------------------------------------------------------
    // Internal helpers
    // -----------------------------------------------------------------------

    /// Filter measurements for a single signal within [from, to] using binary search.
    fn filter_measurements_for_signal(
        &self,
        signal_id: i64,
        from: NaiveDateTime,
        to: NaiveDateTime,
    ) -> Vec<&MeasurementRow> {
        let Some(measurements) = self.measurement_index.get(&signal_id) else {
            return Vec::new();
        };

        // Binary search for the start: first index where timestamp >= from
        let start = measurements.partition_point(|m| m.timestamp < from);
        // Binary search for the end: first index where timestamp > to
        let end = measurements.partition_point(|m| m.timestamp <= to);

        if start >= end {
            return Vec::new();
        }

        measurements[start..end].iter().collect()
    }

    /// Paginate and format results for single-signal endpoints.
    fn paginate_and_format(
        &self,
        filtered: Vec<&MeasurementRow>,
        _signal_id: i64,
        limit: usize,
        offset: usize,
        format: &str,
    ) -> Result<serde_json::Value, AppError> {
        let total = filtered.len();
        let page = filtered
            .into_iter()
            .skip(offset)
            .take(limit)
            .collect::<Vec<_>>();
        let count = page.len();

        if format == "flat" {
            let timestamps: Vec<String> = page
                .iter()
                .map(|m| m.timestamp.format("%Y-%m-%dT%H:%M:%S%.6f").to_string())
                .collect();
            let signal_ids: Vec<i64> = page.iter().map(|m| m.signal_id).collect();
            let values: Vec<f64> = page.iter().map(|m| m.value).collect();
            Ok(serde_json::to_value(FlatMeasurementList {
                total,
                count,
                limit,
                offset,
                timestamps,
                signal_ids,
                values,
            })
            .unwrap())
        } else {
            let measurements: Vec<Measurement> = page
                .iter()
                .map(|m| Measurement {
                    timestamp: m.timestamp,
                    signal_id: m.signal_id,
                    value: m.value,
                })
                .collect();
            Ok(serde_json::to_value(MeasurementList {
                total,
                count,
                limit,
                offset,
                measurements,
            })
            .unwrap())
        }
    }
}

/// Compute the median of a non-empty slice of f64.
fn compute_median(values: &[f64]) -> f64 {
    let mut sorted = values.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let n = sorted.len();
    if n % 2 == 1 {
        sorted[n / 2]
    } else {
        (sorted[n / 2 - 1] + sorted[n / 2]) / 2.0
    }
}

/// Round a float to 2 decimal places.
fn round2(val: f64) -> f64 {
    (val * 100.0).round() / 100.0
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::provider::stub::StubProvider;

    fn make_service() -> AssetService {
        let provider = Arc::new(StubProvider::default_test_data());
        AssetService::new(provider).unwrap()
    }

    fn dt(s: &str) -> NaiveDateTime {
        NaiveDateTime::parse_from_str(s, "%Y-%m-%d %H:%M:%S%.f").unwrap()
    }

    // -- Asset tests --

    #[test]
    fn test_get_all_assets() {
        let svc = make_service();
        let assets = svc.get_all_assets();
        assert_eq!(assets.len(), 2);
    }

    #[test]
    fn test_get_signals_for_asset() {
        let svc = make_service();
        let signals = svc.get_signals_for_asset(1).unwrap();
        assert_eq!(signals.len(), 1);
        assert_eq!(signals[0].signal_id, 100);
    }

    #[test]
    fn test_get_signals_for_asset_multiple() {
        let svc = make_service();
        let signals = svc.get_signals_for_asset(2).unwrap();
        assert_eq!(signals.len(), 2);
    }

    #[test]
    fn test_get_signals_for_nonexistent_asset() {
        let svc = make_service();
        let result = svc.get_signals_for_asset(999);
        assert!(matches!(result, Err(AppError::NotFound(_))));
    }

    // -- Signal tests --

    #[test]
    fn test_get_all_signals() {
        let svc = make_service();
        let signals = svc.get_all_signals();
        assert_eq!(signals.len(), 3);
    }

    #[test]
    fn test_get_signal() {
        let svc = make_service();
        let signal = svc.get_signal(100).unwrap();
        assert_eq!(signal.signal_id, 100);
        assert_eq!(signal.unit, "kV");
    }

    #[test]
    fn test_get_signal_not_found() {
        let svc = make_service();
        let result = svc.get_signal(999);
        assert!(matches!(result, Err(AppError::NotFound(_))));
    }

    // -- Stats tests --

    #[test]
    fn test_stats_with_data() {
        let svc = make_service();
        let from = dt("2021-11-07 09:00:00.000");
        let to = dt("2021-11-07 11:00:00.000");
        let stats = svc.get_signal_stats(100, from, to).unwrap();
        assert_eq!(stats.count, 10);
        assert!(stats.mean.is_some());
        assert!(stats.min.is_some());
        assert!(stats.max.is_some());
        assert!(stats.median.is_some());
        assert!(stats.std_dev.is_some());
    }

    #[test]
    fn test_stats_no_data() {
        let svc = make_service();
        let from = dt("2099-01-01 00:00:00.000");
        let to = dt("2099-12-31 00:00:00.000");
        let stats = svc.get_signal_stats(100, from, to).unwrap();
        assert_eq!(stats.count, 0);
        assert!(stats.mean.is_none());
        assert!(stats.min.is_none());
        assert!(stats.max.is_none());
        assert!(stats.median.is_none());
        assert!(stats.std_dev.is_none());
    }

    #[test]
    fn test_stats_single_value() {
        let svc = make_service();
        // Narrow window to get exactly 1 measurement
        let from = dt("2021-11-07 10:00:00.000");
        let to = dt("2021-11-07 10:00:00.001");
        let stats = svc.get_signal_stats(100, from, to).unwrap();
        assert_eq!(stats.count, 1);
        assert_eq!(stats.std_dev, Some(0.0));
    }

    #[test]
    fn test_stats_signal_not_found() {
        let svc = make_service();
        let from = dt("2021-11-07 09:00:00.000");
        let to = dt("2021-11-07 11:00:00.000");
        let result = svc.get_signal_stats(999, from, to);
        assert!(matches!(result, Err(AppError::NotFound(_))));
    }

    #[test]
    fn test_stats_reversed_dates() {
        let svc = make_service();
        let from = dt("2021-12-01 00:00:00.000");
        let to = dt("2021-11-01 00:00:00.000");
        let result = svc.get_signal_stats(100, from, to);
        assert!(matches!(result, Err(AppError::BadRequest(_))));
        if let Err(AppError::BadRequest(msg)) = result {
            assert!(msg.contains("date range"));
        }
    }

    #[test]
    fn test_stats_equal_dates() {
        let svc = make_service();
        let from = dt("2021-11-07 10:00:00.000");
        let to = dt("2021-11-07 10:00:00.000");
        let result = svc.get_signal_stats(100, from, to);
        assert!(matches!(result, Err(AppError::BadRequest(_))));
    }

    // -- Measurement tests --

    #[test]
    fn test_measurements_objects_format() {
        let svc = make_service();
        let from = dt("2021-11-07 09:00:00.000");
        let to = dt("2021-11-07 11:00:00.000");
        let result = svc
            .get_signal_measurements(100, from, to, 1000, 0, "objects")
            .unwrap();
        assert!(result.get("measurements").is_some());
        assert!(result.get("timestamps").is_none());
        assert_eq!(result["total"].as_u64().unwrap(), 10);
        assert_eq!(result["count"].as_u64().unwrap(), 10);
    }

    #[test]
    fn test_measurements_flat_format() {
        let svc = make_service();
        let from = dt("2021-11-07 09:00:00.000");
        let to = dt("2021-11-07 11:00:00.000");
        let result = svc
            .get_signal_measurements(100, from, to, 1000, 0, "flat")
            .unwrap();
        assert!(result.get("timestamps").is_some());
        assert!(result.get("signal_ids").is_some());
        assert!(result.get("values").is_some());
        assert!(result.get("measurements").is_none());
        let count = result["count"].as_u64().unwrap() as usize;
        assert_eq!(result["timestamps"].as_array().unwrap().len(), count);
        assert_eq!(result["signal_ids"].as_array().unwrap().len(), count);
        assert_eq!(result["values"].as_array().unwrap().len(), count);
    }

    #[test]
    fn test_measurements_pagination() {
        let svc = make_service();
        let from = dt("2021-11-07 09:00:00.000");
        let to = dt("2021-11-07 11:00:00.000");
        let result = svc
            .get_signal_measurements(100, from, to, 3, 2, "objects")
            .unwrap();
        assert_eq!(result["total"].as_u64().unwrap(), 10);
        assert_eq!(result["count"].as_u64().unwrap(), 3);
        assert_eq!(result["limit"].as_u64().unwrap(), 3);
        assert_eq!(result["offset"].as_u64().unwrap(), 2);
    }

    #[test]
    fn test_measurements_signal_not_found() {
        let svc = make_service();
        let from = dt("2021-11-07 09:00:00.000");
        let to = dt("2021-11-07 11:00:00.000");
        let result = svc.get_signal_measurements(999, from, to, 1000, 0, "objects");
        assert!(matches!(result, Err(AppError::NotFound(_))));
    }

    #[test]
    fn test_measurements_reversed_dates() {
        let svc = make_service();
        let from = dt("2021-12-01 00:00:00.000");
        let to = dt("2021-11-01 00:00:00.000");
        let result = svc.get_signal_measurements(100, from, to, 1000, 0, "objects");
        assert!(matches!(result, Err(AppError::BadRequest(_))));
    }

    // -- Multi-signal tests --

    #[test]
    fn test_multi_signal_measurements() {
        let svc = make_service();
        let from = dt("2021-11-07 09:00:00.000");
        let to = dt("2021-11-07 11:00:00.000");
        let result = svc
            .get_multi_signal_measurements(&[100, 200], from, to, 1000, 0, "objects")
            .unwrap();
        assert_eq!(result["total"].as_u64().unwrap(), 15);
    }

    #[test]
    fn test_multi_signal_unknown_ids() {
        let svc = make_service();
        let from = dt("2021-11-07 09:00:00.000");
        let to = dt("2021-11-07 11:00:00.000");
        let result = svc.get_multi_signal_measurements(&[100, 999], from, to, 1000, 0, "objects");
        assert!(matches!(result, Err(AppError::NotFound(_))));
        if let Err(AppError::NotFound(msg)) = result {
            assert!(msg.contains("999"));
        }
    }

    #[test]
    fn test_multi_signal_reversed_dates() {
        let svc = make_service();
        let from = dt("2021-12-01 00:00:00.000");
        let to = dt("2021-11-01 00:00:00.000");
        let result = svc.get_multi_signal_measurements(&[100], from, to, 1000, 0, "objects");
        assert!(matches!(result, Err(AppError::BadRequest(_))));
    }

    #[test]
    fn test_multi_signal_flat_format() {
        let svc = make_service();
        let from = dt("2021-11-07 09:00:00.000");
        let to = dt("2021-11-07 11:00:00.000");
        let result = svc
            .get_multi_signal_measurements(&[100, 200], from, to, 1000, 0, "flat")
            .unwrap();
        assert!(result.get("timestamps").is_some());
        assert!(result.get("measurements").is_none());
    }

    // -- Helper tests --

    #[test]
    fn test_compute_median_odd() {
        assert_eq!(compute_median(&[1.0, 2.0, 3.0]), 2.0);
    }

    #[test]
    fn test_compute_median_even() {
        assert_eq!(compute_median(&[1.0, 2.0, 3.0, 4.0]), 2.5);
    }

    #[test]
    fn test_compute_median_single() {
        assert_eq!(compute_median(&[42.0]), 42.0);
    }

    #[test]
    fn test_round2() {
        assert_eq!(round2(1.234), 1.23);
        assert_eq!(round2(1.235), 1.24);
        assert_eq!(round2(1.0), 1.0);
    }

    #[test]
    fn test_empty_signal_no_measurements() {
        let svc = make_service();
        // Signal 300 exists but has no measurements
        let from = dt("2021-11-07 09:00:00.000");
        let to = dt("2021-11-07 11:00:00.000");
        let result = svc
            .get_signal_measurements(300, from, to, 1000, 0, "objects")
            .unwrap();
        assert_eq!(result["total"].as_u64().unwrap(), 0);
        assert_eq!(result["count"].as_u64().unwrap(), 0);
    }

    #[test]
    fn test_pagination_beyond_total() {
        let svc = make_service();
        let from = dt("2021-11-07 09:00:00.000");
        let to = dt("2021-11-07 11:00:00.000");
        let result = svc
            .get_signal_measurements(100, from, to, 1000, 100, "objects")
            .unwrap();
        assert_eq!(result["total"].as_u64().unwrap(), 10);
        assert_eq!(result["count"].as_u64().unwrap(), 0);
    }

    #[test]
    fn test_multi_signal_pagination() {
        let svc = make_service();
        let from = dt("2021-11-07 09:00:00.000");
        let to = dt("2021-11-07 11:00:00.000");
        let result = svc
            .get_multi_signal_measurements(&[100, 200], from, to, 5, 3, "objects")
            .unwrap();
        assert_eq!(result["total"].as_u64().unwrap(), 15);
        assert_eq!(result["count"].as_u64().unwrap(), 5);
        assert_eq!(result["limit"].as_u64().unwrap(), 5);
        assert_eq!(result["offset"].as_u64().unwrap(), 3);
    }
}
