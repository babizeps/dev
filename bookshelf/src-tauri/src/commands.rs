use crate::models::{Book, ReadingProgress, ReaderSettings};
use chrono::Utc;
use rusqlite::{params, Connection};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use tauri::State;
use uuid::Uuid;

pub struct DbState(pub Mutex<Connection>);
pub struct AppDataDir(pub PathBuf);

fn detect_format(path: &Path) -> Option<String> {
    path.extension()
        .and_then(|e| e.to_str())
        .map(|e| e.to_lowercase())
        .filter(|e| matches!(e.as_str(), "pdf" | "epub" | "txt"))
}

fn extract_epub_metadata(file_path: &Path) -> (String, String) {
    use std::io::Read;

    let title = file_path
        .file_stem()
        .unwrap_or_default()
        .to_string_lossy()
        .to_string();

    let file = match fs::File::open(file_path) {
        Ok(f) => f,
        Err(_) => return (title, "Unknown Author".to_string()),
    };

    let mut archive = match zip::ZipArchive::new(file) {
        Ok(a) => a,
        Err(_) => return (title, "Unknown Author".to_string()),
    };

    // Step 1: read container.xml to find OPF path
    let opf_path = {
        let mut container = match archive.by_name("META-INF/container.xml") {
            Ok(c) => c,
            Err(_) => return (title, "Unknown Author".to_string()),
        };
        let mut content = String::new();
        let _ = container.read_to_string(&mut content);
        // Find full-path="..."
        content.find("full-path=\"").and_then(|start| {
            let rest = &content[start + 11..];
            rest.find('"').map(|end| rest[..end].to_string())
        })
    };

    let opf_path = match opf_path {
        Some(p) => p,
        None => return (title, "Unknown Author".to_string()),
    };

    // Step 2: read OPF file
    let opf = {
        let mut opf_file = match archive.by_name(&opf_path) {
            Ok(f) => f,
            Err(_) => return (title, "Unknown Author".to_string()),
        };
        let mut content = String::new();
        let _ = opf_file.read_to_string(&mut content);
        content
    };

    let parsed_title = extract_xml_tag(&opf, "dc:title")
        .or_else(|| extract_xml_tag(&opf, "title"));
    let parsed_author = extract_xml_tag(&opf, "dc:creator")
        .or_else(|| extract_xml_tag(&opf, "creator"));

    (
        parsed_title.unwrap_or(title),
        parsed_author.unwrap_or_else(|| "Unknown Author".to_string()),
    )
}

fn extract_xml_tag(xml: &str, tag: &str) -> Option<String> {
    let open = format!("<{}", tag);
    let close = format!("</{}>", tag);
    let start = xml.find(&open)?;
    let after_open = xml[start..].find('>')?;
    let content_start = start + after_open + 1;
    let end = xml[content_start..].find(&close)?;
    let content = xml[content_start..content_start + end].trim().to_string();
    if content.is_empty() {
        None
    } else {
        Some(content)
    }
}

fn extract_pdf_metadata(file_path: &Path) -> (String, String) {
    let title = file_path
        .file_stem()
        .unwrap_or_default()
        .to_string_lossy()
        .to_string();

    if let Ok(doc) = lopdf::Document::load(file_path) {
        // Get Info dictionary via its ObjectId from the trailer
        if let Some(lopdf::Object::Reference(info_id)) = doc.trailer.get(b"Info").ok().cloned() {
            if let Ok(lopdf::Object::Dictionary(dict)) = doc.get_object(info_id) {
                let pdf_title = dict.get(b"Title")
                    .ok()
                    .and_then(|o| o.as_str().ok())
                    .map(|s| String::from_utf8_lossy(s).trim().to_string())
                    .filter(|s| !s.is_empty());
                let pdf_author = dict.get(b"Author")
                    .ok()
                    .and_then(|o| o.as_str().ok())
                    .map(|s| String::from_utf8_lossy(s).trim().to_string())
                    .filter(|s| !s.is_empty());
                return (
                    pdf_title.unwrap_or(title),
                    pdf_author.unwrap_or_else(|| "Unknown Author".to_string()),
                );
            }
        }
    }
    (title, "Unknown Author".to_string())
}

