import React, { useEffect, useState } from "react";
import { scanApi, statsApi } from "../services/api";
import { open } from "@tauri-apps/api/dialog";
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
  Loader2
} from "lucide-react";
import Card from "../components/common/Card";

const SettingsView: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [stats, setStats] = useState<any>(null);

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
      const selected = await open({
        directory: true,
        multiple: false,
      });

      if (selected && typeof selected === "string") {
        await handleScan(selected);
      }
    } catch (error) {
      console.error("Failed to select folder:", error);
    }
  };

  const handleScan = async (folderPath: string) => {
    try {
      setScanning(true);
      setScanProgress(0);

      const job = await scanApi.start(folderPath, true);

      const interval = setInterval(async () => {
        try {
          const status = await scanApi.getStatus(job.job_id);
          setScanProgress(status.progress);

          if (status.status === "completed" || status.status === "error") {
            clearInterval(interval);
            setScanning(false);
            if (status.status === "completed") {
              await loadStats();
            }
          }
        } catch (error) {
          console.error("Failed to get scan status:", error);
        }
      }, 1000);
    } catch (error) {
      console.error("Failed to start scan:", error);
      setScanning(false);
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
