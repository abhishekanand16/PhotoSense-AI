export function isTauri(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  
  return (
    '__TAURI_INTERNALS__' in window ||
    '__TAURI_IPC__' in window ||
    (window as any).__TAURI_METADATA__ !== undefined
  );
}

export async function getTauriDialog() {
  if (!isTauri()) {
    return null;
  }
  try {
    const { open } = await import('@tauri-apps/api/dialog');
    return open;
  } catch (error) {
    console.error('Failed to load Tauri dialog:', error);
    return null;
  }
}

export async function openFolderDialog(): Promise<string | null> {
  if (isTauri()) {
    try {
      const open = await getTauriDialog();
      if (open) {
        const selected = await open({
          directory: true,
          multiple: false,
          title: "Select Photo Folder",
        });
        
        if (selected === null) {
          return null;
        }
        
        if (typeof selected === "string") {
          return selected;
        } else if (Array.isArray(selected) && selected.length > 0) {
          return selected[0];
        }
      }
    } catch (error) {
      console.error('Tauri dialog error:', error);
      throw error;
    }
  }
  
  const folderPath = prompt(
    "Running in browser mode. Please enter the full path to the photo folder:\n\n" +
    "Example:\n" +
    "  macOS/Linux: /Users/username/Pictures\n" +
    "  Windows: C:\\Users\\username\\Pictures\n\n" +
    "Note: For native folder picker, run the app with 'npm run tauri dev' instead of 'npm run dev'"
  );
  
  return folderPath ? folderPath.trim() : null;
}
