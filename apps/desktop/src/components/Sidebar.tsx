import React, { useEffect, useState } from "react";
import { statsApi } from "../services/api";
import {
  Image,
  Users,
  Box,
  Search,
  Settings,
  ShieldCheck,
  LayoutDashboard
} from "lucide-react";

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
      setStats({ total_photos: 0, total_people: 0, total_objects: 0 });
    }
  };

  const navItems = [
    { id: "photos", label: "Photos", icon: Image, count: stats?.total_photos ?? 0 },
    { id: "people", label: "People", icon: Users, count: stats?.total_people ?? 0 },
    { id: "objects", label: "Objects", icon: Box, count: stats?.total_objects ?? 0 },
    { id: "search", label: "Search", icon: Search, count: null },
    { id: "settings", label: "Settings", icon: Settings, count: null },
  ];

  return (
    <div className="w-72 p-4 h-full flex flex-col gap-4">
      <div className="flex-1 bg-light-surface dark:bg-dark-surface border border-light-border dark:border-dark-border rounded-3xl shadow-soft flex flex-col overflow-hidden">
        {/* Logo Section */}
        <div className="p-8 pb-4">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-brand-primary rounded-xl flex items-center justify-center text-white shadow-lg shadow-brand-primary/20">
              <LayoutDashboard size={24} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-light-text-primary dark:text-dark-text-primary tracking-tight">
                PhotoSense
              </h1>
              <p className="text-[10px] uppercase tracking-[0.2em] font-bold text-brand-primary">
                AI Intelligence
              </p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-4 flex flex-col gap-1">
          <p className="px-4 text-[11px] font-bold uppercase tracking-wider text-light-text-tertiary dark:text-dark-text-tertiary mb-2">
            Library
          </p>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;

            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`group w-full flex items-center justify-between gap-3 px-4 py-3 rounded-2xl transition-all duration-200 ${isActive
                    ? "bg-brand-primary text-white shadow-lg shadow-brand-primary/25"
                    : "text-light-text-secondary dark:text-dark-text-secondary hover:bg-light-bg dark:hover:bg-dark-bg"
                  }`}
              >
                <div className="flex items-center gap-3">
                  <Icon size={20} className={isActive ? "text-white" : "text-brand-primary opacity-70 group-hover:opacity-100"} />
                  <span className="font-semibold text-sm">{item.label}</span>
                </div>
                {item.count !== null && item.count > 0 && (
                  <span
                    className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${isActive
                        ? "bg-white/20 text-white"
                        : "bg-light-bg dark:bg-dark-bg text-light-text-tertiary dark:text-dark-text-tertiary"
                      }`}
                  >
                    {item.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-6 mt-auto">
          <div className="bg-light-bg dark:bg-dark-bg/50 rounded-2xl p-4 border border-light-border dark:border-dark-border">
            <div className="flex items-center gap-2 text-brand-primary mb-1">
              <ShieldCheck size={14} />
              <span className="text-[11px] font-bold uppercase tracking-wider">Privacy First</span>
            </div>
            <p className="text-[10px] text-light-text-tertiary dark:text-dark-text-tertiary leading-relaxed">
              All analysis happens locally on your machine.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
