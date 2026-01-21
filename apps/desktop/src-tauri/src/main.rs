// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use std::sync::Mutex;

// Store the backend process handle so we can terminate it on app close
struct BackendState {
    child: Option<tauri::api::process::CommandChild>,
}

/// Spawn the Python backend API server.
/// In development, expects Python environment to be set up.
/// In production, uses bundled sidecar binary (PyInstaller).
fn spawn_backend(app_handle: &tauri::AppHandle) -> Result<tauri::api::process::CommandChild, String> {
    use tauri::api::process::{Command, CommandEvent};
    
    // Try sidecar first (production build)
    let sidecar_result = Command::new_sidecar("photosense-backend");
    
    match sidecar_result {
        Ok(sidecar_cmd) => {
            let (mut rx, child) = sidecar_cmd
                .spawn()
                .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;
            
            // Log backend output
            let _app_handle_clone = app_handle.clone();
            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            println!("[Backend] {}", line);
                        }
                        CommandEvent::Stderr(line) => {
                            eprintln!("[Backend ERR] {}", line);
                        }
                        CommandEvent::Error(err) => {
                            eprintln!("[Backend] Error: {}", err);
                        }
                        CommandEvent::Terminated(payload) => {
                            println!("[Backend] Terminated with code: {:?}", payload.code);
                        }
                        _ => {}
                    }
                }
            });
            
            println!("Backend started via sidecar");
            Ok(child)
        }
        Err(_) => {
            // Fall back to development mode: spawn Python directly
            println!("Sidecar not found, attempting development mode...");
            
            // In development, we assume the user runs the backend separately
            // or we can try to spawn it using Python
            Err("Backend sidecar not found. In development, please run the backend manually with: python run_api.py".to_string())
        }
    }
}

#[tauri::command]
fn check_backend_status() -> Result<String, String> {
    // Simple health check by trying to connect to the backend
    // This is called from the frontend to verify backend is running
    Ok("Backend check - implement HTTP health check in frontend".to_string())
}

fn main() {
    tauri::Builder::default()
        .manage(Mutex::new(BackendState { child: None }))
        .setup(|app| {
            let app_handle = app.handle();
            
            // Attempt to spawn backend (non-fatal if it fails in dev mode)
            match spawn_backend(&app_handle) {
                Ok(child) => {
                    let state = app.state::<Mutex<BackendState>>();
                    let mut state_guard = state.lock().unwrap();
                    state_guard.child = Some(child);
                    println!("Backend process started successfully");
                }
                Err(e) => {
                    // In development mode, this is expected - user runs backend separately
                    println!("Note: {}", e);
                    println!("The app will attempt to connect to backend at http://localhost:8000");
                }
            }
            
            Ok(())
        })
        .on_window_event(|event| {
            if let tauri::WindowEvent::Destroyed = event.event() {
                // Clean up backend process when window is destroyed
                let app = event.window().app_handle();
                let state = app.state::<Mutex<BackendState>>();
                let mut state_guard = state.lock().unwrap();
                
                if let Some(child) = state_guard.child.take() {
                    println!("Terminating backend process...");
                    let _ = child.kill();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![check_backend_status])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
