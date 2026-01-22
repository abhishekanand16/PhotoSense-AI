#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;
use tauri::Manager;

struct BackendState {
    child: Option<std::process::Child>,
}

fn log_path(app: &tauri::AppHandle) -> PathBuf {
    let base = app
        .path_resolver()
        .app_data_dir()
        .unwrap_or_else(std::env::temp_dir);
    base.join("logs")
}

fn log_line(app: &tauri::AppHandle, message: &str) {
    let log_dir = log_path(app);
    if fs::create_dir_all(&log_dir).is_ok() {
        let log_file = log_dir.join("backend.log");
        if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(log_file) {
            let _ = writeln!(file, "{message}");
        }
    }
}

fn is_backend_ready() -> bool {
    std::net::TcpStream::connect_timeout(
        &"127.0.0.1:8000".parse().unwrap(),
        Duration::from_secs(1),
    )
    .is_ok()
}

fn wait_for_backend(max_seconds: u32) -> bool {
    for i in 1..=max_seconds * 2 {
        if is_backend_ready() {
            return true;
        }
        thread::sleep(Duration::from_millis(500));
    }
    false
}

fn start_backend(app: &tauri::AppHandle) -> Result<std::process::Child, String> {
    log_line(app, "[PhotoSense] Starting backend...");

    let backend_path = app
        .path_resolver()
        .resolve_resource("backend/photosense-backend")
        .ok_or("Backend resource not found: backend/photosense-backend")?;

    let backend_dir = backend_path
        .parent()
        .ok_or("Backend directory not found")?;

    log_line(
        app,
        &format!("[PhotoSense] Backend path: {}", backend_path.display()),
    );

    let log_dir = log_path(app);
    let _ = fs::create_dir_all(&log_dir);
    let log_file = log_dir.join("backend.log");
    let log_handle = OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_file)
        .map_err(|e| format!("Failed to open backend log file: {e}"))?;

    Command::new(&backend_path)
        .current_dir(backend_dir)
        .stdout(Stdio::from(log_handle.try_clone().map_err(|e| e.to_string())?))
        .stderr(Stdio::from(log_handle))
        .spawn()
        .map_err(|e| format!("Failed to spawn backend: {e}"))
}

#[tauri::command]
fn check_backend_status() -> bool {
    is_backend_ready()
}

fn main() {
    tauri::Builder::default()
        .manage(Mutex::new(BackendState { child: None }))
        .setup(|app| {
            match start_backend(&app.handle()) {
                Ok(child) => {
                    let state = app.state::<Mutex<BackendState>>();
                    state.lock().unwrap().child = Some(child);
                    if !wait_for_backend(30) {
                        log_line(&app.handle(), "[Warning] Backend may still be starting...");
                    }
                }
                Err(e) => {
                    log_line(&app.handle(), &format!("[Error] Backend failed to start: {e}"));
                }
            }
            Ok(())
        })
        .on_window_event(|event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event.event() {
                let state = event.window().app_handle().state::<Mutex<BackendState>>();
                if let Some(child) = state.lock().unwrap().child.take() {
                    let _ = child.kill();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![check_backend_status])
        .run(tauri::generate_context!())
        .expect("Error running PhotoSense-AI");
}
