import React, { useState, useEffect } from "react";
import { convertFileSrc } from "@tauri-apps/api/tauri";
import { searchApi, Photo } from "../services/api";
import { Search, Sparkles, Filter, Loader2 } from "lucide-react";
import EmptyState from "../components/common/EmptyState";
import Card from "../components/common/Card";

const SearchView: React.FC = () => {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  useEffect(() => {
    const handleSearchQuery = (event: CustomEvent) => {
      const searchQuery = event.detail;
      if (searchQuery) {
        setQuery(searchQuery);
        performSearch(searchQuery);
      }
    };
    window.addEventListener('search-query', handleSearchQuery as EventListener);
    return () => window.removeEventListener('search-query', handleSearchQuery as EventListener);
  }, []);

  const performSearch = async (searchQuery: string) => {
    if (!searchQuery.trim()) return;

    try {
      setLoading(true);
      setHasSearched(true);
      const data = await searchApi.search(searchQuery);
      setResults(data);
    } catch (error) {
      console.error("Search failed:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    await performSearch(query);
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <Search className="text-brand-primary" size={24} />
          <h1 className="text-3xl font-black text-light-text-primary dark:text-dark-text-primary tracking-tight">
            Search
          </h1>
        </div>
        <p className="text-light-text-secondary dark:text-dark-text-secondary font-medium">
          Find any memory using natural language. Try searching for "beach sunset" or "family dinner".
        </p>
      </div>

      <div className="max-w-3xl mb-12">
        <div className="relative flex items-center group">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Describe what you're looking for..."
            className="w-full pl-6 pr-32 py-4 bg-light-surface dark:bg-dark-surface border border-light-border dark:border-dark-border rounded-2xl text-lg text-light-text-primary dark:text-dark-text-primary placeholder-light-text-tertiary shadow-soft focus:outline-none focus:ring-4 focus:ring-brand-primary/10 focus:border-brand-primary transition-all"
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="absolute right-2 px-6 py-2.5 bg-brand-primary text-white rounded-xl font-bold hover:bg-brand-secondary disabled:opacity-50 transition-all shadow-lg shadow-brand-primary/20 flex items-center gap-2"
          >
            {loading ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <Sparkles size={18} />
            )}
            <span>Search</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <div className="w-12 h-12 border-4 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin" />
          <p className="text-light-text-tertiary dark:text-dark-text-tertiary font-bold animate-pulse uppercase tracking-widest text-xs">
            Analyzing semantic context
          </p>
        </div>
      ) : results.length > 0 ? (
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
          <div className="flex items-center gap-2 mb-8">
            <Filter size={14} className="text-brand-primary" />
            <span className="text-sm font-bold text-light-text-tertiary dark:text-dark-text-tertiary uppercase tracking-widest">
              Found {results.length} memories matching your description
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {results.map((photo) => (
              <Card key={photo.id} className="aspect-square group relative">
                <img
                  src={convertFileSrc(photo.file_path)}
                  alt={photo.file_path}
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                  loading="lazy"
                />
              </Card>
            ))}
          </div>
        </div>
      ) : hasSearched && query ? (
        <EmptyState
          icon={Search}
          title="No matches found"
          description={`We couldn't find any photos matching "${query}". Try using different keywords or simpler descriptions.`}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 opacity-60">
          {[
            { tag: "Sunset", desc: "Golden hour and vivid skies" },
            { tag: "Nature", desc: "Forrest, mountains and outdoors" },
            { tag: "People", desc: "Portraits and group photos" }
          ].map((item, i) => (
            <Card key={i} className="p-6 border-dashed" hover={false}>
              <div className="text-brand-primary font-bold mb-1">Search for "{item.tag}"</div>
              <div className="text-sm text-light-text-tertiary dark:text-dark-text-tertiary">{item.desc}</div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default SearchView;
