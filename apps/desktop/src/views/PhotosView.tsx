import React, { useEffect, useState } from "react";
import { convertFileSrc } from "@tauri-apps/api/tauri";
import { photosApi, Photo } from "../services/api";
import { Image as ImageIcon, Calendar } from "lucide-react";
import EmptyState from "../components/common/EmptyState";
import Card from "../components/common/Card";

const PhotosView: React.FC = () => {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPhoto, setSelectedPhoto] = useState<Photo | null>(null);

  useEffect(() => {
    loadPhotos();
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

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <ImageIcon className="text-brand-primary" size={24} />
          <h1 className="text-3xl font-black text-light-text-primary dark:text-dark-text-primary tracking-tight">
            Memories
          </h1>
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
            {datePhotos.map((photo) => (
              <Card
                key={photo.id}
                onClick={() => setSelectedPhoto(photo)}
                className="aspect-square group relative"
              >
                <img
                  src={convertFileSrc(photo.file_path)}
                  alt={photo.file_path}
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                  loading="lazy"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='18' height='18' x='3' y='3' rx='2' ry='2'/%3E%3Ccircle cx='9' cy='9' r='2'/%3E%3Cpath d='m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21'/%3E%3C/svg%3E";
                  }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end p-4">
                  <span className="text-white text-[10px] font-bold uppercase tracking-wider truncate w-full">
                    {photo.file_path.split('/').pop()}
                  </span>
                </div>
              </Card>
            ))}
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
            <button
              onClick={() => setSelectedPhoto(null)}
              className="absolute -top-4 -right-4 w-12 h-12 bg-white text-black rounded-full flex items-center justify-center shadow-xl hover:scale-110 transition-transform font-bold"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default PhotosView;
