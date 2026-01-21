// PhotoSense-AI Desktop Application
// 
// This is the Tauri wrapper that:
// 1. Launches the Python backend as a sidecar process
// 2. Manages the backend lifecycle (start on open, stop on close)
// 3. Provides the native window for the React frontend

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use std::time::Duration;
use std::thread;
use std::net::TcpStream;
use tauri::api::process::{Command, CommandChild, CommandEvent};
use tauri::{Manager, State};

const BACKEND_PORT: u16 = 8000;
const BACKEND_HOST: &str = "127.0.0.1";
const HEALTH_CHECK_TIMEOUT_SECS: u64 = 2;
const MAX_STARTUP_ATTEMPTS: u32 = 120; // 60 seconds total (500ms * 120)

/// Holds the backend process handle for lifecycle management
struct BackendState {
    child: Option<CommandChild>,
    port: u16,
    started: bool,
}

/// Simple TCP check to see if backend port is open (faster than HTTP)
fn is_port_open(host: &str, port: u16) -> bool {
    let addr = format!("{}:{}", host, port);
    TcpStream::connect_timeout(
        &addr.parse().unwrap(),
        Duration::from_secs(HEALTH_CHECK_TIMEOUT_SECS)
    ).is_ok()
}

/// Check if the backend health endpoint responds
fn check_backend_health_sync(port: u16) -> bool {
    let url = format!("http://{}:{}/health", BACKEND_HOST, port);
    match ureq::get(&url)
        .timeout(Duration::from_secs(HEALTH_CHECK_TIMEOUT_SECS))
        .call()
    {
        Ok(response) => response.status() == 200,
        Err(_) => false,
    }
}

/// Wait for backend to become healthy (blocking)
fn wait_for_backend_sync(port: u16, max_attempts: u32) -> bool {
    for attempt in 1..=max_attempts {
        // First check if port is open (fast)
        if is_port_open(BACKEND_HOST, port) {
            // Then verify health endpoint (slower but confirms it's our backend)
            if check_backend_health_sync(port) {
                println!("[PhotoSense] Backend is healthy after {} attempts", attempt);
                return true;
            }
        }
        
        if attempt % 10 == 0 {
            println!("[PhotoSense] Still waiting for backend... attempt {}/{}", attempt, max_attempts);
        }
        
        thread::sleep(Duration::from_millis(500));
    }
    false
}

/// Spawn the backend sidecar process
fn spawn_backend() -> Result<(CommandChild, u16), String> {
    println!("[PhotoSense] Starting backend sidecar on port {}", BACKEND_PORT);
    
    // Spawn the sidecar binary
    // Tauri expects sidecar in binaries/ folder with target triple suffix
    // For PyInstaller bundles, the sidecar needs to run from its directory
    // so that it can find its bundled dependencies
    let (mut rx, child) = Command::new_sidecar("photosense-backend")
        .map_err(|e| format!("Failed to create sidecar command: {}", e))?
        .spawn()
        .map_err(|e| format!("Failed to spawn backend: {}", e))?;
    
    // Log backend output in background thread
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    // Filter out noisy uvicorn startup messages
                    if !line.contains("Started server process") 
                        && !line.contains("Waiting for application startup")
                        && !line.contains("Application startup complete") 
                    {
                        println!("[Backend] {}", line);
                    }
                }
                CommandEvent::Stderr(line) => {
                    // uvicorn logs INFO to stderr, so only show if it looks like an error
                    if line.contains("ERROR") || line.contains("error") || line.contains("Exception") {
                        eprintln!("[Backend] {}", line);
                    }
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
    
    Ok((child, BACKEND_PORT))
}

/// Tauri command: Get backend status
#[tauri::command]
fn get_backend_status(state: State<'_, Mutex<BackendState>>) -> Result<String, String> {
    let (port, started) = {
        let state_guard = state.lock().map_err(|e| e.to_string())?;
        (state_guard.port, state_guard.started)
    };
    
    if !started {
        return Err("Backend not started".to_string());
    }
    
    if check_backend_health_sync(port) {
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
            port: BACKEND_PORT,
            started: false,
        }))
        .setup(|app| {
            let app_handle = app.handle();
            
            // Spawn backend
            match spawn_backend() {
                Ok((child, port)) => {
                    // Store the child process
                    {
                        let state = app.state::<Mutex<BackendState>>();
                        if let Ok(mut state_guard) = state.lock() {
                            state_guard.child = Some(child);
                            state_guard.port = port;
                        }
                    }
                    
                    // Wait for backend to be ready in background
                    let app_handle_clone = app_handle.clone();
                    thread::spawn(move || {
                        if wait_for_backend_sync(port, MAX_STARTUP_ATTEMPTS) {
                            println!("[PhotoSense] Backend is ready!");
                            
                            // Mark as started
                            let state = app_handle_clone.state::<Mutex<BackendState>>();
                            if let Ok(mut state_guard) = state.lock() {
                                state_guard.started = true;
                            }
                            
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
                    eprintln!("[PhotoSense] The app will try to connect to an existing backend");
                    // App can still run if user started backend manually
                }
            }
            
            Ok(())
        })
        .on_window_event(|event| {
            // Clean up backend when ALL windows close
            if let tauri::WindowEvent::CloseRequested { .. } = event.event() {
                let app = event.window().app_handle();
                let state = app.state::<Mutex<BackendState>>();
                
                if let Ok(mut state_guard) = state.lock() {
                    if let Some(child) = state_guard.child.take() {
                        println!("[PhotoSense] Terminating backend process...");
                        let _ = child.kill();
                        state_guard.started = false;
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
