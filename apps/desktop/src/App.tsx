/**
 * PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
 * Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
 */
import React, { useState, useEffect } from "react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import SetupScreen from "./components/SetupScreen";
import ObjectsView from "./views/ObjectsView";
import PeopleView from "./views/PeopleView";
import PhotosView from "./views/PhotosView";
import PlacesView from "./views/PlacesView";
import SearchView from "./views/SearchView";
import SettingsView from "./views/SettingsView";
import HelpView from "./views/HelpView";
import { ThemeProvider } from "./components/common/ThemeProvider";
import { modelsApi, healthApi } from "./services/api";

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState("photos");
  const [showSetup, setShowSetup] = useState(false);
  const [checkingSetup, setCheckingSetup] = useState(true);

  // Check if setup is needed on startup
  useEffect(() => {
    const checkSetup = async () => {
      try {
        // First check if backend is available
        const healthy = await healthApi.check();
        if (!healthy) {
          // Backend not ready yet, wait and retry
          setTimeout(checkSetup, 1000);
          return;
        }

        // Check model status
        const status = await modelsApi.getStatus();
        
        // Show setup screen if:
        // - Any models are pending/downloading/checking
        // - Not all models are ready
        if (status.needs_setup || !status.all_ready) {
          setShowSetup(true);
        }
      } catch {
        // If we can't connect, don't show setup screen
        // The backend might still be starting up
      } finally {
        setCheckingSetup(false);
      }
    };

    checkSetup();
  }, []);

  const handleSearch = (query: string) => {
    setCurrentPage("search");
    window.dispatchEvent(new CustomEvent('search-query', { detail: query }));
  };

  const renderPage = () => {
    switch (currentPage) {
      case "photos":
        return <PhotosView />;
      case "people":
        return <PeopleView />;
      case "objects":
        return <ObjectsView />;
      case "places":
        return <PlacesView />;
      case "search":
        return <SearchView />;
      case "help":
        return <HelpView />;
      case "settings":
        return <SettingsView />;
      default:
        return <PhotosView />;
    }
  };

  // Show setup screen during first-time model download
  if (showSetup) {
    return (
      <ThemeProvider>
        <SetupScreen onComplete={() => setShowSetup(false)} />
      </ThemeProvider>
    );
  }

  // Show loading state while checking setup
  if (checkingSetup) {
    return (
      <ThemeProvider>
        <div className="h-screen w-screen bg-light-bg dark:bg-dark-bg flex items-center justify-center">
          <div className="text-light-text-secondary dark:text-dark-text-secondary">
            Loading...
          </div>
        </div>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider>
      <div className="h-screen w-screen bg-light-bg dark:bg-dark-bg text-light-text-primary dark:text-dark-text-primary transition-colors duration-300 flex overflow-hidden font-sans selection:bg-brand-primary/20 selection:text-brand-primary">
        <Sidebar currentPage={currentPage} onNavigate={setCurrentPage} />

        <div className="flex-1 flex flex-col min-w-0">
          <Header
            onSearch={handleSearch}
            onOpenSettings={() => setCurrentPage("settings")}
          />

          <main className="flex-1 overflow-y-auto px-8 pb-8 pt-4 custom-scrollbar">
            <div className="max-w-[1600px] mx-auto h-full">
              {renderPage()}
            </div>
          </main>
        </div>
      </div>
    </ThemeProvider>
  );
};

export default App;
