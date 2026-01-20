import React, { useState, useEffect } from "react";
import { scanApi, healthApi, peopleApi } from "../services/api";
import { openFolderDialog } from "../utils/tauri";
import { useTheme } from "./common/ThemeProvider";
import {
  Sun,
  Moon,
  Search,
  Plus,
  Loader2,
  Settings as SettingsIcon,
  Circle,
  RefreshCw
} from "lucide-react";

interface HeaderProps {
  onThemeToggle?: () => void;
  onSearch?: (query: string) => void;
  onOpenSettings?: () => void;
}

const Header: React.FC<HeaderProps> = ({ onSearch, onOpenSettings }) => {
  const { theme, toggleTheme } = useTheme();
  const [searchQuery, setSearchQuery] = useState("");
  const [processingStatus, setProcessingStatus] = useState<"idle" | "scanning">("idle");
  const [scanProgress, setScanProgress] = useState(0);
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Check backend connection status periodically
  useEffect(() => {
    const checkConnection = async () => {
      const connected = await healthApi.check();
      setIsBackendConnected(connected);
    };

    // Check immediately on mount
    checkConnection();

    // Check every 5 seconds
    const interval = setInterval(checkConnection, 5000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleAddPhotos = async () => {
      await handleSelectFolder();
    };
    window.addEventListener('open-add-photos', handleAddPhotos);
    return () => window.removeEventListener('open-add-photos', handleAddPhotos);
  }, []);

  const handleSelectFolder = async () => {
    try {
      console.log("Opening folder dialog...");
      const folderPath = await openFolderDialog();

      if (folderPath === null) {
        // User cancelled the dialog
        console.log("User cancelled folder selection");
        return;
      }

      if (folderPath) {
        console.log("Selected folder:", folderPath);
        await handleScan(folderPath);
      } else {
        console.error("Invalid folder selection");
        alert("Invalid folder selection. Please try again.");
      }
    } catch (error) {
      console.error("Failed to select folder:", error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      alert(`Failed to select folder: ${errorMessage}\n\nIf this persists, check the browser console for more details.`);
    }
  };

  const handleScan = async (folderPath: string) => {
    try {
      // Check if API is available
      const isHealthy = await healthApi.check();
      if (!isHealthy) {
        alert("Cannot connect to backend API. Please make sure the server is running at http://localhost:8000\n\nStart it with: uvicorn services.api.main:app --reload --port 8000");
        return;
      }

      setProcessingStatus("scanning");
      setScanProgress(0);

      const job = await scanApi.start(folderPath, true);

      const interval = setInterval(async () => {
        try {
          const status = await scanApi.getStatus(job.job_id);
          setScanProgress(status.progress);

          if (status.status === "completed") {
            clearInterval(interval);
            setProcessingStatus("idle");
            setScanProgress(0);
            // Reload after a short delay to show completion
            setTimeout(() => {
              window.location.reload();
            }, 500);
          } else if (status.status === "error") {
            clearInterval(interval);
            setProcessingStatus("idle");
            setScanProgress(0);
            alert(`Scan failed: ${status.message || "Unknown error"}`);
          }
        } catch (error) {
          console.error("Failed to get scan status:", error);
          clearInterval(interval);
          setProcessingStatus("idle");
          setScanProgress(0);
          alert(`Failed to get scan status: ${error instanceof Error ? error.message : String(error)}`);
        }
      }, 1000);
    } catch (error) {
      console.error("Failed to start scan:", error);
      setProcessingStatus("idle");
      setScanProgress(0);
      alert(`Failed to start scan: ${error instanceof Error ? error.message : String(error)}\n\nMake sure the backend API is running at http://localhost:8000`);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearch && searchQuery.trim()) {
      onSearch(searchQuery.trim());
    }
  };

  const handleRefresh = async () => {
    if (isRefreshing) return;
    
    setIsRefreshing(true);
    try {
      // Run all cleanups in parallel for speed
      const cleanupResults = await Promise.allSettled([
        // Clean up orphaned people (0 faces)
        peopleApi.cleanupOrphans().then(r => ({ type: 'people', count: r.count })),
        
        // Clean up orphaned objects (deleted photos)
        fetch('http://localhost:8000/objects/cleanup-orphans', { method: 'POST' })
          .then(r => r.json())
          .then(r => ({ type: 'objects', count: r.deleted_objects })),
        
        // Clean up orphaned locations (deleted photos)
        fetch('http://localhost:8000/places/cleanup-orphans', { method: 'POST' })
          .then(r => r.json())
          .then(r => ({ type: 'locations', count: r.deleted_locations })),
      ]);
      
      // Log cleanup results
      cleanupResults.forEach((result) => {
        if (result.status === 'fulfilled' && result.value.count > 0) {
          console.log(`Cleaned up ${result.value.count} orphaned ${result.value.type}`);
        }
      });
      
      // Dispatch refresh events for all views
      window.dispatchEvent(new CustomEvent('refresh-photos'));
      window.dispatchEvent(new CustomEvent('refresh-people'));
      window.dispatchEvent(new CustomEvent('refresh-objects'));
      window.dispatchEvent(new CustomEvent('refresh-places'));
      window.dispatchEvent(new CustomEvent('refresh-data'));
      
      // Small delay for visual feedback
      await new Promise(resolve => setTimeout(resolve, 500));
    } catch (error) {
      console.error('Refresh failed:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="h-20 flex items-center gap-4 px-8 mt-4 sticky top-0 z-10">
      <div className="flex-1 h-full bg-light-surface/80 dark:bg-dark-surface/80 backdrop-blur-xl border border-light-border dark:border-dark-border rounded-2xl shadow-soft flex items-center gap-6 px-6">

        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="flex-1 max-w-xl group">
          <div className="relative flex items-center">
            <Search className="absolute left-3 w-4 h-4 text-light-text-tertiary dark:text-dark-text-tertiary group-focus-within:text-brand-primary transition-colors" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search your memories..."
              className="w-full pl-10 pr-4 py-2.5 bg-light-bg dark:bg-dark-bg/50 border border-light-border dark:border-dark-border rounded-xl text-sm text-light-text-primary dark:text-dark-text-primary placeholder-light-text-tertiary dark:placeholder-dark-text-tertiary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all"
            />
          </div>
        </form>

        <div className="flex items-center gap-4">
          {/* Status */}
          <div className="flex items-center gap-3 px-4 py-2 bg-light-bg dark:bg-dark-bg/50 border border-light-border dark:border-dark-border rounded-xl">
            {processingStatus === "scanning" ? (
              <>
                <Loader2 size={16} className="text-brand-primary animate-spin" />
                <span className="text-xs font-bold text-light-text-secondary dark:text-dark-text-secondary">
                  {Math.round(scanProgress * 100)}%
                </span>
              </>
            ) : (
              <>
                <Circle 
                  size={8} 
                  className={isBackendConnected 
                    ? "fill-emerald-500 text-emerald-500" 
                    : "fill-red-500 text-red-500"
                  } 
                />
                <span className={`text-xs font-bold uppercase tracking-wider ${isBackendConnected ? "text-light-text-tertiary dark:text-dark-text-tertiary" : "text-red-500"}`}>
                  {isBackendConnected ? "Ready" : "Disconnected"}
                </span>
              </>
            )}
          </div>

          <div className="h-8 w-[1px] bg-light-border dark:bg-dark-border" />

          {/* Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleSelectFolder}
              disabled={processingStatus === "scanning"}
              className="flex items-center gap-2 px-4 py-2.5 bg-brand-primary text-white dark:text-black rounded-xl hover:bg-brand-secondary disabled:opacity-50 transition-all shadow-lg shadow-brand-primary/20 font-bold text-sm"
            >
              <Plus size={18} />
              <span>Import</span>
            </button>

            <button
              onClick={toggleTheme}
              className="p-2.5 bg-light-bg dark:bg-dark-bg/50 border border-light-border dark:border-dark-border rounded-xl text-light-text-secondary dark:text-dark-text-secondary hover:text-brand-primary hover:border-brand-primary transition-all"
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            >
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>

            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="p-2.5 bg-light-bg dark:bg-dark-bg/50 border border-light-border dark:border-dark-border rounded-xl text-light-text-secondary dark:text-dark-text-secondary hover:text-brand-primary hover:border-brand-primary transition-all disabled:opacity-50"
              title="Refresh & cleanup"
            >
              <RefreshCw size={18} className={isRefreshing ? 'animate-spin' : ''} />
            </button>

            {onOpenSettings && (
              <button
                onClick={onOpenSettings}
                className="p-2.5 bg-light-bg dark:bg-dark-bg/50 border border-light-border dark:border-dark-border rounded-xl text-light-text-secondary dark:text-dark-text-secondary hover:text-brand-primary hover:border-brand-primary transition-all"
                title="Settings"
              >
                <SettingsIcon size={18} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Header;
