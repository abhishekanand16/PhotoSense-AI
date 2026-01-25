/**
 * PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
 * Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
 */
import React, { useEffect, useState } from "react";
import { convertFileSrc } from "@tauri-apps/api/tauri";
import { photosApi, scanApi, Photo, GlobalScanStatus } from "../services/api";
import { Image as ImageIcon, Calendar, Trash2, Check, Info, Loader2 } from "lucide-react";
import EmptyState from "../components/common/EmptyState";
import Card from "../components/common/Card";
import MetadataPanel from "../components/MetadataPanel";

const PhotosView: React.FC = () => {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPhoto, setSelectedPhoto] = useState<Photo | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);
  const [metadataPhotoId, setMetadataPhotoId] = useState<number | null>(null);
  const [scanStatus, setScanStatus] = useState<GlobalScanStatus | null>(null);

  useEffect(() => {
    loadPhotos();
    
    // Listen for refresh events
    const handleRefresh = () => {
      loadPhotos();
    };
    window.addEventListener('refresh-photos', handleRefresh);
    
    return () => {
      window.removeEventListener('refresh-photos', handleRefresh);
    };
  }, []);

  // Track scan status to show background activity indicator
  useEffect(() => {
    const pollScanStatus = async () => {
      try {
        const status = await scanApi.getGlobalStatus();
        setScanStatus(status);
      } catch {
        // Ignore errors - just don't show indicator
      }
    };
    
    pollScanStatus();
    const interval = setInterval(pollScanStatus, 2000);
    
    return () => clearInterval(interval);
  }, []);

  const loadPhotos = async () => {
    try {
      setLoading(true);
      const data = await photosApi.list();
      setPhotos(data);
    } catch (error) {
      console.error("Failed to load photos:", error);
    } finally {
      setLoading(false);
    }
  };

  const groupByDate = (photos: Photo[]): Record<string, Photo[]> => {
    const groups: Record<string, Photo[]> = {};
    photos.forEach((photo) => {
      const date = photo.date_taken
        ? new Date(photo.date_taken).toLocaleDateString("en-US", {
          year: "numeric",
          month: "long",
          day: "numeric",
        })
        : "Unknown Date";
      if (!groups[date]) {
        groups[date] = [];
      }
      groups[date].push(photo);
    });
    return groups;
  };

  const toggleSelection = (photoId: number) => {
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(photoId)) {
        newSet.delete(photoId);
      } else {
        newSet.add(photoId);
      }
      return newSet;
    });
  };

  const selectAll = () => {
    setSelectedIds(new Set(photos.map((p) => p.id)));
  };

  const clearSelection = () => {
    setSelectedIds(new Set());
  };

  const handleDelete = async () => {
    if (selectedIds.size === 0) return;

    const confirmed = window.confirm(
      `⚠️ WARNING: This will permanently delete ${selectedIds.size} photo(s) from your computer.\n\n` +
      `This action will:\n` +
      `• Delete the files from disk\n` +
      `• Remove them from the library\n` +
      `• Delete all associated data (faces, objects)\n\n` +
      `This action CANNOT be undone. Are you sure you want to continue?`
    );

    if (!confirmed) return;

    try {
      setIsDeleting(true);
      const idsArray = Array.from(selectedIds);
      
      if (idsArray.length === 1) {
        await photosApi.delete(idsArray[0]);
      } else {
        await photosApi.deleteMultiple(idsArray);
      }

      // Remove deleted photos from state
      setPhotos((prev) => prev.filter((p) => !selectedIds.has(p.id)));
      clearSelection();
      
      // Close modal if selected photo was deleted
      if (selectedPhoto && selectedIds.has(selectedPhoto.id)) {
        setSelectedPhoto(null);
      }
    } catch (error) {
      console.error("Failed to delete photos:", error);
      alert(`Failed to delete photos: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <div className="w-12 h-12 border-4 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin" />
        <p className="text-light-text-tertiary dark:text-dark-text-tertiary font-bold animate-pulse uppercase tracking-widest text-xs">
          Scanning Library
        </p>
      </div>
    );
  }

  if (photos.length === 0) {
    return (
      <EmptyState
        icon={ImageIcon}
        title="Your library is empty"
        description="Start by importing some photos from your computer. Our AI will analyze them locally for people and objects."
        actionLabel="Add Photos"
        onAction={() => window.dispatchEvent(new CustomEvent('open-add-photos'))}
      />
    );
  }

  const grouped = groupByDate(photos);

  const hasSelection = selectedIds.size > 0;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Selection Toolbar - positioned within the main content area (accounting for sidebar w-72 = 288px) */}
      {hasSelection && (
        <div className="fixed top-24 left-72 right-0 z-50 px-8">
          <div className="bg-light-surface dark:bg-dark-surface border border-light-border dark:border-dark-border rounded-2xl shadow-lg p-4 flex items-center justify-between max-w-[1600px] mx-auto">
            <div className="flex items-center gap-4">
              <span className="text-sm font-bold text-light-text-primary dark:text-dark-text-primary">
                {selectedIds.size} photo{selectedIds.size !== 1 ? "s" : ""} selected
              </span>
              <button
                onClick={clearSelection}
                className="text-xs text-light-text-tertiary dark:text-dark-text-tertiary hover:text-light-text-primary dark:hover:text-dark-text-primary transition-colors"
              >
                Clear selection
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-xl disabled:opacity-50 transition-all shadow-lg font-bold text-sm"
              >
                <Trash2 size={16} />
                <span>{isDeleting ? "Deleting..." : "Delete"}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      <div className={`mb-10 ${hasSelection ? "mt-20" : ""}`}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <ImageIcon className="text-brand-primary" size={24} />
            <h1 className="text-3xl font-black text-light-text-primary dark:text-dark-text-primary tracking-tight">
              Memories
            </h1>
            {/* Show scanning indicator when import/processing is happening */}
            {scanStatus && (scanStatus.status === "scanning" || scanStatus.status === "indexing") && (
              <div className="flex items-center gap-2 px-3 py-1 bg-brand-primary/10 rounded-full">
                <Loader2 size={12} className="text-brand-primary animate-spin" />
                <span className="text-xs font-medium text-brand-primary">
                  {scanStatus.phase === "import" 
                    ? `Importing ${scanStatus.imported_photos || 0} photos...` 
                    : `Analyzing ${scanStatus.processed_photos}/${scanStatus.total_photos}...`}
                </span>
              </div>
            )}
          </div>
          {!hasSelection && photos.length > 0 && (
            <button
              onClick={selectAll}
              className="text-sm text-light-text-secondary dark:text-dark-text-secondary hover:text-brand-primary transition-colors font-medium"
            >
              Select all
            </button>
          )}
        </div>
        <p className="text-light-text-secondary dark:text-dark-text-secondary font-medium">
          A timeline of your life, analyzed and organized by AI.
        </p>
      </div>

      {Object.entries(grouped).map(([date, datePhotos]) => (
        <div key={date} className="mb-12">
          <div className="flex items-center gap-2 mb-6 sticky top-24 z-10 py-2 bg-light-bg/50 dark:bg-dark-bg/50 backdrop-blur-sm">
            <Calendar className="text-light-text-tertiary dark:text-dark-text-tertiary" size={16} />
            <h2 className="text-sm font-bold text-light-text-tertiary dark:text-dark-text-tertiary uppercase tracking-widest">
              {date}
            </h2>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {datePhotos.map((photo) => {
              const isSelected = selectedIds.has(photo.id);
              return (
                <Card
                  key={photo.id}
                  onClick={() => {
                    if (hasSelection) {
                      toggleSelection(photo.id);
                    } else {
                      setSelectedPhoto(photo);
                    }
                  }}
                  className={`aspect-square group relative cursor-pointer ${isSelected ? "ring-4 ring-brand-primary" : ""}`}
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
                  {/* Selection Checkbox */}
                  <div
                    className="absolute top-2 left-2 z-10"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleSelection(photo.id);
                    }}
                  >
                    <div
                      className={`w-6 h-6 rounded-md border-2 flex items-center justify-center transition-all ${
                        isSelected
                          ? "bg-brand-primary border-brand-primary"
                          : "bg-white/80 dark:bg-dark-bg/80 border-white/50 dark:border-dark-border backdrop-blur-sm"
                      }`}
                    >
                      {isSelected && <Check size={16} className="text-white" />}
                    </div>
                  </div>
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
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end p-4">
                    <span className="text-white text-[10px] font-bold uppercase tracking-wider truncate w-full">
                      {photo.file_path.split('/').pop()}
                    </span>
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      ))}

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

export default PhotosView;
