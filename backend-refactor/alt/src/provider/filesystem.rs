use std::fs;
use std::io::Read;
use std::path::PathBuf;

use chrono::NaiveDateTime;
use tracing::{debug, info};

use crate::models::{Asset, MeasurementRow, RawAsset, RawSignal, Signal};
use crate::provider::DataProvider;

const MAX_MEASUREMENT_ROWS: usize = 10_000_000;

/// Filesystem-based data provider that reads from JSON and CSV files.
pub struct FilesystemProvider {
    pub assets_path: PathBuf,
    pub signals_path: PathBuf,
    pub measurements_path: PathBuf,
}

impl FilesystemProvider {
    pub fn new(assets_path: PathBuf, signals_path: PathBuf, measurements_path: PathBuf) -> Self {
        Self {
            assets_path,
            signals_path,
            measurements_path,
        }
    }
}

impl DataProvider for FilesystemProvider {
    fn load_assets(&self) -> Result<Vec<Asset>, String> {
        let path = &self.assets_path;
        debug!("Loading assets from {}", path.display());

        let content = fs::read_to_string(path)
            .map_err(|e| format!("Failed to read assets file '{}': {}", path.display(), e))?;

        let raw: Vec<RawAsset> = serde_json::from_str(&content)
            .map_err(|e| format!("Failed to parse assets JSON: {e}"))?;

        let assets: Result<Vec<Asset>, String> = raw
            .into_iter()
            .map(|r| {
                Ok(Asset {
                    asset_id: r
                        .asset_id
                        .parse::<i64>()
                        .map_err(|e| format!("Invalid AssetID '{}': {e}", r.asset_id))?,
                    latitude: r
                        .latitude
                        .parse::<f64>()
                        .map_err(|e| format!("Invalid Latitude '{}': {e}", r.latitude))?,
                    longitude: r
                        .longitude
                        .parse::<f64>()
                        .map_err(|e| format!("Invalid Longitude '{}': {e}", r.longitude))?,
                    description: r.descri,
                })
            })
            .collect();

        let assets = assets?;
        info!(
            path = %path.display(),
            count = assets.len(),
            "Loaded assets"
        );
        Ok(assets)
    }

    fn load_signals(&self) -> Result<Vec<Signal>, String> {
        let path = &self.signals_path;
        debug!("Loading signals from {}", path.display());

        let content = fs::read_to_string(path)
            .map_err(|e| format!("Failed to read signals file '{}': {}", path.display(), e))?;

        let raw: Vec<RawSignal> = serde_json::from_str(&content)
            .map_err(|e| format!("Failed to parse signals JSON: {e}"))?;

        let signals: Result<Vec<Signal>, String> = raw
            .into_iter()
            .map(|r| {
                Ok(Signal {
                    signal_g_id: r.signal_g_id,
                    signal_id: r
                        .signal_id
                        .parse::<i64>()
                        .map_err(|e| format!("Invalid SignalId '{}': {e}", r.signal_id))?,
                    signal_name: r.signal_name,
                    asset_id: r
                        .asset_id
                        .parse::<i64>()
                        .map_err(|e| format!("Invalid AssetId '{}': {e}", r.asset_id))?,
                    unit: r.unit,
                })
            })
            .collect();

        let signals = signals?;
        info!(
            path = %path.display(),
            count = signals.len(),
            "Loaded signals"
        );
        Ok(signals)
    }

