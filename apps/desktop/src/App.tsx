import React, { useState } from "react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import ObjectsView from "./views/ObjectsView";
import PeopleView from "./views/PeopleView";
import PhotosView from "./views/PhotosView";
import PlacesView from "./views/PlacesView";
import SearchView from "./views/SearchView";
import SettingsView from "./views/SettingsView";
import { ThemeProvider } from "./components/common/ThemeProvider";

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState("photos");

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
      case "settings":
        return <SettingsView />;
      default:
        return <PhotosView />;
    }
  };

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
