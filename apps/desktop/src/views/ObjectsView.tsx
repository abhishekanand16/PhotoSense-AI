import React, { useEffect, useState } from "react";
import { convertFileSrc } from "@tauri-apps/api/tauri";
import { objectsApi, Photo } from "../services/api";
import { Box } from "lucide-react";
import EmptyState from "../components/common/EmptyState";
import Card from "../components/common/Card";

const ObjectsView: React.FC = () => {
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingPhotos, setLoadingPhotos] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState<Photo | null>(null);

  useEffect(() => {
    loadCategories();
  }, []);

  useEffect(() => {
    if (selectedCategory) {
      loadPhotosForCategory(selectedCategory);
    } else {
      setPhotos([]);
    }
  }, [selectedCategory]);

  const loadCategories = async () => {
    try {
      setLoading(true);
      const data = await objectsApi.getCategories();
      setCategories(data);
      if (data.length > 0 && !selectedCategory) {
        setSelectedCategory(data[0]);
      }
    } catch (error) {
      console.error("Failed to load categories:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadPhotosForCategory = async (category: string) => {
    try {
      setLoadingPhotos(true);
      const data = await objectsApi.getPhotosByCategory(category);
      setPhotos(data);
    } catch (error) {
      console.error("Failed to load photos for category:", error);
    } finally {
      setLoadingPhotos(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <div className="w-12 h-12 border-4 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin" />
        <p className="text-light-text-tertiary dark:text-dark-text-tertiary font-bold animate-pulse uppercase tracking-widest text-xs">
          Loading Categories
        </p>
      </div>
    );
  }

  if (categories.length === 0) {
    return (
      <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-2">
            <Box className="text-brand-primary" size={24} />
            <h1 className="text-3xl font-black text-light-text-primary dark:text-dark-text-primary tracking-tight">
              Objects
            </h1>
          </div>
          <p className="text-light-text-secondary dark:text-dark-text-secondary font-medium">
            Smart categories and detected objects from your library.
          </p>
        </div>

        <div className="flex items-center justify-center min-h-[500px]">
          <EmptyState
            icon={Box}
            title="No objects identified"
            description="Our AI identifies objects like 'mountains', 'beaches', or 'cars' to help you find photos faster. Add photos to begin the discovery."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <Box className="text-brand-primary" size={24} />
          <h1 className="text-3xl font-black text-light-text-primary dark:text-dark-text-primary tracking-tight">
            Objects
          </h1>
        </div>
        <p className="text-light-text-secondary dark:text-dark-text-secondary font-medium">
          Smart categories and detected objects from your library.
        </p>
      </div>

      {/* Category Filter */}
      <div className="mb-8">
        <div className="flex flex-wrap gap-3">
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setSelectedCategory(category)}
              className={`px-4 py-2 rounded-xl font-bold text-sm transition-all ${selectedCategory === category
                  ? "bg-brand-primary text-white dark:text-black shadow-lg shadow-brand-primary/20"
                  : "bg-light-surface dark:bg-dark-surface border border-light-border dark:border-dark-border text-light-text-secondary dark:text-dark-text-secondary hover:border-brand-primary hover:text-brand-primary"
                }`}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      {/* Photos Grid */}
      {loadingPhotos ? (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <div className="w-12 h-12 border-4 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin" />
          <p className="text-light-text-tertiary dark:text-dark-text-tertiary font-bold animate-pulse uppercase tracking-widest text-xs">
            Loading Photos
          </p>
        </div>
      ) : photos.length > 0 ? (
        <div>
          <div className="mb-6">
            <h2 className="text-lg font-bold text-light-text-primary dark:text-dark-text-primary">
              {selectedCategory} ({photos.length} photos)
            </h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {photos.map((photo) => (
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
      ) : selectedCategory ? (
        <div className="flex items-center justify-center min-h-[400px]">
          <EmptyState
            icon={Box}
            title={`No photos found for "${selectedCategory}"`}
            description="Try selecting a different category or add more photos to your library."
          />
        </div>
      ) : null}

      {/* Photo Modal */}
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

export default ObjectsView;
