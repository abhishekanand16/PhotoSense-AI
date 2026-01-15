/** Search view - semantic and similarity search. */

import React, { useState, useEffect } from "react";
import { convertFileSrc } from "@tauri-apps/api/tauri";
import { searchApi, Photo } from "../services/api";

const SearchView: React.FC = () => {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Listen for search queries from command bar
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
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-dark-text-primary dark:text-dark-text-primary mb-1">
          Search
        </h1>
        <p className="text-dark-text-secondary dark:text-dark-text-secondary">
          Semantic search, not filters
        </p>
      </div>

      <div className="mb-6 flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search for photos..."
          className="flex-1 px-4 py-2 bg-dark-surface dark:bg-dark-surface border border-dark-border dark:border-dark-border rounded-lg text-dark-text-primary dark:text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-blue-600"
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      {results.length > 0 && (
        <div>
          <div className="mb-4 text-dark-text-secondary dark:text-dark-text-secondary">
            Found {results.length} result{results.length !== 1 ? "s" : ""}
          </div>
          <div className="grid grid-cols-4 gap-4">
            {results.map((photo) => (
              <div
                key={photo.id}
                className="relative aspect-square bg-dark-border dark:bg-dark-border rounded-lg overflow-hidden"
              >
                <img
                  src={convertFileSrc(photo.file_path)}
                  alt={photo.file_path}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3C/svg%3E";
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {!loading && results.length === 0 && query && (
        <div className="text-center py-12 text-dark-text-secondary dark:text-dark-text-secondary">
          No results found
        </div>
      )}
    </div>
  );
};

export default SearchView;
