import React, { useEffect, useState, useRef } from "react";
import { scanApi, statsApi, healthApi, photosApi, GlobalScanStatus } from "../services/api";
import { openFolderDialog } from "../utils/tauri";
import { useTheme } from "../components/common/ThemeProvider";
import {
  Settings as SettingsIcon,
  Moon,
  Sun,
  Database,
  Shield,
  Cpu,
  FolderPlus,
  BarChart3,
  Loader2,
  RefreshCw,
  Scan
} from "lucide-react";
import Card from "../components/common/Card";

const SettingsView: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const [, setIsBackendConnected] = useState(false);
  const [globalStatus, setGlobalStatus] = useState<GlobalScanStatus>({
    status: "idle",
    total_photos: 0,
    processed_photos: 0,
    progress_percent: 100,
    message: "Ready",
  });
  const [stats, setStats] = useState<any>(null);
  const [updatingMetadata, setUpdatingMetadata] = useState(false);
  const lastStatusRef = useRef<GlobalScanStatus["status"]>("idle");
  const lastKnownActiveStatus = useRef<GlobalScanStatus | null>(null);
  const consecutiveFailures = useRef(0);

  useEffect(() => {
    loadStats();
  }, []);

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
        
        if (status.status === "completed" && lastStatusRef.current !== "completed") {
          await loadStats();
          window.dispatchEvent(new CustomEvent('refresh-photos'));
        }
        if (status.status === "error" && lastStatusRef.current !== "error") {
          alert(`Scan failed: ${status.error || status.message || "Unknown error"}`);
        }
        lastStatusRef.current = status.status;
      } catch {
        consecutiveFailures.current += 1;
        
        // If we had an active scan and this is just a temporary timeout,
        // keep showing the last known progress instead of "Disconnected"
        if (lastKnownActiveStatus.current && consecutiveFailures.current < 3) {
          setGlobalStatus(lastKnownActiveStatus.current);
          setIsBackendConnected(true);
        } else {
          setIsBackendConnected(false);
          lastKnownActiveStatus.current = null;
        }
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, 1000);
    return () => clearInterval(interval);
  }, []);

  const loadStats = async () => {
    try {
      const data = await statsApi.get();
      setStats(data);
    } catch (error) {
      console.error("Failed to load stats:", error);
    }
  };

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

  const handleUpdateMetadata = async () => {
    try {
      setUpdatingMetadata(true);
      await photosApi.updateMetadata();
      alert("Metadata update started in the background. Photos will be updated with date information and other metadata. This may take a few minutes.");
      setTimeout(async () => {
        await loadStats();
        window.dispatchEvent(new CustomEvent('refresh-photos'));
      }, 2000);
    } catch (error) {
      console.error("Failed to update metadata:", error);
      alert(`Failed to update metadata: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setUpdatingMetadata(false);
    }
  };

  const handleScanFaces = async () => {
    try {
      const isHealthy = await healthApi.check();
      if (!isHealthy) {
        alert("Cannot connect to backend API. Please make sure the server is running at http://localhost:8000\n\nStart it with: uvicorn services.api.main:app --reload --port 8000");
        return;
      }

      await scanApi.scanFaces();
    } catch (error) {
      console.error("Failed to start face scanning:", error);
      alert(`Failed to start face scanning: ${error instanceof Error ? error.message : String(error)}\n\nMake sure the backend API is running at http://localhost:8000`);
    }
  };

  const isScanning = globalStatus.status === "scanning" || globalStatus.status === "indexing";

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

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <SettingsIcon className="text-brand-primary" size={24} />
          <h1 className="text-3xl font-black text-light-text-primary dark:text-dark-text-primary tracking-tight">
            Settings
          </h1>
        </div>
        <p className="text-light-text-secondary dark:text-dark-text-secondary font-medium">
          Manage your library, appearance, and privacy preferences.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-5xl">
        <section>
          <div className="flex items-center gap-2 mb-4">
            <Sun size={16} className="text-brand-primary" />
            <h2 className="text-sm font-bold text-light-text-tertiary dark:text-dark-text-tertiary uppercase tracking-widest">
              Appearance
            </h2>
          </div>
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-light-text-primary dark:text-dark-text-primary mb-1">Theme</h3>
                <p className="text-sm text-light-text-secondary dark:text-dark-text-secondary">
                  Choose between light and dark mode
                </p>
              </div>
              <button
                onClick={toggleTheme}
                className="flex items-center gap-2 px-4 py-2 bg-light-bg dark:bg-dark-bg/50 border border-light-border dark:border-dark-border rounded-xl font-bold text-sm hover:border-brand-primary hover:text-brand-primary transition-all"
              >
                {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
                <span>{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>
              </button>
            </div>
          </Card>

          <div className="mt-8">
            <div className="flex items-center gap-2 mb-4">
              <RefreshCw size={16} className={`text-brand-primary ${isScanning ? 'animate-spin' : ''}`} />
              <h2 className="text-sm font-bold text-light-text-tertiary dark:text-dark-text-tertiary uppercase tracking-widest">
                AI Status
              </h2>
            </div>
            <Card className={`p-6 relative overflow-hidden transition-all duration-500 ${isScanning ? 'border-brand-primary/50 shadow-lg shadow-brand-primary/10' : ''}`}>
              {/* Animated background gradient when scanning */}
              {isScanning && (
                <div className="absolute inset-0 overflow-hidden">
                  <div 
                    className="absolute inset-0 bg-gradient-to-r from-transparent via-brand-primary/5 to-transparent"
                    style={{
                      animation: 'shimmer 2s ease-in-out infinite',
                    }}
                  />
                  <div 
                    className="absolute bottom-0 left-0 h-1 bg-gradient-to-r from-brand-primary via-brand-secondary to-brand-primary rounded-full"
                    style={{
                      width: `${globalStatus.progress_percent}%`,
                      transition: 'width 0.5s ease-out',
                      boxShadow: '0 0 10px rgba(var(--brand-primary-rgb, 99, 102, 241), 0.5)',
                    }}
                  />
                </div>
              )}
              
              <div className="flex items-center gap-4 mb-4 relative z-10">
                <div className="relative">
                  {isScanning ? (
                    <div className="relative w-12 h-12 flex items-center justify-center">
                      {/* Outer rotating ring */}
                      <div 
                        className="absolute inset-0 rounded-full border-2 border-transparent border-t-brand-primary border-r-brand-primary/50"
                        style={{ animation: 'spin 1.5s linear infinite' }}
                      />
                      {/* Middle pulsing ring */}
                      <div 
                        className="absolute inset-1 rounded-full border-2 border-transparent border-b-brand-secondary border-l-brand-secondary/50"
                        style={{ animation: 'spin 2s linear infinite reverse' }}
                      />
                      {/* Center icon */}
                      <Cpu size={18} className="text-brand-primary animate-pulse" />
                    </div>
                  ) : (
                    <div className={`w-3 h-3 rounded-full ${globalStatus.status === 'error' ? 'bg-red-500' : globalStatus.status === 'completed' || globalStatus.total_photos > 0 ? 'bg-emerald-500' : 'bg-light-text-tertiary dark:bg-dark-text-tertiary opacity-30'}`} />
                  )}
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-light-text-primary dark:text-dark-text-primary">
                    {isScanning
                      ? "AI is Processing"
                      : globalStatus.status === "error"
                        ? "Scan failed"
                        : globalStatus.status === "completed"
                          ? "Up to date"
                          : globalStatus.total_photos === 0
                            ? "Ready"
                            : "Up to date"}
                  </h3>
                  <p className="text-sm text-light-text-secondary dark:text-dark-text-secondary">
                    {isScanning
                      ? `${globalStatus.message || "Processing images..."}${formatEta(globalStatus.eta_seconds) ? ` • ETA ${formatEta(globalStatus.eta_seconds)}` : ""}`
                      : globalStatus.status === "error"
                        ? (globalStatus.error || globalStatus.message || "Scan failed")
                        : globalStatus.total_photos === 0
                          ? "Import photos to get started"
                          : "All photos processed"}
                  </p>
                </div>
                {isScanning && (
                  <div className="flex flex-col items-end">
                    <div className="text-2xl font-black text-brand-primary tabular-nums">
                      {globalStatus.progress_percent}%
                    </div>
                    <div className="text-xs text-light-text-tertiary dark:text-dark-text-tertiary">
                      {globalStatus.processed_photos}/{globalStatus.total_photos}
                    </div>
                  </div>
                )}
              </div>

              {/* Progress bar when scanning */}
              {isScanning && (
                <div className="mb-4 relative z-10">
                  <div className="h-2 bg-light-bg dark:bg-dark-bg/50 rounded-full overflow-hidden border border-light-border dark:border-dark-border">
                    <div 
                      className="h-full bg-gradient-to-r from-brand-primary to-brand-secondary rounded-full relative"
                      style={{
                        width: `${globalStatus.progress_percent}%`,
                        transition: 'width 0.5s ease-out',
                      }}
                    >
                      {/* Animated shine effect on progress bar */}
                      <div 
                        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                        style={{
                          animation: 'shimmer 1.5s ease-in-out infinite',
                        }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {stats && !isScanning && (
                <div className="flex items-center gap-2 px-3 py-2 bg-light-bg dark:bg-dark-bg/50 rounded-xl border border-light-border dark:border-dark-border relative z-10">
                  <BarChart3 size={14} className="text-brand-primary" />
                  <span className="text-xs font-medium text-light-text-secondary dark:text-dark-text-secondary">
                    Photos Processed:
                  </span>
                  <span className="text-sm font-bold text-brand-primary">{stats.total_photos}</span>
                </div>
              )}

              <div className="pt-4 border-t border-light-border dark:border-dark-border">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-light-text-primary dark:text-dark-text-primary mb-1">Scan Faces</h3>
                    <p className="text-sm text-light-text-secondary dark:text-dark-text-secondary">
                      Run face recognition on imported photos
                    </p>
                  </div>
                  <button
                    onClick={handleScanFaces}
                    disabled={isScanning}
                    className="flex items-center gap-2 px-4 py-2 bg-light-bg dark:bg-dark-bg/50 border border-light-border dark:border-dark-border rounded-xl font-bold text-sm hover:border-brand-primary hover:text-brand-primary disabled:opacity-50 transition-all"
                  >
                    {isScanning ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        <span>Scanning...</span>
                      </>
                    ) : (
                      <>
                        <Scan size={16} />
                        <span>Start Scan</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </Card>
          </div>
        </section>

        <section>
          <div className="flex items-center gap-2 mb-4">
            <Database size={16} className="text-brand-primary" />
            <h2 className="text-sm font-bold text-light-text-tertiary dark:text-dark-text-tertiary uppercase tracking-widest">
              Library Control
            </h2>
          </div>
          <Card className="p-6">
            <div className="flex flex-col gap-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-light-text-primary dark:text-dark-text-primary mb-1">Index Repository</h3>
                  <p className="text-sm text-light-text-secondary dark:text-dark-text-secondary">
                    Reprocess your photo library
                  </p>
                </div>
                <button
                  onClick={handleSelectFolder}
                  disabled={isScanning}
                  className="flex items-center gap-2 px-4 py-2 bg-brand-primary text-white dark:text-black rounded-xl font-bold text-sm hover:bg-brand-secondary disabled:opacity-50 transition-all shadow-lg shadow-brand-primary/20"
                >
                  {isScanning ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      <span>{globalStatus.progress_percent}%</span>
                    </>
                  ) : (
                    <>
                      <FolderPlus size={16} />
                      <span>Import Photos</span>
                    </>
                  )}
                </button>
              </div>

              <div className="flex items-center justify-between pt-4 border-t border-light-border dark:border-dark-border">
                <div>
                  <h3 className="font-bold text-light-text-primary dark:text-dark-text-primary mb-1">Update Metadata</h3>
                  <p className="text-sm text-light-text-secondary dark:text-dark-text-secondary">
                    Extract date and camera info from existing photos
                  </p>
                </div>
                <button
                  onClick={handleUpdateMetadata}
                  disabled={updatingMetadata}
                  className="flex items-center gap-2 px-4 py-2 bg-light-bg dark:bg-dark-bg/50 border border-light-border dark:border-dark-border rounded-xl font-bold text-sm hover:border-brand-primary hover:text-brand-primary disabled:opacity-50 transition-all"
                >
                  {updatingMetadata ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      <span>Updating...</span>
                    </>
                  ) : (
                    <>
                      <RefreshCw size={16} />
                      <span>Update</span>
                    </>
                  )}
                </button>
              </div>

              {stats && (
                <div className="grid grid-cols-2 gap-4 mt-2">
                  <div className="p-4 bg-light-bg dark:bg-dark-bg/50 rounded-2xl border border-light-border dark:border-dark-border">
                    <div className="text-xs font-bold text-light-text-tertiary dark:text-dark-text-tertiary uppercase tracking-widest mb-1">Photos</div>
                    <div className="text-2xl font-black text-brand-primary">{stats.total_photos}</div>
                  </div>
                  <div className="p-4 bg-light-bg dark:bg-dark-bg/50 rounded-2xl border border-light-border dark:border-dark-border">
                    <div className="text-xs font-bold text-light-text-tertiary dark:text-dark-text-tertiary uppercase tracking-widest mb-1">People</div>
                    <div className="text-2xl font-black text-brand-primary">{stats.total_people}</div>
                  </div>
                </div>
              )}
            </div>
          </Card>
        </section>

        <section>
          <div className="flex items-center gap-2 mb-4">
            <Cpu size={16} className="text-brand-primary" />
            <h2 className="text-sm font-bold text-light-text-tertiary dark:text-dark-text-tertiary uppercase tracking-widest">
              Engine Status
            </h2>
          </div>
          <Card className="p-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between py-2 border-b border-light-border dark:border-dark-border">
                <span className="text-sm font-medium text-light-text-secondary dark:text-dark-text-secondary">AI Core</span>
                <span className="text-xs font-bold text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-full">ACTIVE</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-light-border dark:border-dark-border">
                <span className="text-sm font-medium text-light-text-secondary dark:text-dark-text-secondary">Privacy Masking</span>
                <span className="text-xs font-bold text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-full">VERIFIED</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm font-medium text-light-text-secondary dark:text-dark-text-secondary">Version</span>
                <span className="text-xs font-bold text-light-text-tertiary dark:text-dark-text-tertiary">1.0.0-PROD</span>
              </div>
            </div>
          </Card>
        </section>

        <section>
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 size={16} className="text-brand-primary" />
            <h2 className="text-sm font-bold text-light-text-tertiary dark:text-dark-text-tertiary uppercase tracking-widest">
              Insight
            </h2>
          </div>
          <div className="p-6 bg-brand-primary/10 rounded-3xl border border-brand-primary/20">
            <h3 className="flex items-center gap-2 font-bold text-brand-primary mb-2">
              <Shield size={18} />
              Privacy Note
            </h3>
            <p className="text-sm text-light-text-secondary dark:text-dark-text-secondary leading-relaxed">
              PhotoSense-AI processed your images locally. No data is sent to the cloud. Your memories remain yours, and yours alone.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
};

export default SettingsView;
