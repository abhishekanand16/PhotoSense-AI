/** Photos view - main gallery. */

import React, { useEffect, useState } from "react";
import { convertFileSrc } from "@tauri-apps/api/tauri";
import { photosApi, Photo } from "../services/api";

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
      <div className="flex items-center justify-center h-full">
        <div className="text-dark-text-secondary dark:text-dark-text-secondary">Loading photos...</div>
      </div>
    );
  }

  if (photos.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div className="text-6xl mb-6">📸</div>
        <div className="text-2xl font-semibold text-dark-text-primary dark:text-dark-text-primary mb-3">
          No Photos Yet
        </div>
        <div className="text-dark-text-secondary dark:text-dark-text-secondary mb-6">
          Photos are analyzed locally
        </div>
        <button
          onClick={() => {
            // This will be handled by the command bar
            window.dispatchEvent(new CustomEvent('open-add-photos'));
          }}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-base"
        >
          Add Photos
        </button>
      </div>
    );
  }

  const grouped = groupByDate(photos);

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-dark-text-primary dark:text-dark-text-primary mb-1">
          Photos
        </h1>
        <p className="text-dark-text-secondary dark:text-dark-text-secondary">
          Timeline and grid view of all your photos
        </p>
      </div>

      {Object.entries(grouped).map(([date, datePhotos]) => (
        <div key={date} className="mb-8">
          <h2 className="text-lg font-semibold text-dark-text-primary dark:text-dark-text-primary mb-4">
            {date}
          </h2>
          <div className="grid grid-cols-4 gap-4">
            {datePhotos.map((photo) => (
              <div
                key={photo.id}
                className="relative aspect-square bg-dark-border dark:bg-dark-border rounded-lg overflow-hidden cursor-pointer hover:opacity-90 transition-opacity"
                onClick={() => setSelectedPhoto(photo)}
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
      ))}

      {selectedPhoto && (
        <div
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50"
          onClick={() => setSelectedPhoto(null)}
        >
          <div className="max-w-4xl max-h-[90vh] p-4">
            <img
              src={convertFileSrc(selectedPhoto.file_path)}
              alt={selectedPhoto.file_path}
              className="max-w-full max-h-[90vh] object-contain rounded-lg"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default PhotosView;
