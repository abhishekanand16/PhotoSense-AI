// PhotoSense-AI Desktop Application
// 
// This is the Tauri wrapper that:
// 1. Launches the Python backend as a sidecar process
// 2. Manages the backend lifecycle (start on open, stop on close)
// 3. Provides the native window for the React frontend
// 4. Ensures backend cleanup on crash, force-quit, or OS shutdown

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::Mutex;
use std::sync::atomic::{AtomicU32, AtomicBool, Ordering};
use std::time::Duration;
use std::thread;
use std::net::TcpStream;
use tauri::api::process::{Command, CommandChild, CommandEvent};
use tauri::{Manager, State, RunEvent};

const BACKEND_PORT: u16 = 8000;
const BACKEND_HOST: &str = "127.0.0.1";
const HEALTH_CHECK_TIMEOUT_SECS: u64 = 2;
const MAX_STARTUP_ATTEMPTS: u32 = 120; // 60 seconds total (500ms * 120)

/// Global PID tracking for cleanup on unexpected termination
static BACKEND_PID: AtomicU32 = AtomicU32::new(0);
static CLEANUP_DONE: AtomicBool = AtomicBool::new(false);

/// Holds the backend process handle for lifecycle management
struct BackendState {
    child: Option<std::process::Child>,
}

/// Kill backend process by PID (used for cleanup on crash/force-quit)
fn kill_backend_by_pid() {
    // Only run cleanup once
    if CLEANUP_DONE.swap(true, Ordering::SeqCst) {
        return;
    }
    
    let pid = BACKEND_PID.load(Ordering::SeqCst);
    if pid == 0 {
        return;
    }
    
    println!("[PhotoSense] Cleanup: Killing backend process PID {}", pid);
    
    #[cfg(target_os = "windows")]
    {
        // Windows: use taskkill to forcefully terminate the process tree
        let _ = std::process::Command::new("taskkill")
            .args(["/F", "/T", "/PID", &pid.to_string()])
            .output();
    }
    
    #[cfg(not(target_os = "windows"))]
    {
        // Unix: send SIGKILL to process group
        unsafe {
            // Kill the process group (negative PID)
            libc::kill(-(pid as i32), libc::SIGKILL);
            // Also kill the process directly in case it's not a group leader
            libc::kill(pid as i32, libc::SIGKILL);
        }
    }
}

/// Check if backend port is already in use (prevents duplicate instances)
fn is_backend_already_running() -> bool {
    is_port_open(BACKEND_HOST, BACKEND_PORT)
}

/// Simple TCP check to see if backend port is open (faster than HTTP)
fn is_port_open(host: &str, port: u16) -> bool {
    let addr = format!("{}:{}", host, port);
    TcpStream::connect_timeout(
        &addr.parse().unwrap(),
        Duration::from_secs(HEALTH_CHECK_TIMEOUT_SECS)
    ).is_ok()
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

/// Spawn the backend sidecar process
fn spawn_backend() -> Result<(CommandChild, u16), String> {
    // Check if backend is already running (prevents duplicate instances)
    if is_backend_already_running() {
        println!("[PhotoSense] Backend already running on port {}, reusing existing instance", BACKEND_PORT);
        return Err("Backend already running".to_string());
    }
    
    println!("[PhotoSense] Starting backend sidecar on port {}", BACKEND_PORT);
    
    // Spawn the sidecar binary
    // Tauri expects sidecar in binaries/ folder with target triple suffix
    // For PyInstaller bundles, the sidecar needs to run from its directory
    // so that it can find its bundled dependencies
    let (mut rx, child) = Command::new_sidecar("photosense-backend")
        .map_err(|e| format!("Failed to create sidecar command: {}", e))?
        .spawn()
        .map_err(|e| format!("Failed to spawn backend: {}", e))?;
    
    // Store PID globally for cleanup on unexpected termination
    let pid = child.pid();
    BACKEND_PID.store(pid, Ordering::SeqCst);
    println!("[PhotoSense] Backend process started with PID {}", pid);
    
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
                    // Clear PID on normal termination
                    BACKEND_PID.store(0, Ordering::SeqCst);
                }
                _ => {}
            }
        }
    });
    
    Ok((child, BACKEND_PORT))
}

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

/// Cleanup function called on app exit (handles all termination scenarios)
fn cleanup_backend(state: &Mutex<BackendState>) {
    // First try graceful shutdown via CommandChild
    if let Ok(mut state_guard) = state.lock() {
        if let Some(child) = state_guard.child.take() {
            println!("[PhotoSense] Terminating backend process gracefully...");
            let _ = child.kill();
            state_guard.started = false;
        }
    }
    
    // Then ensure cleanup via PID (catches edge cases)
    kill_backend_by_pid();
}

fn main() {
    // Register panic hook to cleanup backend on crash
    let default_panic = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        eprintln!("[PhotoSense] Application panic detected, cleaning up backend...");
        kill_backend_by_pid();
        default_panic(info);
    }));
    
    // Register signal handlers for graceful shutdown (Unix)
    #[cfg(not(target_os = "windows"))]
    {
        // Handle SIGTERM, SIGINT, SIGHUP
        let _ = ctrlc::set_handler(move || {
            println!("[PhotoSense] Received termination signal, cleaning up...");
            kill_backend_by_pid();
            std::process::exit(0);
        });
    }
    
    let app = tauri::Builder::default()
        .manage(Mutex::new(BackendState {
            child: None,
            port: BACKEND_PORT,
            started: false,
        }))
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
                    // Check if backend is already running (this is OK)
                    if is_backend_already_running() {
                        println!("[PhotoSense] Connecting to existing backend on port {}", BACKEND_PORT);
                        let state = app.state::<Mutex<BackendState>>();
                        if let Ok(mut state_guard) = state.lock() {
                            state_guard.started = true;
                        }
                        let _ = app_handle.emit_all("backend-ready", BACKEND_PORT);
                    } else {
                        eprintln!("[PhotoSense] Failed to start backend: {}", e);
                        eprintln!("[PhotoSense] The app will try to connect to an existing backend");
                    }
                }
            }
            Ok(())
        })
        .on_window_event(|event| {
            // Clean up backend when window closes
            if let tauri::WindowEvent::CloseRequested { .. } = event.event() {
                let app = event.window().app_handle();
                let state = app.state::<Mutex<BackendState>>();
                cleanup_backend(&state);
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_status,
            get_backend_port,
        ])
        .build(tauri::generate_context!())
        .expect("Error building PhotoSense-AI");
    
    // Use run() with event handler to catch ALL exit scenarios
    app.run(|app_handle, event| {
        match event {
            RunEvent::Exit => {
                // Called on normal exit, Cmd+Q, dock quit, etc.
                println!("[PhotoSense] Application exiting, cleaning up backend...");
                let state = app_handle.state::<Mutex<BackendState>>();
                cleanup_backend(&state);
            }
            RunEvent::ExitRequested { api, .. } => {
                // Called when exit is requested but can be prevented
                // We don't prevent it, just ensure cleanup happens
                println!("[PhotoSense] Exit requested, backend will be cleaned up...");
            }
            _ => {}
        }
    });
}
