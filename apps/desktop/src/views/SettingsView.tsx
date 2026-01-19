import React, { useEffect, useState } from "react";
import { scanApi, statsApi, healthApi, photosApi } from "../services/api";
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
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [scanMessage, setScanMessage] = useState("");
  const [stats, setStats] = useState<any>(null);
  const [updatingMetadata, setUpdatingMetadata] = useState(false);

  useEffect(() => {
    loadStats();
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

      setScanning(true);
      setScanProgress(0);

      const job = await scanApi.start(folderPath, true);
      let hasRefreshedAfterImport = false;

      const interval = setInterval(async () => {
        try {
          const status = await scanApi.getStatus(job.job_id);
          setScanProgress(status.progress);
          setScanMessage(status.message || "");

          // Refresh photos after import phase completes (photos are now visible)
          if (status.phase === "scanning" && !hasRefreshedAfterImport) {
            hasRefreshedAfterImport = true;
            window.dispatchEvent(new CustomEvent('refresh-photos'));
            await loadStats();
          }

          if (status.status === "completed") {
            clearInterval(interval);
            setScanning(false);
            setScanMessage("");
            await loadStats();
            // Final refresh to show any face/object data
            window.dispatchEvent(new CustomEvent('refresh-photos'));
          } else if (status.status === "error") {
            clearInterval(interval);
            setScanning(false);
            setScanMessage("");
            alert(`Scan failed: ${status.message || "Unknown error"}`);
          }
        } catch (error) {
          console.error("Failed to get scan status:", error);
          clearInterval(interval);
          setScanning(false);
          setScanMessage("");
          alert(`Failed to get scan status: ${error instanceof Error ? error.message : String(error)}`);
        }
      }, 1000);
    } catch (error) {
      console.error("Failed to start scan:", error);
      setScanning(false);
      alert(`Failed to start scan: ${error instanceof Error ? error.message : String(error)}\n\nMake sure the backend API is running at http://localhost:8000`);
    }
  };

  const handleUpdateMetadata = async () => {
    try {
      setUpdatingMetadata(true);
      await photosApi.updateMetadata();
      alert("Metadata update started in the background. Photos will be updated with date information and other metadata. This may take a few minutes.");
      // Refresh stats after a delay
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
      // Check if API is available
      const isHealthy = await healthApi.check();
      if (!isHealthy) {
        alert("Cannot connect to backend API. Please make sure the server is running at http://localhost:8000\n\nStart it with: uvicorn services.api.main:app --reload --port 8000");
        return;
      }

      setScanning(true);
      setScanProgress(0);

      const job = await scanApi.scanFaces();

      const interval = setInterval(async () => {
        try {
          const status = await scanApi.getStatus(job.job_id);
          setScanProgress(status.progress);
          setScanMessage(status.message || "");

          if (status.status === "completed") {
            clearInterval(interval);
            setScanning(false);
            setScanMessage("");
            await loadStats();
            window.dispatchEvent(new CustomEvent('refresh-photos'));
          } else if (status.status === "error") {
            clearInterval(interval);
            setScanning(false);
            setScanMessage("");
            alert(`Face scanning failed: ${status.message || "Unknown error"}`);
          }
        } catch (error) {
          console.error("Failed to get scan status:", error);
          clearInterval(interval);
          setScanning(false);
          setScanMessage("");
          alert(`Failed to get scan status: ${error instanceof Error ? error.message : String(error)}`);
        }
      }, 1000);
    } catch (error) {
      console.error("Failed to start face scanning:", error);
      setScanning(false);
      alert(`Failed to start face scanning: ${error instanceof Error ? error.message : String(error)}\n\nMake sure the backend API is running at http://localhost:8000`);
    }
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
        {/* Appearance Section */}
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

          {/* AI Status Section */}
          <div className="mt-8">
            <div className="flex items-center gap-2 mb-4">
              <RefreshCw size={16} className={`text-brand-primary ${scanning ? 'animate-spin' : ''}`} />
              <h2 className="text-sm font-bold text-light-text-tertiary dark:text-dark-text-tertiary uppercase tracking-widest">
                AI Status
              </h2>
            </div>
            <Card className="p-6">
              <div className="flex items-center gap-4 mb-4">
                <div className="relative">
                  <div className={`w-3 h-3 rounded-full ${scanning ? 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.4)]' : 'bg-light-text-tertiary dark:bg-dark-text-tertiary opacity-30'}`} />
                  {scanning && (
                    <div className="absolute inset-0 w-3 h-3 rounded-full bg-emerald-500 animate-ping opacity-40" />
                  )}
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-light-text-primary dark:text-dark-text-primary">
                    {scanning ? "AI is Processing" : "System Idle"}
                  </h3>
                  <p className="text-sm text-light-text-secondary dark:text-dark-text-secondary">
                    {scanning ? (scanMessage || "Processing images...") : "Ready for next task"}
                  </p>
                </div>
                {scanning && (
                  <div className="text-lg font-black text-brand-primary">
                    {Math.round(scanProgress * 100)}%
                  </div>
                )}
              </div>

              {stats && (
                <div className="flex items-center gap-2 px-3 py-2 bg-light-bg dark:bg-dark-bg/50 rounded-xl border border-light-border dark:border-dark-border">
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
                    disabled={scanning}
                    className="flex items-center gap-2 px-4 py-2 bg-light-bg dark:bg-dark-bg/50 border border-light-border dark:border-dark-border rounded-xl font-bold text-sm hover:border-brand-primary hover:text-brand-primary disabled:opacity-50 transition-all"
                  >
                    {scanning ? (
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

        {/* Database Section */}
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
                  disabled={scanning}
                  className="flex items-center gap-2 px-4 py-2 bg-brand-primary text-white dark:text-black rounded-xl font-bold text-sm hover:bg-brand-secondary disabled:opacity-50 transition-all shadow-lg shadow-brand-primary/20"
                >
                  {scanning ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      <span>{Math.round(scanProgress * 100)}%</span>
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

        {/* System Info Section */}
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

        {/* Tip Section */}
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
