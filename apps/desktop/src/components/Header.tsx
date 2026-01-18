import React, { useState, useEffect } from "react";
import { scanApi } from "../services/api";
import { open } from "@tauri-apps/api/dialog";
import { useTheme } from "./common/ThemeProvider";
import {
  Sun,
  Moon,
  Search,
  Plus,
  Loader2,
  Settings as SettingsIcon,
  Circle
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

  useEffect(() => {
    const handleAddPhotos = async () => {
      await handleSelectFolder();
    };
    window.addEventListener('open-add-photos', handleAddPhotos);
    return () => window.removeEventListener('open-add-photos', handleAddPhotos);
  }, []);

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
      setProcessingStatus("scanning");
      setScanProgress(0);

      const job = await scanApi.start(folderPath, true);

      const interval = setInterval(async () => {
        try {
          const status = await scanApi.getStatus(job.job_id);
          setScanProgress(status.progress);

          if (status.status === "completed" || status.status === "error") {
            clearInterval(interval);
            setProcessingStatus("idle");
            setScanProgress(0);
            window.location.reload();
          }
        } catch (error) {
          console.error("Failed to get scan status:", error);
          setProcessingStatus("idle");
        }
      }, 1000);
    } catch (error) {
      console.error("Failed to start scan:", error);
      setProcessingStatus("idle");
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearch && searchQuery.trim()) {
      onSearch(searchQuery.trim());
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
                <Circle size={8} className="fill-emerald-500 text-emerald-500" />
                <span className="text-xs font-bold text-light-text-tertiary dark:text-dark-text-tertiary uppercase tracking-wider">
                  Ready
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
