// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use std::thread;
use std::time::Duration;
use tauri::Manager;

struct BackendState {
    child: Option<tauri::api::process::CommandChild>,
}

/// Check if backend is responding on port 8000
fn is_backend_ready() -> bool {
    std::net::TcpStream::connect_timeout(
        &"127.0.0.1:8000".parse().unwrap(),
        Duration::from_secs(1),
    )
    .is_ok()
}

/// Wait for backend to become ready
fn wait_for_backend(max_seconds: u32) -> bool {
    for i in 1..=max_seconds * 2 {
        if is_backend_ready() {
            println!("[PhotoSense] Backend ready after ~{}ms", i * 500);
            return true;
        }
        if i % 4 == 0 {
            println!("[PhotoSense] Waiting for backend... ({}s)", i / 2);
        }
        thread::sleep(Duration::from_millis(500));
    }
    false
}

/// Spawn the Python backend sidecar
fn start_backend() -> Result<tauri::api::process::CommandChild, String> {
    use tauri::api::process::{Command, CommandEvent};

    println!("[PhotoSense] Starting backend...");

    let cmd = Command::new_sidecar("photosense-backend")
        .map_err(|e| format!("Sidecar not found: {}", e))?;

    let (mut rx, child) = cmd
        .spawn()
        .map_err(|e| format!("Failed to spawn backend: {}", e))?;

    // Log output in background
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => println!("[Backend] {}", line),
                CommandEvent::Stderr(line) => eprintln!("[Backend] {}", line),
                CommandEvent::Error(e) => eprintln!("[Backend Error] {}", e),
                CommandEvent::Terminated(t) => {
                    println!("[Backend] Process exited with code: {:?}", t.code)
                }
                _ => {}
            }
        }
    });

    Ok(child)
}

#[tauri::command]
fn check_backend_status() -> bool {
    is_backend_ready()
}

fn main() {
    tauri::Builder::default()
        .manage(Mutex::new(BackendState { child: None }))
        .setup(|app| {
            println!("================================================");
            println!("  PhotoSense-AI Starting");
            println!("================================================");

            // Start the backend sidecar
            match start_backend() {
                Ok(child) => {
                    // Store the child process handle
                    let state = app.state::<Mutex<BackendState>>();
                    state.lock().unwrap().child = Some(child);

                    // Wait for backend to be ready (max 30 seconds)
                    if wait_for_backend(30) {
                        println!("================================================");
                        println!("  PhotoSense-AI Ready!");
                        println!("  Backend: http://127.0.0.1:8000");
                        println!("================================================");
                    } else {
                        eprintln!("[Warning] Backend may still be starting...");
                    }
                }
                Err(e) => {
                    eprintln!("================================================");
                    eprintln!("  Backend failed to start: {}", e);
                    eprintln!("  ");
                    eprintln!("  For development, run manually:");
                    eprintln!("  python run_api.py");
                    eprintln!("================================================");
                }
            }

            Ok(())
        })
        .on_window_event(|event| {
            // Kill backend when app window closes
            if let tauri::WindowEvent::CloseRequested { .. } = event.event() {
                let state = event.window().app_handle().state::<Mutex<BackendState>>();
                if let Some(child) = state.lock().unwrap().child.take() {
                    println!("[PhotoSense] Stopping backend...");
                    let _ = child.kill();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![check_backend_status])
        .run(tauri::generate_context!())
        .expect("Error running PhotoSense-AI");
}
