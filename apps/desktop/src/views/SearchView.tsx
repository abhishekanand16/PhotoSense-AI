/**
 * PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
 * Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
 */
import React, { useState, useEffect } from "react";
import { convertFileSrc } from "@tauri-apps/api/tauri";
import { searchApi, Photo } from "../services/api";
import { Search, Sparkles, Filter, Loader2, Info } from "lucide-react";
import EmptyState from "../components/common/EmptyState";
import Card from "../components/common/Card";
import MetadataPanel from "../components/MetadataPanel";

const SearchView: React.FC = () => {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState<Photo | null>(null);
  const [metadataPhotoId, setMetadataPhotoId] = useState<number | null>(null);

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
            className="absolute right-2 px-6 py-2.5 bg-brand-primary text-white dark:text-black rounded-xl font-bold hover:bg-brand-secondary disabled:opacity-50 transition-all shadow-lg shadow-brand-primary/20 flex items-center gap-2"
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
              <Card 
                key={photo.id} 
                onClick={() => setSelectedPhoto(photo)}
                className="aspect-square group relative cursor-pointer"
              >
                <img
                  src={convertFileSrc(photo.file_path)}
                  alt={photo.file_path}
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                  loading="lazy"
                  onError={(e) => {
                    console.error("Failed to load image:", photo.file_path);
                    (e.target as HTMLImageElement).src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='18' height='18' x='3' y='3' rx='2' ry='2'/%3E%3Ccircle cx='9' cy='9' r='2'/%3E%3Cpath d='m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21'/%3E%3C/svg%3E";
                  }}
                />
                {/* Info button (visible on hover) */}
                <button
                  className="absolute top-2 right-2 z-10 w-7 h-7 rounded-full bg-black/50 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-brand-primary transition-all"
                  onClick={(e) => {
                    e.stopPropagation();
                    setMetadataPhotoId(photo.id);
                  }}
                  title="View photo info"
                >
                  <Info size={14} />
                </button>
                {/* Filename overlay on hover */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end p-4">
                  <span className="text-white text-[10px] font-bold uppercase tracking-wider truncate w-full">
                    {photo.file_path.split('/').pop()}
                  </span>
                </div>
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

      {/* Full-screen photo modal */}
      {selectedPhoto && (
        <div
          className="fixed inset-0 bg-dark-bg/95 flex items-center justify-center z-[100] animate-in fade-in duration-300 backdrop-blur-md"
          onClick={() => setSelectedPhoto(null)}
        >
          <div className="max-w-6xl max-h-[90vh] p-4 relative group" onClick={e => e.stopPropagation()}>
            <img
              src={convertFileSrc(selectedPhoto.file_path)}
              alt={selectedPhoto.file_path}
              className="max-w-full max-h-[90vh] object-contain rounded-3xl shadow-2xl"
            />
            {/* Close button */}
            <button
              onClick={() => setSelectedPhoto(null)}
              className="absolute -top-4 -right-4 w-12 h-12 bg-white text-black rounded-full flex items-center justify-center shadow-xl hover:scale-110 transition-transform font-bold"
            >
              ✕
            </button>
            {/* Info button */}
            <button
              onClick={() => setMetadataPhotoId(selectedPhoto.id)}
              className="absolute -top-4 right-12 w-12 h-12 bg-brand-primary text-white dark:text-black rounded-full flex items-center justify-center shadow-xl hover:scale-110 transition-transform"
              title="View photo info"
            >
              <Info size={20} />
            </button>
          </div>
        </div>
      )}

      {/* Metadata Panel */}
      {metadataPhotoId && (
        <MetadataPanel
          photoId={metadataPhotoId}
          onClose={() => setMetadataPhotoId(null)}
        />
      )}
    </div>
  );
};

export default SearchView;
