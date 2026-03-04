use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use serde_json::json;

/// Application error types that map to specific HTTP status codes.
#[derive(Debug)]
pub enum AppError {
    /// 404 Not Found
    NotFound(String),
    /// 400 Bad Request
    BadRequest(String),
    /// 422 Unprocessable Entity
    UnprocessableEntity(String),
    /// 503 Service Unavailable
    ServiceUnavailable(String),
}

impl std::fmt::Display for AppError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AppError::NotFound(msg) => write!(f, "{msg}"),
            AppError::BadRequest(msg) => write!(f, "{msg}"),
            AppError::UnprocessableEntity(msg) => write!(f, "{msg}"),
            AppError::ServiceUnavailable(msg) => write!(f, "{msg}"),
        }
    }
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            AppError::NotFound(msg) => (StatusCode::NOT_FOUND, msg.clone()),
            AppError::BadRequest(msg) => (StatusCode::BAD_REQUEST, msg.clone()),
            AppError::UnprocessableEntity(msg) => (StatusCode::UNPROCESSABLE_ENTITY, msg.clone()),
            AppError::ServiceUnavailable(_) => (
                StatusCode::SERVICE_UNAVAILABLE,
                "Service temporarily unavailable".to_string(),
            ),
        };

        let body = json!({ "detail": message });
        (status, axum::Json(body)).into_response()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use http_body_util::BodyExt;

    async fn response_body(resp: Response) -> serde_json::Value {
        let bytes = resp.into_body().collect().await.unwrap().to_bytes();
        serde_json::from_slice(&bytes).unwrap()
    }

    #[tokio::test]
    async fn test_not_found_response() {
        let err = AppError::NotFound("Signal 999 not found".to_string());
        let resp = err.into_response();
        assert_eq!(resp.status(), StatusCode::NOT_FOUND);
        let body = response_body(resp).await;
        assert_eq!(body["detail"], "Signal 999 not found");
    }

    #[tokio::test]
    async fn test_bad_request_response() {
        let err = AppError::BadRequest("Invalid date range".to_string());
        let resp = err.into_response();
        assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
        let body = response_body(resp).await;
        assert_eq!(body["detail"], "Invalid date range");
    }

    #[tokio::test]
    async fn test_unprocessable_entity_response() {
        let err = AppError::UnprocessableEntity("Missing field".to_string());
        let resp = err.into_response();
        assert_eq!(resp.status(), StatusCode::UNPROCESSABLE_ENTITY);
    }

    #[tokio::test]
    async fn test_service_unavailable_hides_details() {
        let err = AppError::ServiceUnavailable("/secret/path/data.csv not found".to_string());
        let resp = err.into_response();
        assert_eq!(resp.status(), StatusCode::SERVICE_UNAVAILABLE);
        let body = response_body(resp).await;
        // Must NOT expose the internal path
        assert_eq!(body["detail"], "Service temporarily unavailable");
        assert!(!body["detail"].as_str().unwrap().contains("/secret"));
    }

    #[test]
    fn test_display_impl() {
        let err = AppError::NotFound("test".to_string());
        assert_eq!(format!("{err}"), "test");
    }
}
