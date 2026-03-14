mod commands;
mod db;
mod models;

use commands::{AppDataDir, DbState};
use rusqlite::Connection;
use std::sync::Mutex;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .setup(|app| {
            let app_data_dir = app
                .path()
                .app_data_dir()
                .expect("could not resolve app data dir");
            std::fs::create_dir_all(&app_data_dir).expect("could not create app data dir");

            let db_path = db::get_db_path(&app_data_dir);
            let conn = Connection::open(&db_path).expect("could not open database");
            db::init_db(&conn).expect("could not initialize database");

            app.manage(DbState(Mutex::new(conn)));
            app.manage(AppDataDir(app_data_dir));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::list_books,
            commands::add_book,
            commands::remove_book,
            commands::update_last_opened,
            commands::get_progress,
            commands::save_progress,
            commands::read_file_bytes,
            commands::read_file_text,
            commands::get_settings,
            commands::save_settings,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
