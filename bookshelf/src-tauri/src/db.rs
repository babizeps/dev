use rusqlite::{Connection, Result};
use std::path::PathBuf;

pub fn get_db_path(app_data_dir: &PathBuf) -> PathBuf {
    app_data_dir.join("bookshelf.db")
}

pub fn init_db(conn: &Connection) -> Result<()> {
    conn.execute_batch(
        "
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            file_path TEXT NOT NULL UNIQUE,
            format TEXT NOT NULL,
            cover_path TEXT,
            total_pages INTEGER,
            file_size INTEGER NOT NULL,
            added_at TEXT NOT NULL,
            last_opened_at TEXT
        );
        CREATE TABLE IF NOT EXISTS reading_progress (
            book_id TEXT PRIMARY KEY REFERENCES books(id) ON DELETE CASCADE,
            position TEXT NOT NULL,
            percentage REAL NOT NULL,
            updated_at TEXT NOT NULL
        );
        ",
    )
}