#[tauri::command]
pub fn list_books(state: State<DbState>) -> Result<Vec<Book>, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare(
            "SELECT id, title, author, file_path, format, cover_path, total_pages, file_size, added_at, last_opened_at FROM books ORDER BY last_opened_at DESC, added_at DESC",
        )
        .map_err(|e| e.to_string())?;

    let books = stmt
        .query_map([], |row| {
            Ok(Book {
                id: row.get(0)?,
                title: row.get(1)?,
                author: row.get(2)?,
                file_path: row.get(3)?,
                format: row.get(4)?,
                cover_path: row.get(5)?,
                total_pages: row.get(6)?,
                file_size: row.get(7)?,
                added_at: row.get(8)?,
                last_opened_at: row.get(9)?,
            })
        })
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;

    Ok(books)
}

#[tauri::command]
pub fn add_book(file_path: String, state: State<DbState>) -> Result<Book, String> {
    let path = Path::new(&file_path);

    if !path.exists() {
        return Err(format!("File not found: {}", file_path));
    }

    let format = detect_format(path).ok_or("Unsupported file format. Use PDF, EPUB, or TXT.")?;

    let file_size = fs::metadata(path)
        .map_err(|e| e.to_string())?
        .len() as i64;

    let (title, author) = match format.as_str() {
        "epub" => extract_epub_metadata(path),
        "pdf" => extract_pdf_metadata(path),
        "txt" => (
            path.file_stem()
                .unwrap_or_default()
                .to_string_lossy()
                .to_string(),
            "Unknown Author".to_string(),
        ),
        _ => unreachable!(),
    };

    let book = Book {
        id: Uuid::new_v4().to_string(),
        title,
        author,
        file_path: file_path.clone(),
        format,
        cover_path: None,
        total_pages: None,
        file_size,
        added_at: Utc::now().to_rfc3339(),
        last_opened_at: None,
    };

    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO books (id, title, author, file_path, format, cover_path, total_pages, file_size, added_at, last_opened_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
        params![
            book.id, book.title, book.author, book.file_path, book.format,
            book.cover_path, book.total_pages, book.file_size, book.added_at, book.last_opened_at
        ],
    )
    .map_err(|e| {
        if e.to_string().contains("UNIQUE constraint failed") {
            "This book is already in your library.".to_string()
        } else {
            e.to_string()
        }
    })?;

    Ok(book)
}

#[tauri::command]
pub fn remove_book(book_id: String, state: State<DbState>) -> Result<(), String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM books WHERE id = ?1", params![book_id])
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn update_last_opened(book_id: String, state: State<DbState>) -> Result<(), String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "UPDATE books SET last_opened_at = ?1 WHERE id = ?2",
        params![Utc::now().to_rfc3339(), book_id],
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn get_progress(book_id: String, state: State<DbState>) -> Result<Option<ReadingProgress>, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    let result = conn.query_row(
        "SELECT book_id, position, percentage, updated_at FROM reading_progress WHERE book_id = ?1",
        params![book_id],
        |row| {
            Ok(ReadingProgress {
                book_id: row.get(0)?,
                position: row.get(1)?,
                percentage: row.get(2)?,
                updated_at: row.get(3)?,
            })
        },
    );

    match result {
        Ok(p) => Ok(Some(p)),
        Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
        Err(e) => Err(e.to_string()),
    }
}

#[tauri::command]
pub fn save_progress(
    book_id: String,
    position: String,
    percentage: f64,
    state: State<DbState>,
) -> Result<(), String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO reading_progress (book_id, position, percentage, updated_at)
         VALUES (?1, ?2, ?3, ?4)
         ON CONFLICT(book_id) DO UPDATE SET position=excluded.position, percentage=excluded.percentage, updated_at=excluded.updated_at",
        params![book_id, position, percentage, Utc::now().to_rfc3339()],
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn read_file_bytes(path: String) -> Result<Vec<u8>, String> {
    fs::read(&path).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn read_file_text(path: String) -> Result<String, String> {
    fs::read_to_string(&path).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_settings(state: State<AppDataDir>) -> ReaderSettings {
    let settings_path = state.0.join("settings.json");
    if let Ok(content) = fs::read_to_string(&settings_path) {
        serde_json::from_str(&content).unwrap_or_default()
    } else {
        ReaderSettings::default()
    }
}

#[tauri::command]
pub fn save_settings(settings: ReaderSettings, state: State<AppDataDir>) -> Result<(), String> {
    let settings_path = state.0.join("settings.json");
    let content = serde_json::to_string_pretty(&settings).map_err(|e| e.to_string())?;
    fs::write(&settings_path, content).map_err(|e| e.to_string())
}
