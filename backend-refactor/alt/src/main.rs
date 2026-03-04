use std::sync::Arc;

use axum::routing::get;
use axum::Router;
use tracing::{error, info, warn};
use utoipa::OpenApi;

mod config;
mod errors;
mod models;
mod provider;
mod routes;
mod service;

use config::AppConfig;
use provider::filesystem::FilesystemProvider;
use provider::DataProvider;
use service::AssetService;

#[derive(OpenApi)]
#[openapi(
    paths(
        routes::health::health_check,
        routes::assets::get_assets,
        routes::assets::get_asset_signals,
        routes::signals::get_signals,
        routes::signals::get_signal,
        routes::signals::get_signal_stats,
        routes::signals::get_signal_measurements,
        routes::measurements::get_measurements,
    ),
    components(schemas(
        models::Asset,
        models::Signal,
        models::Measurement,
        models::SignalStats,
        models::MeasurementList,
        models::FlatMeasurementList,
        models::ErrorResponse,
    ))
)]
struct ApiDoc;

/// Build the application (used by both main and tests).
pub fn build_app(service: Arc<AssetService>, debug: bool) -> Router {
    let mut app = Router::new()
        .route("/health", get(routes::health::health_check))
        .route("/assets", get(routes::assets::get_assets))
        .route(
            "/assets/{asset_id}/signals",
            get(routes::assets::get_asset_signals),
        )
        .route("/signals", get(routes::signals::get_signals))
        .route("/signals/{signal_id}", get(routes::signals::get_signal))
        .route(
            "/signals/{signal_id}/stats",
            get(routes::signals::get_signal_stats),
        )
        .route(
            "/signals/{signal_id}/measurements",
            get(routes::signals::get_signal_measurements),
        )
        .route("/measurements", get(routes::measurements::get_measurements))
        .with_state(service);

    // Only enable OpenAPI/Swagger in debug mode
    if debug {
        app = app.merge(
            utoipa_swagger_ui::SwaggerUi::new("/docs")
                .url("/openapi.json", ApiDoc::openapi()),
        );
    }

    app
}

#[tokio::main]
async fn main() {
    // Load .env file (ignore if missing)
    let _ = dotenvy::dotenv();

    // Load configuration
    let config = match AppConfig::from_env() {
        Ok(cfg) => cfg,
        Err(e) => {
            eprintln!("Configuration error: {e}");
            std::process::exit(1);
        }
    };

    // Initialize logging
    let log_level = if config.debug { "debug" } else { "info" };
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new(log_level)),
        )
        .init();

    info!(
        app_name = %config.app_name,
        version = %config.api_version,
        debug = config.debug,
        "Starting application"
    );

    if config.debug {
        warn!("Debug mode is enabled. Do not use in production!");
    }

    // Create filesystem provider
    let provider: Arc<dyn DataProvider> = Arc::new(FilesystemProvider::new(
        config.assets_path.clone(),
        config.signals_path.clone(),
        config.measurements_path.clone(),
    ));

    // Eagerly initialize service (cache warming)
    let service = match AssetService::new(provider) {
        Ok(svc) => Arc::new(svc),
        Err(e) => {
            error!("Failed to initialize service: {e}");
            std::process::exit(1);
        }
    };

    info!("All data loaded and indexed successfully");

    // Build the application
    let app = build_app(service, config.debug);

    // Start the server
    let listener = tokio::net::TcpListener::bind("0.0.0.0:8000")
        .await
        .expect("Failed to bind to port 8000");

    info!("Listening on 0.0.0.0:8000");

    axum::serve(listener, app)
        .await
        .expect("Server error");
}

