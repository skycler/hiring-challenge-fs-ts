use crate::models::{Asset, MeasurementRow, Signal};

pub mod filesystem;
#[cfg(test)]
pub mod stub;

/// Abstract data provider interface.
/// Providers return complete datasets. Filtering/indexing is the service layer's job.
pub trait DataProvider: Send + Sync {
    fn load_assets(&self) -> Result<Vec<Asset>, String>;
    fn load_signals(&self) -> Result<Vec<Signal>, String>;
    fn load_measurements(&self) -> Result<Vec<MeasurementRow>, String>;
}
