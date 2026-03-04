use axum::Json;
use serde_json::{json, Value};

/// GET /health
#[utoipa::path(
    get,
    path = "/health",
    responses(
        (status = 200, description = "Health check", body = Value)
    )
)]
pub async fn health_check() -> Json<Value> {
    Json(json!({ "status": "ok" }))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_health_check() {
        let Json(body) = health_check().await;
        assert_eq!(body["status"], "ok");
    }
}
