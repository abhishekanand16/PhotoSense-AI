// Prevents additional console window on Windows in release, DO NOT REMOVE!!
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
            let _ = writeln!(file, "{}", message);
        }
    }
}

fn is_backend_ready() -> bool {
    let addr: std::net::SocketAddr = match "127.0.0.1:8000".parse() {
        Ok(a) => a,
        Err(_) => return false,
    };
    std::net::TcpStream::connect_timeout(&addr, Duration::from_secs(1)).is_ok()
}

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

fn start_backend(app: &tauri::AppHandle) -> Result<std::process::Child, String> {
    println!("[PhotoSense] Starting backend...");
    log_line(app, "[PhotoSense] Starting backend...");

    // #region agent log
    let debug_log = std::path::PathBuf::from("/Users/abhishek/Documents/GitHub/PhotoSense-AI/.cursor/debug.log");
    let _ = std::fs::OpenOptions::new().create(true).append(true).open(&debug_log).and_then(|mut f| {
        use std::io::Write;
        writeln!(f, r#"{{"location":"main.rs:57","message":"start_backend entry","data":{{"timestamp":{}}},"sessionId":"debug-session","hypothesisId":"A"}}"#, std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_millis())
    });
    // #endregion

    #[cfg(target_os = "windows")]
    let backend_name = "resources/backend/photosense-backend.exe";
    #[cfg(not(target_os = "windows"))]
    let backend_name = "resources/backend/photosense-backend";

    // #region agent log
    let _ = std::fs::OpenOptions::new().create(true).append(true).open(&debug_log).and_then(|mut f| {
        use std::io::Write;
        writeln!(f, r#"{{"location":"main.rs:64","message":"backend_name resolved","data":{{"backend_name":"{}","timestamp":{}}},"sessionId":"debug-session","hypothesisId":"A"}}"#, backend_name, std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_millis())
    });
    // #endregion

    let backend_path = app
        .path_resolver()
        .resolve_resource(backend_name)
        .ok_or_else(|| format!("Backend resource not found: {}", backend_name))?;

    // #region agent log
    let _ = std::fs::OpenOptions::new().create(true).append(true).open(&debug_log).and_then(|mut f| {
        use std::io::Write;
        writeln!(f, r#"{{"location":"main.rs:69","message":"backend_path resolved","data":{{"backend_path":"{}","exists":{},"timestamp":{}}},"sessionId":"debug-session","hypothesisId":"A,E"}}"#, backend_path.display(), backend_path.exists(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_millis())
    });
    // #endregion

    if !backend_path.exists() {
        return Err(format!(
            "Backend executable does not exist at: {}",
            backend_path.display()
        ));
    }

    let backend_dir = match backend_path.parent() {
        Some(d) => d.to_path_buf(),
        None => return Err(format!("Backend directory not found for: {}", backend_path.display())),
    };

    #[cfg(target_family = "unix")]
    {
        use std::os::unix::fs::PermissionsExt;
        if let Ok(meta) = fs::metadata(&backend_path) {
            let old_mode = meta.permissions().mode();
            let mut perms = meta.permissions();
            perms.set_mode(0o755);
            let _ = fs::set_permissions(&backend_path, perms);
            
            // #region agent log
            let _ = std::fs::OpenOptions::new().create(true).append(true).open(&debug_log).and_then(|mut f| {
                use std::io::Write;
                writeln!(f, r#"{{"location":"main.rs:86","message":"permissions set","data":{{"old_mode":{},"new_mode":493,"timestamp":{}}},"sessionId":"debug-session","hypothesisId":"B"}}"#, old_mode, std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_millis())
            });
            // #endregion
        }
    }

    log_line(app, &format!("[PhotoSense] Backend path: {}", backend_path.display()));
    log_line(app, &format!("[PhotoSense] Backend cwd: {}", backend_dir.display()));

    let log_dir = log_path(app);
    let _ = fs::create_dir_all(&log_dir);
    let log_file = log_dir.join("backend.log");
    
    let data_dir_str = log_dir
        .parent()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|| backend_dir.to_string_lossy().to_string());
    
    let log_handle = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_file)
        .map_err(|e| format!("Failed to open backend log file: {e}"))?;

    let log_handle_clone = log_handle.try_clone()
        .map_err(|e| format!("Failed to clone log handle: {e}"))?;

    // #region agent log
    let _ = std::fs::OpenOptions::new().create(true).append(true).open(&debug_log).and_then(|mut f| {
        use std::io::Write;
        writeln!(f, r#"{{"location":"main.rs:114","message":"before spawn","data":{{"backend_path":"{}","backend_dir":"{}","data_dir":"{}","timestamp":{}}},"sessionId":"debug-session","hypothesisId":"C,D"}}"#, backend_path.display(), backend_dir.display(), data_dir_str, std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_millis())
    });
    // #endregion

    let child = Command::new(&backend_path)
        .current_dir(&backend_dir)
        .env("PHOTOSENSE_DATA_DIR", data_dir_str)
        .stdout(Stdio::from(log_handle_clone))
        .stderr(Stdio::from(log_handle))
        .spawn()
        .map_err(|e| {
            // #region agent log
            let _ = std::fs::OpenOptions::new().create(true).append(true).open(&debug_log).and_then(|mut f| {
                use std::io::Write;
                writeln!(f, r#"{{"location":"main.rs:120","message":"spawn failed","data":{{"error":"{}","timestamp":{}}},"sessionId":"debug-session","hypothesisId":"C"}}"#, e.to_string().replace("\"", "\\\""), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_millis())
            });
            // #endregion
            format!("Failed to spawn backend: {e}")
        })?;

    // #region agent log
    let _ = std::fs::OpenOptions::new().create(true).append(true).open(&debug_log).and_then(|mut f| {
        use std::io::Write;
        writeln!(f, r#"{{"location":"main.rs:122","message":"spawn success","data":{{"pid":{},"timestamp":{}}},"sessionId":"debug-session","hypothesisId":"C"}}"#, child.id(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_millis())
    });
    // #endregion

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

            match start_backend(&app.handle()) {
                Ok(child) => {
                    let state = app.state::<Mutex<BackendState>>();
                    state.lock().unwrap().child = Some(child);
                    if wait_for_backend(30) {
                        println!("================================================");
                        println!("  PhotoSense-AI Ready!");
                        println!("  Backend: http://127.0.0.1:8000");
                        println!("================================================");
                    } else {
                        eprintln!("[Warning] Backend may still be starting...");
                        log_line(&app.handle(), "[Warning] Backend may still be starting...");
                    }
                }
                Err(e) => {
                    eprintln!("================================================");
                    eprintln!("  Backend failed to start: {}", e);
                    eprintln!("  ");
                    eprintln!("  For development, run manually:");
                    eprintln!("  python run_api.py");
                    eprintln!("================================================");
                    log_line(&app.handle(), &format!("[Error] Backend failed to start: {e}"));
                }
            }
            Ok(())
        })
        .on_window_event(|event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event.event() {
                let app_handle = event.window().app_handle();
                let state = app_handle.state::<Mutex<BackendState>>();
                let child_opt = {
                    let mut state_guard = state.lock().unwrap();
                    state_guard.child.take()
                };
                if let Some(mut child) = child_opt {
                    println!("[PhotoSense] Stopping backend...");
                    let _ = child.kill();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![check_backend_status])
        .run(tauri::generate_context!())
        .expect("Error running PhotoSense-AI");
}
