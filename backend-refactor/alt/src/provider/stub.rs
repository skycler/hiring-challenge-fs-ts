use chrono::NaiveDateTime;

use crate::models::{Asset, MeasurementRow, Signal};
use crate::provider::DataProvider;

/// In-memory stub provider for unit testing.
pub struct StubProvider {
    pub assets: Vec<Asset>,
    pub signals: Vec<Signal>,
    pub measurements: Vec<MeasurementRow>,
}

impl StubProvider {
    /// Create a stub with default test data.
    pub fn default_test_data() -> Self {
        let assets = vec![
            Asset {
                asset_id: 1,
                latitude: 47.5568277613,
                longitude: 8.2338560914,
                description: "UW Beznau".to_string(),
            },
            Asset {
                asset_id: 2,
                latitude: 47.219215463,
                longitude: 8.9728980141,
                description: "UW Grynau".to_string(),
            },
        ];

        let signals = vec![
            Signal {
                signal_g_id: "045ad75f-d8c7-4c92-b252-05f515e4006f".to_string(),
                signal_id: 100,
                signal_name: "SIG_100".to_string(),
                asset_id: 1,
                unit: "kV".to_string(),
            },
            Signal {
                signal_g_id: "beb78c41-96a9-48f8-b77f-62f21366814a".to_string(),
                signal_id: 200,
                signal_name: "SIG_200".to_string(),
                asset_id: 2,
                unit: "kW".to_string(),
            },
            Signal {
                signal_g_id: "566a7ca6-d9d0-463d-829c-cd9a2d9e4f2f".to_string(),
                signal_id: 300,
                signal_name: "SIG_300".to_string(),
                asset_id: 2,
                unit: "kV".to_string(),
            },
        ];

        let base = NaiveDateTime::parse_from_str(
            "2021-11-07 10:00:00.000",
            "%Y-%m-%d %H:%M:%S%.f",
        )
        .unwrap();

        let mut measurements = Vec::new();
        // Signal 100: 10 measurements
        for i in 0..10 {
            measurements.push(MeasurementRow {
                timestamp: base + chrono::Duration::minutes(i),
                signal_id: 100,
                value: 100.0 + i as f64,
            });
        }
        // Signal 200: 5 measurements
        for i in 0..5 {
            measurements.push(MeasurementRow {
                timestamp: base + chrono::Duration::minutes(i * 2),
                signal_id: 200,
                value: 200.0 + i as f64,
            });
        }
        // Signal 300: 0 measurements (empty signal)

        Self {
            assets,
            signals,
            measurements,
        }
    }

    /// Create an empty stub.
    pub fn empty() -> Self {
        Self {
            assets: vec![],
            signals: vec![],
            measurements: vec![],
        }
    }
}

impl DataProvider for StubProvider {
    fn load_assets(&self) -> Result<Vec<Asset>, String> {
        Ok(self.assets.clone())
    }

    fn load_signals(&self) -> Result<Vec<Signal>, String> {
        Ok(self.signals.clone())
    }

    fn load_measurements(&self) -> Result<Vec<MeasurementRow>, String> {
        Ok(self.measurements.clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_stub_default_data() {
        let stub = StubProvider::default_test_data();
        assert_eq!(stub.load_assets().unwrap().len(), 2);
        assert_eq!(stub.load_signals().unwrap().len(), 3);
        assert_eq!(stub.load_measurements().unwrap().len(), 15);
    }

    #[test]
    fn test_stub_empty() {
        let stub = StubProvider::empty();
        assert_eq!(stub.load_assets().unwrap().len(), 0);
        assert_eq!(stub.load_signals().unwrap().len(), 0);
        assert_eq!(stub.load_measurements().unwrap().len(), 0);
    }
}
