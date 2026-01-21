// PhotoSense-AI Desktop Application
// 
// This is the Tauri wrapper that:
// 1. Launches the Python backend as a sidecar process
// 2. Manages the backend lifecycle
// 3. Provides the native window for the React frontend

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use std::time::Duration;
use tauri::api::process::{Command, CommandChild, CommandEvent};
use tauri::{Manager, State};

/// Holds the backend process handle for lifecycle management
struct BackendState {
    child: Option<CommandChild>,
    port: u16,
}

/// Check if the backend is responding
async fn check_backend_health(port: u16) -> bool {
    let url = format!("http://127.0.0.1:{}/health", port);
    match reqwest::Client::new()
        .get(&url)
        .timeout(Duration::from_secs(2))
        .send()
        .await
    {
        Ok(response) => response.status().is_success(),
        Err(_) => false,
    }
}

/// Wait for backend to become healthy
async fn wait_for_backend(port: u16, max_attempts: u32) -> bool {
    for attempt in 1..=max_attempts {
        if check_backend_health(port).await {
            println!("[PhotoSense] Backend is healthy after {} attempts", attempt);
            return true;
        }
        println!("[PhotoSense] Waiting for backend... attempt {}/{}", attempt, max_attempts);
        tokio::time::sleep(Duration::from_millis(500)).await;
    }
    false
}

/// Spawn the backend sidecar process
fn spawn_backend() -> Result<(CommandChild, u16), String> {
    let port: u16 = 8000;
    
    println!("[PhotoSense] Starting backend sidecar on port {}", port);
    
    // Spawn the sidecar binary
    let (mut rx, child) = Command::new_sidecar("photosense-backend")
        .map_err(|e| format!("Failed to create sidecar command: {}", e))?
        .spawn()
        .map_err(|e| format!("Failed to spawn backend: {}", e))?;
    
    // Log backend output in background
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    println!("[Backend] {}", line);
                }
                CommandEvent::Stderr(line) => {
                    eprintln!("[Backend] {}", line);
                }
                CommandEvent::Error(err) => {
                    eprintln!("[Backend ERROR] {}", err);
                }
                CommandEvent::Terminated(payload) => {
                    println!("[Backend] Process terminated with code: {:?}", payload.code);
                }
                _ => {}
            }
        }
    });
    
    Ok((child, port))
}

/// Tauri command: Get backend status
#[tauri::command]
async fn get_backend_status(state: State<'_, Mutex<BackendState>>) -> Result<String, String> {
    let port = {
        let state_guard = state.lock().map_err(|e| e.to_string())?;
        state_guard.port
    };
    
    if check_backend_health(port).await {
        Ok(format!("Backend running on port {}", port))
    } else {
        Err("Backend not responding".to_string())
    }
}

/// Tauri command: Get backend port
#[tauri::command]
fn get_backend_port(state: State<'_, Mutex<BackendState>>) -> Result<u16, String> {
    let state_guard = state.lock().map_err(|e| e.to_string())?;
    Ok(state_guard.port)
}

fn main() {
    tauri::Builder::default()
        .manage(Mutex::new(BackendState {
            child: None,
            port: 8000,
        }))
        .setup(|app| {
            let app_handle = app.handle();
            
            // Spawn backend
            match spawn_backend() {
                Ok((child, port)) => {
                    // Store the child process
                    let state = app.state::<Mutex<BackendState>>();
                    if let Ok(mut state_guard) = state.lock() {
                        state_guard.child = Some(child);
                        state_guard.port = port;
                    }
                    
                    // Wait for backend to be ready
                    let app_handle_clone = app_handle.clone();
                    tauri::async_runtime::spawn(async move {
                        if wait_for_backend(port, 60).await {
                            println!("[PhotoSense] Backend is ready!");
                            // Emit event to frontend
                            let _ = app_handle_clone.emit_all("backend-ready", port);
                        } else {
                            eprintln!("[PhotoSense] Backend failed to start within timeout");
                            let _ = app_handle_clone.emit_all("backend-failed", "Timeout waiting for backend");
                        }
                    });
                }
                Err(e) => {
                    eprintln!("[PhotoSense] Failed to start backend: {}", e);
                    // App can still run; user will see connection errors in UI
                }
            }
            
            Ok(())
        })
        .on_window_event(|event| {
            // Clean up backend when window closes
            if let tauri::WindowEvent::Destroyed = event.event() {
                let app = event.window().app_handle();
                let state = app.state::<Mutex<BackendState>>();
                
                if let Ok(mut state_guard) = state.lock() {
                    if let Some(child) = state_guard.child.take() {
                        println!("[PhotoSense] Terminating backend process...");
                        let _ = child.kill();
                    }
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_status,
            get_backend_port,
        ])
        .run(tauri::generate_context!())
        .expect("Error running PhotoSense-AI");
}
