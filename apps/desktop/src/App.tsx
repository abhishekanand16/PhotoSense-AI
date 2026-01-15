/** Main App component. */

import React, { useEffect, useState } from "react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import ObjectsView from "./views/ObjectsView";
import PeopleView from "./views/PeopleView";
import PhotosView from "./views/PhotosView";
import SearchView from "./views/SearchView";
import SettingsView from "./views/SettingsView";
import { initTheme, getTheme, setTheme } from "./services/theme";

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState("photos");

  useEffect(() => {
    initTheme();
  }, []);

  const handleThemeToggle = () => {
    const current = getTheme();
    const newTheme = current === "dark" ? "light" : "dark";
    setTheme(newTheme);
  };

  const handleSearch = (query: string) => {
    setCurrentPage("search");
    // Pass query to search view via event
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
      case "search":
        return <SearchView />;
      case "settings":
        return <SettingsView />;
      default:
        return <PhotosView />;
    }
  };

  return (
    <div className="h-screen flex flex-col dark">
      <Header onThemeToggle={handleThemeToggle} onSearch={handleSearch} />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar currentPage={currentPage} onNavigate={setCurrentPage} />
        <div className="flex-1 bg-dark-bg dark:bg-dark-bg overflow-hidden">
          {renderPage()}
        </div>
      </div>
    </div>
  );
};

export default App;