// ---------------------------------------------------------------------------
// Integration-style tests using the test client
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use http_body_util::BodyExt;
    use provider::stub::StubProvider;
    use tower::ServiceExt;

    fn test_service() -> Arc<AssetService> {
        let provider = Arc::new(StubProvider::default_test_data());
        Arc::new(AssetService::new(provider).unwrap())
    }

    fn test_app() -> Router {
        build_app(test_service(), true)
    }

    async fn get_json(app: Router, uri: &str) -> (StatusCode, serde_json::Value) {
        let resp = app
            .oneshot(
                Request::builder()
                    .uri(uri)
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        let status = resp.status();
        let bytes = resp.into_body().collect().await.unwrap().to_bytes();
        let body: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        (status, body)
    }

    // -- Health --

    #[tokio::test]
    async fn test_health() {
        let (status, body) = get_json(test_app(), "/health").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body["status"], "ok");
    }

    // -- Assets --

    #[tokio::test]
    async fn test_get_assets() {
        let (status, body) = get_json(test_app(), "/assets").await;
        assert_eq!(status, StatusCode::OK);
        let arr = body.as_array().unwrap();
        assert_eq!(arr.len(), 2);
        assert!(arr[0].get("asset_id").is_some());
        assert!(arr[0].get("latitude").is_some());
        assert!(arr[0].get("longitude").is_some());
        assert!(arr[0].get("description").is_some());
    }

    #[tokio::test]
    async fn test_get_asset_signals() {
        let (status, body) = get_json(test_app(), "/assets/1/signals").await;
        assert_eq!(status, StatusCode::OK);
        let arr = body.as_array().unwrap();
        assert_eq!(arr.len(), 1);
        assert_eq!(arr[0]["asset_id"], 1);
    }

    #[tokio::test]
    async fn test_get_asset_signals_multiple() {
        let (status, body) = get_json(test_app(), "/assets/2/signals").await;
        assert_eq!(status, StatusCode::OK);
        let arr = body.as_array().unwrap();
        assert_eq!(arr.len(), 2);
    }

    #[tokio::test]
    async fn test_get_asset_signals_not_found() {
        let (status, body) = get_json(test_app(), "/assets/999/signals").await;
        assert_eq!(status, StatusCode::NOT_FOUND);
        assert!(body["detail"].as_str().unwrap().contains("999"));
    }

    // -- Signals --

    #[tokio::test]
    async fn test_get_signals() {
        let (status, body) = get_json(test_app(), "/signals").await;
        assert_eq!(status, StatusCode::OK);
        let arr = body.as_array().unwrap();
        assert_eq!(arr.len(), 3);
        assert!(arr[0].get("signal_g_id").is_some());
        assert!(arr[0].get("signal_id").is_some());
        assert!(arr[0].get("signal_name").is_some());
        assert!(arr[0].get("asset_id").is_some());
        assert!(arr[0].get("unit").is_some());
    }

    #[tokio::test]
    async fn test_get_signal() {
        let (status, body) = get_json(test_app(), "/signals/100").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body["signal_id"], 100);
        assert_eq!(body["unit"], "kV");
        assert_eq!(body["asset_id"], 1);
    }

    #[tokio::test]
    async fn test_get_signal_not_found() {
        let (status, body) = get_json(test_app(), "/signals/999999").await;
        assert_eq!(status, StatusCode::NOT_FOUND);
        assert!(body["detail"].as_str().unwrap().contains("999999"));
    }

    // -- Signal Stats --

    #[tokio::test]
    async fn test_get_stats() {
        let (status, body) = get_json(
            test_app(),
            "/signals/100/stats?from=2021-11-07T00:00:00&to=2021-12-01T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body["signal_id"], 100);
        assert!(body["count"].as_u64().unwrap() > 0);
        assert!(body["mean"].is_number());
        assert!(body["min"].is_number());
        assert!(body["max"].is_number());
        assert!(body["median"].is_number());
        assert!(body["std_dev"].is_number());
    }

    #[tokio::test]
    async fn test_get_stats_no_data() {
        let (status, body) = get_json(
            test_app(),
            "/signals/100/stats?from=2099-01-01T00:00:00&to=2099-12-31T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body["count"], 0);
        assert!(body["mean"].is_null());
        assert!(body["min"].is_null());
        assert!(body["max"].is_null());
        assert!(body["median"].is_null());
        assert!(body["std_dev"].is_null());
    }

    #[tokio::test]
    async fn test_get_stats_not_found() {
        let (status, _body) = get_json(
            test_app(),
            "/signals/999/stats?from=2021-11-07T00:00:00&to=2021-12-01T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn test_get_stats_reversed_dates() {
        let (status, body) = get_json(
            test_app(),
            "/signals/100/stats?from=2021-12-01T00:00:00&to=2021-11-01T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::BAD_REQUEST);
        assert!(body["detail"].as_str().unwrap().contains("date range"));
    }

    #[tokio::test]
    async fn test_get_stats_missing_params() {
        let (status, _body) = get_json(test_app(), "/signals/100/stats").await;
        assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    }

    #[tokio::test]
    async fn test_get_stats_missing_to() {
        let (status, _body) = get_json(
            test_app(),
            "/signals/100/stats?from=2021-11-07T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    }

    // -- Signal Measurements --

    #[tokio::test]
    async fn test_get_signal_measurements_default() {
        let (status, body) = get_json(
            test_app(),
            "/signals/100/measurements?from=2021-11-07T00:00:00&to=2021-12-01T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body["limit"], 1000);
        assert_eq!(body["offset"], 0);
        assert!(body["total"].as_u64().unwrap() > 0);
        assert!(body.get("measurements").is_some());
        let measurements = body["measurements"].as_array().unwrap();
        assert_eq!(measurements.len(), body["count"].as_u64().unwrap() as usize);
    }

    #[tokio::test]
    async fn test_get_signal_measurements_pagination() {
        let (status, body) = get_json(
            test_app(),
            "/signals/100/measurements?from=2021-11-07T00:00:00&to=2021-12-01T00:00:00&limit=3&offset=2",
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body["limit"], 3);
        assert_eq!(body["offset"], 2);
        assert_eq!(body["count"], 3);
    }

    #[tokio::test]
    async fn test_get_signal_measurements_flat() {
        let (status, body) = get_json(
            test_app(),
            "/signals/100/measurements?from=2021-11-07T00:00:00&to=2021-12-01T00:00:00&format=flat",
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert!(body.get("timestamps").is_some());
        assert!(body.get("signal_ids").is_some());
        assert!(body.get("values").is_some());
        assert!(body.get("measurements").is_none());
        let count = body["count"].as_u64().unwrap() as usize;
        assert_eq!(body["timestamps"].as_array().unwrap().len(), count);
        assert_eq!(body["signal_ids"].as_array().unwrap().len(), count);
        assert_eq!(body["values"].as_array().unwrap().len(), count);
        // All signal_ids should be 100
        for sid in body["signal_ids"].as_array().unwrap() {
            assert_eq!(sid, 100);
        }
    }

    #[tokio::test]
    async fn test_get_signal_measurements_objects_explicit() {
        let (status, body) = get_json(
            test_app(),
            "/signals/100/measurements?from=2021-11-07T00:00:00&to=2021-12-01T00:00:00&format=objects",
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert!(body.get("measurements").is_some());
        assert!(body.get("timestamps").is_none());
        assert!(body.get("signal_ids").is_none());
        assert!(body.get("values").is_none());
    }

    #[tokio::test]
    async fn test_get_signal_measurements_invalid_format() {
        let (status, _body) = get_json(
            test_app(),
            "/signals/100/measurements?from=2021-11-07T00:00:00&to=2021-12-01T00:00:00&format=invalid",
        )
        .await;
        assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    }

    #[tokio::test]
    async fn test_get_signal_measurements_not_found() {
        let (status, _body) = get_json(
            test_app(),
            "/signals/999/measurements?from=2021-11-07T00:00:00&to=2021-12-01T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::NOT_FOUND);
    }

    #[tokio::test]
    async fn test_get_signal_measurements_reversed_dates() {
        let (status, _body) = get_json(
            test_app(),
            "/signals/100/measurements?from=2021-12-01T00:00:00&to=2021-11-01T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn test_get_signal_measurements_missing_params() {
        let (status, _body) = get_json(test_app(), "/signals/100/measurements").await;
        assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    }

    // -- Multi-signal Measurements --

    #[tokio::test]
    async fn test_get_measurements_multi() {
        let (status, body) = get_json(
            test_app(),
            "/measurements?signal_ids=100,200&from=2021-11-07T00:00:00&to=2021-12-01T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body["total"], 15);
        assert!(body.get("measurements").is_some());
    }

    #[tokio::test]
    async fn test_get_measurements_pagination() {
        let (status, body) = get_json(
            test_app(),
            "/measurements?signal_ids=100,200&from=2021-11-07T00:00:00&to=2021-12-01T00:00:00&limit=3&offset=0",
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body["count"], 3);
        assert_eq!(body["limit"], 3);
    }

    #[tokio::test]
    async fn test_get_measurements_unknown_signal() {
        let (status, body) = get_json(
            test_app(),
            "/measurements?signal_ids=999&from=2021-11-07T00:00:00&to=2021-12-01T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::NOT_FOUND);
        assert!(body["detail"].as_str().unwrap().contains("999"));
    }

    #[tokio::test]
    async fn test_get_measurements_mix_known_unknown() {
        let (status, body) = get_json(
            test_app(),
            "/measurements?signal_ids=100,999&from=2021-11-07T00:00:00&to=2021-12-01T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::NOT_FOUND);
        assert!(body["detail"].as_str().unwrap().contains("999"));
    }

    #[tokio::test]
    async fn test_get_measurements_non_integer() {
        let (status, body) = get_json(
            test_app(),
            "/measurements?signal_ids=abc&from=2021-11-07T00:00:00&to=2021-12-01T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::BAD_REQUEST);
        assert!(body["detail"].as_str().unwrap().contains("integers"));
    }

    #[tokio::test]
    async fn test_get_measurements_empty_signal_ids() {
        let (status, body) = get_json(
            test_app(),
            "/measurements?signal_ids=&from=2021-11-07T00:00:00&to=2021-12-01T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::BAD_REQUEST);
        assert!(body["detail"].as_str().unwrap().contains("required"));
    }

    #[tokio::test]
    async fn test_get_measurements_reversed_dates() {
        let (status, body) = get_json(
            test_app(),
            "/measurements?signal_ids=100&from=2021-12-01T00:00:00&to=2021-11-01T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::BAD_REQUEST);
        assert!(body["detail"].as_str().unwrap().contains("date range"));
    }

    #[tokio::test]
    async fn test_get_measurements_missing_signal_ids() {
        let (status, _body) = get_json(
            test_app(),
            "/measurements?from=2021-11-07T00:00:00&to=2021-12-01T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    }

    #[tokio::test]
    async fn test_get_measurements_missing_dates() {
        let (status, _body) = get_json(
            test_app(),
            "/measurements?signal_ids=100",
        )
        .await;
        assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    }

    #[tokio::test]
    async fn test_get_measurements_flat() {
        let (status, body) = get_json(
            test_app(),
            "/measurements?signal_ids=100,200&from=2021-11-07T00:00:00&to=2021-12-01T00:00:00&format=flat",
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert!(body.get("timestamps").is_some());
        assert!(body.get("signal_ids").is_some());
        assert!(body.get("values").is_some());
        assert!(body.get("measurements").is_none());
        let count = body["count"].as_u64().unwrap() as usize;
        assert_eq!(body["timestamps"].as_array().unwrap().len(), count);
    }

    #[tokio::test]
    async fn test_get_measurements_objects_explicit() {
        let (status, body) = get_json(
            test_app(),
            "/measurements?signal_ids=100,200&from=2021-11-07T00:00:00&to=2021-12-01T00:00:00&format=objects",
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert!(body.get("measurements").is_some());
        assert!(body.get("timestamps").is_none());
    }

    #[tokio::test]
    async fn test_get_measurements_invalid_format() {
        let (status, _body) = get_json(
            test_app(),
            "/measurements?signal_ids=100&from=2021-11-07T00:00:00&to=2021-12-01T00:00:00&format=invalid",
        )
        .await;
        assert_eq!(status, StatusCode::UNPROCESSABLE_ENTITY);
    }

    // -- OpenAPI docs --

    #[tokio::test]
    async fn test_openapi_available_in_debug() {
        let app = build_app(test_service(), true);
        let resp = app
            .oneshot(
                Request::builder()
                    .uri("/openapi.json")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_openapi_not_available_in_production() {
        let app = build_app(test_service(), false);
        let resp = app
            .oneshot(
                Request::builder()
                    .uri("/openapi.json")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::NOT_FOUND);
    }

    // -- Edge cases --

    #[tokio::test]
    async fn test_get_measurements_too_many_signal_ids() {
        // Build a query with 101 signal IDs
        let ids: Vec<String> = (1..=101).map(|i| i.to_string()).collect();
        let ids_str = ids.join(",");
        let uri = format!(
            "/measurements?signal_ids={}&from=2021-11-07T00:00:00&to=2021-12-01T00:00:00",
            ids_str
        );
        let (status, body) = get_json(test_app(), &uri).await;
        assert_eq!(status, StatusCode::BAD_REQUEST);
        assert!(body["detail"].as_str().unwrap().contains("max"));
    }

    #[tokio::test]
    async fn test_get_measurements_with_whitespace() {
        let (status, body) = get_json(
            test_app(),
            "/measurements?signal_ids=%20100%20,%20200%20&from=2021-11-07T00:00:00&to=2021-12-01T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body["total"], 15);
    }

    #[tokio::test]
    async fn test_get_measurements_trailing_comma() {
        let (status, body) = get_json(
            test_app(),
            "/measurements?signal_ids=100,&from=2021-11-07T00:00:00&to=2021-12-01T00:00:00",
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body["total"], 10);
    }
}