    fn load_measurements(&self) -> Result<Vec<MeasurementRow>, String> {
        let path = &self.measurements_path;
        debug!("Loading measurements from {}", path.display());

        // Read file handling BOM (UTF-8-sig)
        let mut file = fs::File::open(path)
            .map_err(|e| format!("Failed to open measurements file '{}': {}", path.display(), e))?;
        let mut raw_bytes = Vec::new();
        file.read_to_end(&mut raw_bytes)
            .map_err(|e| format!("Failed to read measurements file: {e}"))?;

        // Strip UTF-8 BOM if present
        let content = if raw_bytes.starts_with(&[0xEF, 0xBB, 0xBF]) {
            &raw_bytes[3..]
        } else {
            &raw_bytes[..]
        };

        let mut rdr = csv::ReaderBuilder::new()
            .delimiter(b'|')
            .has_headers(true)
            .from_reader(content);

        let mut measurements = Vec::new();

        for (idx, result) in rdr.records().enumerate() {
            if idx >= MAX_MEASUREMENT_ROWS {
                return Err(format!(
                    "Measurements file exceeds maximum row limit of {MAX_MEASUREMENT_ROWS}"
                ));
            }

            let record = result
                .map_err(|e| format!("Failed to parse CSV row {}: {e}", idx + 1))?;

            let ts_str = record
                .get(0)
                .ok_or_else(|| format!("Missing Ts column at row {}", idx + 1))?;
            let signal_id_str = record
                .get(1)
                .ok_or_else(|| format!("Missing SignalId column at row {}", idx + 1))?;
            let value_str = record
                .get(2)
                .ok_or_else(|| format!("Missing MeasurementValue column at row {}", idx + 1))?;

            let timestamp = NaiveDateTime::parse_from_str(ts_str, "%Y-%m-%d %H:%M:%S%.f")
                .map_err(|e| format!("Invalid timestamp '{}' at row {}: {e}", ts_str, idx + 1))?;

            let signal_id: i64 = signal_id_str.parse().map_err(|e| {
                format!(
                    "Invalid SignalId '{}' at row {}: {e}",
                    signal_id_str,
                    idx + 1
                )
            })?;

            // European comma notation: replace ',' with '.'
            let value_normalized = value_str.replace(',', ".");
            let value: f64 = value_normalized.parse().map_err(|e| {
                format!(
                    "Invalid MeasurementValue '{}' at row {}: {e}",
                    value_str,
                    idx + 1
                )
            })?;

            measurements.push(MeasurementRow {
                timestamp,
                signal_id,
                value,
            });
        }

        info!(
            path = %path.display(),
            count = measurements.len(),
            "Loaded measurements"
        );
        Ok(measurements)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn test_load_assets_valid() {
        let dir = std::env::temp_dir().join("test_assets_valid");
        let _ = fs::create_dir_all(&dir);
        let path = dir.join("assets.json");
        let mut f = fs::File::create(&path).unwrap();
        write!(
            f,
            r#"[{{"AssetID":"1","Latitude":"47.5","Longitude":"8.2","descri":"Test"}}]"#
        )
        .unwrap();

        let provider = FilesystemProvider::new(
            path.clone(),
            dir.join("dummy.json"),
            dir.join("dummy.csv"),
        );
        let assets = provider.load_assets().unwrap();
        assert_eq!(assets.len(), 1);
        assert_eq!(assets[0].asset_id, 1);
        assert!((assets[0].latitude - 47.5).abs() < 0.01);
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_load_assets_missing_file() {
        let provider = FilesystemProvider::new(
            PathBuf::from("/nonexistent/assets.json"),
            PathBuf::from("/nonexistent/signals.json"),
            PathBuf::from("/nonexistent/measurements.csv"),
        );
        let result = provider.load_assets();
        assert!(result.is_err());
    }

    #[test]
    fn test_load_signals_valid() {
        let dir = std::env::temp_dir().join("test_signals_valid");
        let _ = fs::create_dir_all(&dir);
        let path = dir.join("signal.json");
        let mut f = fs::File::create(&path).unwrap();
        write!(
            f,
            r#"[{{"SignalGId":"abc-def","SignalId":"100","SignalName":"SIG1","AssetId":"1","Unit":"kV"}}]"#
        )
        .unwrap();

        let provider = FilesystemProvider::new(
            dir.join("dummy.json"),
            path.clone(),
            dir.join("dummy.csv"),
        );
        let signals = provider.load_signals().unwrap();
        assert_eq!(signals.len(), 1);
        assert_eq!(signals[0].signal_id, 100);
        assert_eq!(signals[0].unit, "kV");
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_load_measurements_european_decimal() {
        let dir = std::env::temp_dir().join("test_meas_euro");
        let _ = fs::create_dir_all(&dir);
        let path = dir.join("measurements.csv");
        let mut f = fs::File::create(&path).unwrap();
        // Write BOM + content
        f.write_all(&[0xEF, 0xBB, 0xBF]).unwrap();
        write!(
            f,
            "Ts|SignalId|MeasurementValue\n2021-11-07 23:59:03.762|427038|116,129\n"
        )
        .unwrap();

        let provider = FilesystemProvider::new(
            dir.join("dummy.json"),
            dir.join("dummy.json"),
            path.clone(),
        );
        let measurements = provider.load_measurements().unwrap();
        assert_eq!(measurements.len(), 1);
        assert_eq!(measurements[0].signal_id, 427038);
        assert!((measurements[0].value - 116.129).abs() < 0.001);
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_load_measurements_missing_file() {
        let provider = FilesystemProvider::new(
            PathBuf::from("/tmp/d.json"),
            PathBuf::from("/tmp/d.json"),
            PathBuf::from("/nonexistent/measurements.csv"),
        );
        let result = provider.load_measurements();
        assert!(result.is_err());
    }

    #[test]
    fn test_load_measurements_no_bom() {
        let dir = std::env::temp_dir().join("test_meas_nobom");
        let _ = fs::create_dir_all(&dir);
        let path = dir.join("measurements.csv");
        let mut f = fs::File::create(&path).unwrap();
        write!(
            f,
            "Ts|SignalId|MeasurementValue\n2021-11-07 23:59:03.762|427038|116.129\n"
        )
        .unwrap();

        let provider = FilesystemProvider::new(
            dir.join("d.json"),
            dir.join("d.json"),
            path.clone(),
        );
        let measurements = provider.load_measurements().unwrap();
        assert_eq!(measurements.len(), 1);
        // Value with '.' should also work (no comma)
        assert!((measurements[0].value - 116.129).abs() < 0.001);
        let _ = fs::remove_dir_all(&dir);
    }
}
