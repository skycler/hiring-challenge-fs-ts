use std::env;
use std::path::{Path, PathBuf};

/// Application configuration loaded from environment variables.
#[derive(Debug, Clone)]
pub struct AppConfig {
    pub app_name: String,
    pub api_version: String,
    pub debug: bool,
    pub data_dir: PathBuf,
    pub signals_path: PathBuf,
    pub assets_path: PathBuf,
    pub measurements_path: PathBuf,
}

impl AppConfig {
    /// Load configuration from environment variables (with .env support).
    /// Validates path-traversal protection rules.
    pub fn from_env() -> Result<Self, String> {
        let app_name = env::var("APP_NAME").unwrap_or_else(|_| "AssetAPI".to_string());
        let api_version = env::var("API_VERSION").unwrap_or_else(|_| "v1".to_string());
        let debug = env::var("DEBUG")
            .unwrap_or_else(|_| "false".to_string())
            .to_lowercase()
            == "true";
        let data_dir_str = env::var("DATA_DIR").unwrap_or_else(|_| "data".to_string());
        let signals_path_str =
            env::var("SIGNALS_PATH").unwrap_or_else(|_| "data/signal.json".to_string());
        let assets_path_str =
            env::var("ASSETS_PATH").unwrap_or_else(|_| "data/assets.json".to_string());
        let measurements_path_str =
            env::var("MEASUREMENTS_PATH").unwrap_or_else(|_| "data/measurements.csv".to_string());

        let project_root = env::current_dir().map_err(|e| format!("Cannot get cwd: {e}"))?;

        // Resolve DATA_DIR
        let data_dir = resolve_and_validate_inside(&project_root, &data_dir_str, &project_root)?;

        // Resolve each file path and ensure it's inside DATA_DIR
        let signals_path = resolve_and_validate_inside(&project_root, &signals_path_str, &data_dir)?;
        let assets_path = resolve_and_validate_inside(&project_root, &assets_path_str, &data_dir)?;
        let measurements_path =
            resolve_and_validate_inside(&project_root, &measurements_path_str, &data_dir)?;

        Ok(Self {
            app_name,
            api_version,
            debug,
            data_dir,
            signals_path,
            assets_path,
            measurements_path,
        })
    }
}

/// Resolve a potentially relative path against `base` and check it lives inside `must_be_inside`.
fn resolve_and_validate_inside(
    base: &Path,
    raw: &str,
    must_be_inside: &Path,
) -> Result<PathBuf, String> {
    let candidate = if Path::new(raw).is_absolute() {
        PathBuf::from(raw)
    } else {
        base.join(raw)
    };

    // We can't canonicalize if the path doesn't exist yet, so we normalize manually.
    let resolved = normalize_path(&candidate);
    let parent_resolved = normalize_path(must_be_inside);

    if !resolved.starts_with(&parent_resolved) {
        return Err(format!(
            "Path '{}' escapes allowed directory '{}'",
            raw,
            parent_resolved.display()
        ));
    }

    Ok(resolved)
}

/// Simple path normalization that resolves `.` and `..` without requiring the path to exist.
fn normalize_path(path: &Path) -> PathBuf {
    let mut components = Vec::new();
    for component in path.components() {
        match component {
            std::path::Component::ParentDir => {
                components.pop();
            }
            std::path::Component::CurDir => {}
            c => components.push(c),
        }
    }
    components.iter().collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_path_removes_parent() {
        let p = normalize_path(Path::new("/a/b/../c"));
        assert_eq!(p, PathBuf::from("/a/c"));
    }

    #[test]
    fn test_normalize_path_removes_curdir() {
        let p = normalize_path(Path::new("/a/./b/./c"));
        assert_eq!(p, PathBuf::from("/a/b/c"));
    }

    #[test]
    fn test_resolve_and_validate_inside_ok() {
        let base = Path::new("/project");
        let inside = Path::new("/project/data");
        let result = resolve_and_validate_inside(base, "data/file.json", inside);
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), PathBuf::from("/project/data/file.json"));
    }

    #[test]
    fn test_resolve_and_validate_inside_escape() {
        let base = Path::new("/project");
        let inside = Path::new("/project/data");
        let result = resolve_and_validate_inside(base, "../etc/passwd", inside);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("escapes"));
    }

    #[test]
    fn test_resolve_and_validate_data_dir_inside_project() {
        let base = Path::new("/project");
        let project = Path::new("/project");
        let result = resolve_and_validate_inside(base, "data", project);
        assert!(result.is_ok());
    }

    #[test]
    fn test_resolve_and_validate_data_dir_escapes_project() {
        let base = Path::new("/project");
        let project = Path::new("/project");
        let result = resolve_and_validate_inside(base, "../other", project);
        assert!(result.is_err());
    }

    #[test]
    fn test_resolve_absolute_path_inside() {
        let base = Path::new("/project");
        let inside = Path::new("/project/data");
        let result = resolve_and_validate_inside(base, "/project/data/file.json", inside);
        assert!(result.is_ok());
    }

    #[test]
    fn test_resolve_absolute_path_outside() {
        let base = Path::new("/project");
        let inside = Path::new("/project/data");
        let result = resolve_and_validate_inside(base, "/etc/passwd", inside);
        assert!(result.is_err());
    }
}
