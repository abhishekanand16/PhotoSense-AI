/**
 * PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
 * Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
 */
import React, { useState, useEffect, useRef } from "react";
import { scanApi, healthApi, peopleApi, GlobalScanStatus } from "../services/api";
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
  RefreshCw,
  AlertCircle
} from "lucide-react";

interface HeaderProps {
  onThemeToggle?: () => void;
  onSearch?: (query: string) => void;
  onOpenSettings?: () => void;
}

const Header: React.FC<HeaderProps> = ({ onSearch, onOpenSettings }) => {
  const { theme, toggleTheme } = useTheme();
  const [searchQuery, setSearchQuery] = useState("");
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  const [globalStatus, setGlobalStatus] = useState<GlobalScanStatus>({
    status: "idle",
    total_photos: 0,
    processed_photos: 0,
    progress_percent: 100,
    message: "Ready",
  });
  const lastStatusRef = useRef<GlobalScanStatus["status"]>("idle");
  const lastPhaseRef = useRef<string | null | undefined>(null);
  const lastImportedCountRef = useRef<number>(0);
  const lastKnownActiveStatus = useRef<GlobalScanStatus | null>(null);
  const consecutiveFailures = useRef(0);

  useEffect(() => {
    const pollStatus = async () => {
      try {
        const status = await scanApi.getGlobalStatus();
        setGlobalStatus(status);
        setIsBackendConnected(true);
        consecutiveFailures.current = 0;
        
        // Track last known active scan status for resilience
        if (status.status === "scanning" || status.status === "indexing") {
          lastKnownActiveStatus.current = status;
        } else {
          lastKnownActiveStatus.current = null;
        }
        
        // Refresh photos when scan completes
        if (status.status === "completed" && lastStatusRef.current !== "completed") {
          window.dispatchEvent(new CustomEvent('refresh-photos'));
          window.dispatchEvent(new CustomEvent('refresh-people'));
        }
        
        // Refresh photos when import phase completes (transition to processing)
        // This allows users to see photos immediately after import, before ML processing finishes
        if (status.phase === "processing" && lastPhaseRef.current === "import") {
          window.dispatchEvent(new CustomEvent('refresh-photos'));
        }
        
        // Refresh photos incrementally during import phase (every 10 new photos)
        const importedCount = status.imported_photos || 0;
        if (status.phase === "import" && importedCount > 0) {
          if (importedCount >= lastImportedCountRef.current + 10) {
            window.dispatchEvent(new CustomEvent('refresh-photos'));
            lastImportedCountRef.current = importedCount;
          }
        }
        
        // Reset imported count tracking when scan completes
        if (status.status === "completed" || status.status === "idle") {
          lastImportedCountRef.current = 0;
        }
        
        if (status.status === "error" && lastStatusRef.current !== "error") {
          alert(`Scan failed: ${status.error || status.message || "Unknown error"}`);
        }
        lastStatusRef.current = status.status;
        lastPhaseRef.current = status.phase;
      } catch {
        consecutiveFailures.current += 1;
        
        // If we had an active scan and this is just a temporary timeout (< 3 consecutive failures),
        // keep showing the last known progress instead of "Disconnected"
        if (lastKnownActiveStatus.current && consecutiveFailures.current < 3) {
          // Keep showing the last known scanning status - backend is just busy
          setGlobalStatus(lastKnownActiveStatus.current);
          setIsBackendConnected(true);
        } else {
          // Backend is truly disconnected (multiple failures or no active scan)
          setIsBackendConnected(false);
          lastKnownActiveStatus.current = null;
        }
      }
    };

    pollStatus();

    const interval = setInterval(pollStatus, 1000);

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
      const folderPath = await openFolderDialog();

      if (folderPath === null) {
        return;
      }

      if (folderPath) {
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
      const isHealthy = await healthApi.check();
      if (!isHealthy) {
        alert("Cannot connect to backend API. Please make sure the server is running at http://localhost:8000\n\nStart it with: uvicorn services.api.main:app --reload --port 8000");
        return;
      }

      await scanApi.start(folderPath, true);
    } catch (error) {
      console.error("Failed to start scan:", error);
      alert(`Failed to start scan: ${error instanceof Error ? error.message : String(error)}\n\nMake sure the backend API is running at http://localhost:8000`);
    }
  };
  
  const isScanning = globalStatus.status === "scanning" || globalStatus.status === "indexing";

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearch && searchQuery.trim()) {
      onSearch(searchQuery.trim());
    }
  };

  const formatEta = (seconds?: number | null) => {
    if (!seconds || seconds <= 0) {
      return null;
    }
    const minutes = Math.floor(seconds / 60);
    const remaining = seconds % 60;
    if (minutes <= 0) {
      return `${remaining}s`;
    }
    return `${minutes}m ${remaining}s`;
  };

  const handleRefresh = async () => {
    if (isRefreshing) return;
    
    setIsRefreshing(true);
    try {
      const cleanupResults = await Promise.allSettled([
        peopleApi.cleanupOrphans().then(r => ({ type: 'people', count: r.count })),
        
        fetch('http://localhost:8000/objects/cleanup-orphans', { method: 'POST' })
          .then(r => r.json())
          .then(r => ({ type: 'objects', count: r.deleted_objects })),
        
        fetch('http://localhost:8000/places/cleanup-orphans', { method: 'POST' })
          .then(r => r.json())
          .then(r => ({ type: 'locations', count: r.deleted_locations })),
      ]);
      
      cleanupResults.forEach((result) => {
        if (result.status === 'fulfilled' && result.value.count > 0) {
        }
      });
      
      window.dispatchEvent(new CustomEvent('refresh-photos'));
      window.dispatchEvent(new CustomEvent('refresh-people'));
      window.dispatchEvent(new CustomEvent('refresh-objects'));
      window.dispatchEvent(new CustomEvent('refresh-places'));
      window.dispatchEvent(new CustomEvent('refresh-data'));
      
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
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-3 px-4 py-2 bg-light-bg dark:bg-dark-bg/50 border border-light-border dark:border-dark-border rounded-xl min-w-[180px]">
              {!isBackendConnected ? (
                <>
                  <Circle size={8} className="fill-red-500 text-red-500 animate-pulse" />
                  <span className="text-xs font-bold uppercase tracking-wider text-red-500">
                    Disconnected
                  </span>
                </>
              ) : globalStatus.status === "scanning" || globalStatus.status === "indexing" ? (
                <>
                  <Loader2 size={16} className="text-brand-primary animate-spin flex-shrink-0" />
                  <div className="flex flex-col min-w-0">
                    {globalStatus.phase === "import" ? (
                      // PHASE 1: Import - fast, photos visible immediately
                      <>
                        <span className="text-xs font-bold text-brand-primary">
                          Importing... {globalStatus.processed_photos}/{globalStatus.total_photos}
                        </span>
                        <span className="text-[10px] text-light-text-tertiary dark:text-dark-text-tertiary truncate">
                          {formatEta(globalStatus.eta_seconds) ? `ETA ${formatEta(globalStatus.eta_seconds)}` : "Photos visible after import"}
                        </span>
                      </>
                    ) : globalStatus.phase === "clustering" ? (
                      // PHASE 3: Clustering - organizing faces
                      <>
                        <span className="text-xs font-bold text-brand-primary">
                          Organizing faces...
                        </span>
                        <span className="text-[10px] text-light-text-tertiary dark:text-dark-text-tertiary truncate">
                          Almost done
                        </span>
                      </>
                    ) : (
                      // PHASE 2: ML Processing - AI analysis in background
                      <>
                        <span className="text-xs font-bold text-brand-primary">
                          Analyzing... {globalStatus.processed_photos}/{globalStatus.total_photos}
                        </span>
                        <span className="text-[10px] text-light-text-tertiary dark:text-dark-text-tertiary truncate">
                          {formatEta(globalStatus.eta_seconds) ? `ETA ${formatEta(globalStatus.eta_seconds)}` : "Processing AI features"}
                        </span>
                      </>
                    )}
                  </div>
                </>
              ) : globalStatus.status === "error" ? (
                <>
                  <AlertCircle size={14} className="text-amber-500 flex-shrink-0" />
                  <span className="text-xs font-bold text-amber-500">
                    Scan failed
                  </span>
                </>
              ) : globalStatus.status === "completed" ? (
                <>
                  <Circle size={8} className="fill-emerald-500 text-emerald-500" />
                  <span className="text-xs font-bold uppercase tracking-wider text-light-text-tertiary dark:text-dark-text-tertiary">
                    Up to date
                  </span>
                </>
              ) : globalStatus.total_photos === 0 ? (
                <>
                  <Circle size={8} className="fill-light-text-tertiary dark:fill-dark-text-tertiary text-light-text-tertiary dark:text-dark-text-tertiary" />
                  <span className="text-xs font-bold uppercase tracking-wider text-light-text-tertiary dark:text-dark-text-tertiary">
                    Ready
                  </span>
                </>
              ) : (
                <>
                  <Circle size={8} className="fill-emerald-500 text-emerald-500" />
                  <span className="text-xs font-bold uppercase tracking-wider text-light-text-tertiary dark:text-dark-text-tertiary">
                    Up to date
                  </span>
                </>
              )}
            </div>
            
            {(globalStatus.status === "scanning" || globalStatus.status === "indexing") && (
              <div className="h-1 bg-light-border dark:bg-dark-border rounded-full overflow-hidden mx-1">
                <div 
                  className="h-full bg-brand-primary transition-all duration-300 ease-out"
                  style={{ width: `${globalStatus.progress_percent}%` }}
                />
              </div>
            )}
          </div>

          <div className="h-8 w-[1px] bg-light-border dark:bg-dark-border" />

          <div className="flex items-center gap-2">
            <button
              onClick={handleSelectFolder}
              disabled={isScanning}
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
