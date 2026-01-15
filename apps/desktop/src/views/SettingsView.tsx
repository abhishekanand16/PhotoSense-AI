/** Settings view. */

import React, { useEffect, useState } from "react";
import { scanApi, statsApi } from "../services/api";
import { getTheme, setTheme } from "../services/theme";
import { open } from "@tauri-apps/api/dialog";

const SettingsView: React.FC = () => {
  const [theme, setThemeState] = useState<"dark" | "light">(getTheme());
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

  const handleThemeToggle = () => {
    const newTheme = theme === "dark" ? "light" : "dark";
    setTheme(newTheme);
    setThemeState(newTheme);
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

      // Poll for status
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
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-dark-text-primary dark:text-dark-text-primary mb-1">
          Settings
        </h1>
        <p className="text-dark-text-secondary dark:text-dark-text-secondary">
          Power-user settings and preferences
        </p>
      </div>

      <div className="space-y-6 max-w-2xl">
        <div className="bg-dark-surface dark:bg-dark-surface border border-dark-border dark:border-dark-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-dark-text-primary dark:text-dark-text-primary mb-4">
            Appearance
          </h2>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-dark-text-primary dark:text-dark-text-primary font-medium">
                Theme
              </div>
              <div className="text-sm text-dark-text-secondary dark:text-dark-text-secondary">
                {theme === "dark" ? "Dark mode" : "Light mode"}
              </div>
            </div>
            <button
              onClick={handleThemeToggle}
              className="px-4 py-2 bg-dark-border dark:bg-dark-border rounded-lg text-dark-text-secondary dark:text-dark-text-secondary hover:bg-dark-border/80"
            >
              {theme === "dark" ? "☀️ Light" : "🌙 Dark"}
            </button>
          </div>
        </div>

        <div className="bg-dark-surface dark:bg-dark-surface border border-dark-border dark:border-dark-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-dark-text-primary dark:text-dark-text-primary mb-4">
            Library
          </h2>
          <div className="space-y-4">
            <button
              onClick={handleSelectFolder}
              disabled={scanning}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {scanning ? `Scanning... ${Math.round(scanProgress * 100)}%` : "Add Photos"}
            </button>

            {stats && (
              <div className="grid grid-cols-2 gap-4 mt-4">
                <div className="text-center p-4 bg-dark-bg dark:bg-dark-bg rounded-lg">
                  <div className="text-2xl font-bold text-dark-text-primary dark:text-dark-text-primary">
                    {stats.total_photos}
                  </div>
                  <div className="text-sm text-dark-text-secondary dark:text-dark-text-secondary">
                    Photos
                  </div>
                </div>
                <div className="text-center p-4 bg-dark-bg dark:bg-dark-bg rounded-lg">
                  <div className="text-2xl font-bold text-dark-text-primary dark:text-dark-text-primary">
                    {stats.total_people}
                  </div>
                  <div className="text-sm text-dark-text-secondary dark:text-dark-text-secondary">
                    People
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsView;
