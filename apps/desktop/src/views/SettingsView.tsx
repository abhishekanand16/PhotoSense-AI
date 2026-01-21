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
  Scan,
  HelpCircle,
  ChevronDown,
  ChevronUp
} from "lucide-react";
import Card from "../components/common/Card";

const SettingsView: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [globalStatus, setGlobalStatus] = useState<GlobalScanStatus>({
    status: "idle",
    total_photos: 0,
    processed_photos: 0,
    progress_percent: 100,
    message: "Ready",
  });
  const [stats, setStats] = useState<any>(null);
  const [updatingMetadata, setUpdatingMetadata] = useState(false);
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);
  const lastStatusRef = useRef<GlobalScanStatus["status"]>("idle");
  const lastKnownActiveStatus = useRef<GlobalScanStatus | null>(null);
  const consecutiveFailures = useRef(0);

  const faqItems = [
    {
      question: "How do I add photos to my library?",
      answer: "Click the 'Import' button in the top header or go to Settings and click 'Import Photos'. Select a folder containing your photos, and the app will automatically scan and organize them for you."
    },
    {
      question: "Why are some faces not detected?",
      answer: "Face detection works best with clear, front-facing photos. Very small faces, heavily obscured faces, or unusual angles might not be detected. You can try running 'Scan Faces' again from Settings to re-process your photos."
    },
    {
      question: "How do I rename a person?",
      answer: "Go to the People tab, hover over the person you want to rename, and click the small edit (pencil) icon next to their name. Type the new name and press Enter or click the checkmark to save."
    },
    {
      question: "Is my data private and secure?",
      answer: "Yes! PhotoSense-AI processes all your photos locally on your device. No images or personal data are ever uploaded to the cloud. Your memories stay completely private on your computer."
    },
    {
      question: "What does 'Disconnected' status mean?",
      answer: "If you see 'Disconnected' in red, it means the backend server isn't running. The app needs the server to process photos. Make sure to start it before using the app's features."
    },
    {
      question: "How do I search for specific photos?",
      answer: "Use the search bar at the top of the app. You can search by objects (like 'dog', 'car'), scenes (like 'beach', 'sunset'), or even descriptions like 'person wearing red shirt'. The AI will find matching photos."
    },
    {
      question: "Why is processing taking a long time?",
      answer: "Processing time depends on the number of photos and your computer's speed. The AI analyzes each photo for faces, objects, and scenes. Large libraries may take several minutes. You can see the progress in the header."
    },
    {
      question: "Can I delete photos from the app?",
      answer: "Yes, you can delete photos from the app. When you delete a photo, it removes both the index entry AND the original file from your computer. Be careful - this action cannot be undone."
    }
  ];

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
            <Card className="p-6">
              <div className="flex items-center gap-4 mb-4">
                <div className="relative">
                  <div className={`w-3 h-3 rounded-full ${isScanning ? 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.4)]' : 'bg-light-text-tertiary dark:bg-dark-text-tertiary opacity-30'}`} />
                  {isScanning && (
                    <div className="absolute inset-0 w-3 h-3 rounded-full bg-emerald-500 animate-ping opacity-40" />
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
                  <div className="text-lg font-black text-brand-primary">
                    {globalStatus.progress_percent}%
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

      <div className="mt-12 max-w-5xl">
        <div className="flex items-center gap-2 mb-4">
          <HelpCircle size={16} className="text-brand-primary" />
          <h2 className="text-sm font-bold text-light-text-tertiary dark:text-dark-text-tertiary uppercase tracking-widest">
            Help & FAQ
          </h2>
        </div>
        <Card className="p-6">
          <div className="space-y-2">
            {faqItems.map((item, index) => (
              <div 
                key={index}
                className="border border-light-border dark:border-dark-border rounded-xl overflow-hidden"
              >
                <button
                  onClick={() => setExpandedFaq(expandedFaq === index ? null : index)}
                  className="w-full flex items-center justify-between p-4 text-left hover:bg-light-bg dark:hover:bg-dark-bg/50 transition-colors"
                >
                  <span className="font-bold text-light-text-primary dark:text-dark-text-primary pr-4">
                    {item.question}
                  </span>
                  {expandedFaq === index ? (
                    <ChevronUp size={18} className="text-brand-primary flex-shrink-0" />
                  ) : (
                    <ChevronDown size={18} className="text-light-text-tertiary dark:text-dark-text-tertiary flex-shrink-0" />
                  )}
                </button>
                {expandedFaq === index && (
                  <div className="px-4 pb-4 animate-in fade-in slide-in-from-top-2 duration-200">
                    <p className="text-sm text-light-text-secondary dark:text-dark-text-secondary leading-relaxed">
                      {item.answer}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default SettingsView;
