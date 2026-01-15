/** Sidebar navigation component. */

import React, { useEffect, useState } from "react";
import { statsApi } from "../services/api";

interface SidebarProps {
  currentPage: string;
  onNavigate: (page: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ currentPage, onNavigate }) => {
  const [stats, setStats] = useState<{
    total_photos: number;
    total_people: number;
    total_objects: number;
  } | null>(null);

  useEffect(() => {
    loadStats();
    // Refresh stats every 5 seconds
    const interval = setInterval(loadStats, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadStats = async () => {
    try {
      const data = await statsApi.get();
      setStats({
        total_photos: data.total_photos || 0,
        total_people: data.total_people || 0,
        total_objects: data.total_objects || 0,
      });
    } catch (error) {
      console.error("Failed to load stats:", error);
      // Set defaults on error
      setStats({
        total_photos: 0,
        total_people: 0,
        total_objects: 0,
      });
    }
  };

  const navItems = [
    { id: "photos", label: "Photos", icon: "🖼️", count: stats?.total_photos ?? 0 },
    { id: "people", label: "People", icon: "👥", count: stats?.total_people ?? 0 },
    { id: "objects", label: "Objects", icon: "📦", count: stats?.total_objects ?? 0 },
    { id: "search", label: "Search", icon: "🔍", count: null },
    { id: "settings", label: "Settings", icon: "⚙️", count: null },
  ];

  return (
    <div className="w-64 bg-dark-surface dark:bg-dark-surface border-r border-dark-border dark:border-dark-border h-full flex flex-col">
      <div className="p-6 border-b border-dark-border dark:border-dark-border">
        <div className="text-3xl mb-2">📸</div>
        <div className="text-xl font-bold text-dark-text-primary dark:text-dark-text-primary">
          PhotoSense-AI
        </div>
        <div className="text-sm text-dark-text-secondary dark:text-dark-text-secondary mt-1">
          Visual Intelligence
        </div>
      </div>

      <nav className="flex-1 p-4">
        <div className="text-xs uppercase tracking-wider text-dark-text-tertiary dark:text-dark-text-tertiary mb-3 px-3">
          Navigation
        </div>
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            className={`w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg mb-1 transition-colors ${
              currentPage === item.id
                ? "bg-blue-600 text-white"
                : "text-dark-text-secondary dark:text-dark-text-secondary hover:bg-dark-border dark:hover:bg-dark-border"
            }`}
          >
            <div className="flex items-center gap-3">
              <span className="text-lg">{item.icon}</span>
              <span className="font-medium">{item.label}</span>
            </div>
            {item.count !== null && (
              <span
                className={`text-sm font-medium ${
                  currentPage === item.id
                    ? "text-white/80"
                    : "text-dark-text-tertiary dark:text-dark-text-tertiary"
                }`}
              >
                {item.count}
              </span>
            )}
          </button>
        ))}
      </nav>

      <div className="p-4 border-t border-dark-border dark:border-dark-border text-center text-xs text-dark-text-tertiary dark:text-dark-text-tertiary">
        <div className="mb-1">🔒 Fully Offline & Private</div>
        <div>© 2024 PhotoSense-AI</div>
      </div>
    </div>
  );
};

export default Sidebar;
