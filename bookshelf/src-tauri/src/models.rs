use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct Book {
    pub id: String,
    pub title: String,
    pub author: String,
    pub file_path: String,
    pub format: String,
    pub cover_path: Option<String>,
    pub total_pages: Option<i64>,
    pub file_size: i64,
    pub added_at: String,
    pub last_opened_at: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct ReadingProgress {
    pub book_id: String,
    pub position: String,
    pub percentage: f64,
    pub updated_at: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct ReaderSettings {
    pub theme: String,
    pub font_size: i64,
    pub line_height: f64,
    pub font_family: String,
}

impl Default for ReaderSettings {
    fn default() -> Self {
        ReaderSettings {
            theme: "light".to_string(),
            font_size: 18,
            line_height: 1.6,
            font_family: "serif".to_string(),
        }
    }
}
