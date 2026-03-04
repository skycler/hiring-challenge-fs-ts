use std::sync::Arc;

use axum::extract::{Path, State};
use axum::Json;

use crate::errors::AppError;
use crate::models::{Asset, Signal};
use crate::service::AssetService;

/// GET /assets
#[utoipa::path(
    get,
    path = "/assets",
    responses(
        (status = 200, description = "All assets", body = Vec<Asset>)
    )
)]
pub async fn get_assets(
    State(service): State<Arc<AssetService>>,
) -> Json<Vec<Asset>> {
    Json(service.get_all_assets())
}

/// GET /assets/{asset_id}/signals
#[utoipa::path(
    get,
    path = "/assets/{asset_id}/signals",
    params(
        ("asset_id" = i64, Path, description = "Asset ID")
    ),
    responses(
        (status = 200, description = "Signals for asset", body = Vec<Signal>),
        (status = 404, description = "Asset not found")
    )
)]
pub async fn get_asset_signals(
    State(service): State<Arc<AssetService>>,
    Path(asset_id): Path<i64>,
) -> Result<Json<Vec<Signal>>, AppError> {
    let signals = service.get_signals_for_asset(asset_id)?;
    Ok(Json(signals))
}
