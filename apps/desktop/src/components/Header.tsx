/** Command bar component with search, Add Photos, and processing indicator. */

import React, { useState, useEffect } from "react";
import { getTheme, setTheme } from "../services/theme";
import { scanApi } from "../services/api";
import { open } from "@tauri-apps/api/dialog";

interface HeaderProps {
  onThemeToggle: () => void;
  onSearch?: (query: string) => void;
}

const Header: React.FC<HeaderProps> = ({ onThemeToggle, onSearch }) => {
  const theme = getTheme();
  const [searchQuery, setSearchQuery] = useState("");
  const [processingStatus, setProcessingStatus] = useState<"idle" | "scanning">("idle");
  const [scanProgress, setScanProgress] = useState(0);

  useEffect(() => {
    // Listen for add photos events
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

      // Poll for status
      const interval = setInterval(async () => {
        try {
          const status = await scanApi.getStatus(job.job_id);
          setScanProgress(status.progress);

          if (status.status === "completed" || status.status === "error") {
            clearInterval(interval);
            setProcessingStatus("idle");
            setScanProgress(0);
            // Refresh the app
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
    <div className="h-16 bg-dark-surface dark:bg-dark-surface border-b border-dark-border dark:border-dark-border flex items-center gap-4 px-6">
      {/* Search bar */}
      <form onSubmit={handleSearchSubmit} className="flex-1 max-w-md">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search photos..."
          disabled={true}
          className="w-full px-4 py-2 bg-dark-bg dark:bg-dark-bg border border-dark-border dark:border-dark-border rounded-lg text-dark-text-primary dark:text-dark-text-primary placeholder-dark-text-tertiary focus:outline-none focus:ring-2 focus:ring-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
        />
      </form>

      {/* Add Photos button */}
      <button
        onClick={handleSelectFolder}
        disabled={processingStatus === "scanning"}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
      >
        Add Photos
      </button>

      {/* Processing indicator */}
      <div className="flex items-center gap-2 min-w-[120px]">
        {processingStatus === "scanning" ? (
          <div className="flex items-center gap-2 text-sm text-dark-text-secondary dark:text-dark-text-secondary">
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
            <span>Scanning {Math.round(scanProgress * 100)}%</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-sm text-dark-text-tertiary dark:text-dark-text-tertiary">
            <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
            <span>Idle</span>
          </div>
        )}
      </div>

      {/* Theme toggle */}
      <button
        onClick={onThemeToggle}
        className="p-2 rounded-lg hover:bg-dark-border dark:hover:bg-dark-border transition-colors"
        title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      >
        {theme === "dark" ? "☀️" : "🌙"}
      </button>
    </div>
  );
};

export default Header;
