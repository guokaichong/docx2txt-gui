#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            docx_reader_lib::parse_docx,
            docx_reader_lib::export_txt,
            docx_reader_lib::export_md,
        ])
        .run(tauri::generate_context!())
        .expect("Tauri 应用启动失败");
}
