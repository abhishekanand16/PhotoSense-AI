import React, { useState, useEffect, useCallback } from "react";
import { convertFileSrc } from "@tauri-apps/api/tauri";
import { MapPin, Globe, Loader2, ImageOff, ChevronRight } from "lucide-react";
import L from "leaflet";
import MapComponent from "../components/MapComponent";
import Card from "../components/common/Card";
import EmptyState from "../components/common/EmptyState";
import { placesApi, photosApi, Place, Photo, PhotoLocation, BoundingBox } from "../services/api";

const PlacesView: React.FC = () => {
  // Data state
  const [places, setPlaces] = useState<Place[]>([]);
  const [mapLocations, setMapLocations] = useState<PhotoLocation[]>([]);
  const [filteredPhotos, setFilteredPhotos] = useState<Photo[]>([]);
  const [allPhotos, setAllPhotos] = useState<Photo[]>([]);
  
  // UI state
  const [loading, setLoading] = useState(true);
  const [photosLoading, setPhotosLoading] = useState(false);
  const [selectedPlace, setSelectedPlace] = useState<string | null>(null);
  const [selectedPhotoId, setSelectedPhotoId] = useState<number | null>(null);
  const [showUnknown, setShowUnknown] = useState(false);

  // Load initial data
  useEffect(() => {
    loadData();
    
    // Listen for refresh events from header
    const handleRefresh = () => {
      loadData();
    };
    
    window.addEventListener('refresh-places', handleRefresh);
    window.addEventListener('refresh-data', handleRefresh);
    
    return () => {
      window.removeEventListener('refresh-places', handleRefresh);
      window.removeEventListener('refresh-data', handleRefresh);
    };
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // Load places, map locations, and all photos in parallel
      const [placesData, locationsData, photosData] = await Promise.all([
        placesApi.getPlaces(50),
        placesApi.getMapLocations(),
        photosApi.list(),
      ]);
      
      setPlaces(placesData);
      setMapLocations(locationsData);
      setAllPhotos(photosData);
      
      // Initially show all photos with locations
      const photoIdsWithLocation = new Set(locationsData.map(l => l.photo_id));
      const photosWithLocation = photosData.filter(p => photoIdsWithLocation.has(p.id));
      setFilteredPhotos(photosWithLocation);
      
    } catch (error) {
      console.error("Failed to load places data:", error);
    } finally {
      setLoading(false);
    }
  };

  // Handle place selection from list
  const handlePlaceClick = useCallback(async (place: Place) => {
    try {
      setPhotosLoading(true);
      setSelectedPlace(place.name);
      setSelectedPhotoId(null);
      setShowUnknown(false);
      
      const photos = await placesApi.getPhotosByPlace(place.name);
      setFilteredPhotos(photos);
    } catch (error) {
      console.error("Failed to load photos for place:", error);
    } finally {
      setPhotosLoading(false);
    }
  }, []);

  // Handle cluster click on map
  const handleClusterClick = useCallback(async (bounds: L.LatLngBounds, _photoIds: number[]) => {
    try {
      setPhotosLoading(true);
      setSelectedPlace(null);
      setSelectedPhotoId(null);
      
      const bbox: BoundingBox = {
        min_lat: bounds.getSouth(),
        max_lat: bounds.getNorth(),
        min_lon: bounds.getWest(),
        max_lon: bounds.getEast(),
      };
      
      const photos = await placesApi.getPhotosByBbox(bbox);
      setFilteredPhotos(photos);
    } catch (error) {
      console.error("Failed to load photos for cluster:", error);
    } finally {
      setPhotosLoading(false);
    }
  }, []);

  // Handle marker click on map
  const handleMarkerClick = useCallback((photoId: number) => {
    setSelectedPhotoId(photoId);
    // Scroll to the photo in the grid
    const element = document.getElementById(`photo-${photoId}`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, []);

  // Handle photo click in grid
  const handlePhotoClick = useCallback((photo: Photo) => {
    setSelectedPhotoId(photo.id);
  }, []);

  // Show all photos with location
  const handleShowAll = useCallback(() => {
    setSelectedPlace(null);
    setSelectedPhotoId(null);
    setShowUnknown(false);
    
    const photoIdsWithLocation = new Set(mapLocations.map(l => l.photo_id));
    const photosWithLocation = allPhotos.filter(p => photoIdsWithLocation.has(p.id));
    setFilteredPhotos(photosWithLocation);
  }, [mapLocations, allPhotos]);

  // Show photos without location
  const handleShowUnknown = useCallback(async () => {
    try {
      setPhotosLoading(true);
      setSelectedPlace("Unknown");
      setSelectedPhotoId(null);
      setShowUnknown(true);
      
      const photos = await placesApi.getPhotosWithoutLocation();
      setFilteredPhotos(photos);
    } catch (error) {
      console.error("Failed to load photos without location:", error);
    } finally {
      setPhotosLoading(false);
    }
  }, []);

  // Calculate unknown count
  const unknownCount = allPhotos.length - mapLocations.length;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <div className="w-12 h-12 border-4 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin" />
        <p className="text-light-text-tertiary dark:text-dark-text-tertiary font-bold animate-pulse uppercase tracking-widest text-xs">
          Loading places
        </p>
      </div>
    );
  }

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700 h-full flex flex-col">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <MapPin className="text-brand-primary" size={24} />
          <h1 className="text-3xl font-black text-light-text-primary dark:text-dark-text-primary tracking-tight">
            Places
          </h1>
        </div>
        <p className="text-light-text-secondary dark:text-dark-text-secondary font-medium">
          Browse your photos by location. Click on map clusters or places to filter.
        </p>
      </div>

      {/* Main content - Map sidebar + Photo grid */}
      <div className="flex-1 flex gap-6 min-h-0">
        {/* Left sidebar - Map and Places list */}
        <div className="w-80 flex-shrink-0 flex flex-col gap-4">
          {/* Map */}
          <Card className="overflow-hidden" hover={false}>
            <MapComponent
              locations={mapLocations}
              onClusterClick={handleClusterClick}
              onMarkerClick={handleMarkerClick}
              selectedPhotoId={selectedPhotoId}
              height="220px"
            />
          </Card>

          {/* Places list */}
          <Card className="flex-1 overflow-hidden flex flex-col" hover={false}>
            <div className="p-4 border-b border-light-border dark:border-dark-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Globe size={16} className="text-brand-primary" />
                  <span className="font-bold text-sm text-light-text-primary dark:text-dark-text-primary">
                    Locations
                  </span>
                </div>
                <button
                  onClick={handleShowAll}
                  className={`text-xs font-semibold px-2 py-1 rounded-lg transition-colors ${
                    !selectedPlace && !showUnknown
                      ? "bg-brand-primary/10 text-brand-primary"
                      : "text-light-text-tertiary dark:text-dark-text-tertiary hover:bg-light-bg dark:hover:bg-dark-bg"
                  }`}
                >
                  Show All
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar">
              {places.length === 0 && unknownCount === 0 ? (
                <div className="p-4 text-center text-light-text-tertiary dark:text-dark-text-tertiary text-sm">
                  No location data available. Import photos with GPS metadata.
                </div>
              ) : (
                <div className="py-2">
                  {/* Places with photos */}
                  {places.map((place) => (
                    <button
                      key={place.name}
                      onClick={() => handlePlaceClick(place)}
                      className={`w-full flex items-center justify-between px-4 py-3 transition-colors ${
                        selectedPlace === place.name
                          ? "bg-brand-primary/10"
                          : "hover:bg-light-bg dark:hover:bg-dark-bg"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <MapPin
                          size={16}
                          className={
                            selectedPlace === place.name
                              ? "text-brand-primary"
                              : "text-light-text-tertiary dark:text-dark-text-tertiary"
                          }
                        />
                        <span
                          className={`font-medium text-sm ${
                            selectedPlace === place.name
                              ? "text-brand-primary"
                              : "text-light-text-primary dark:text-dark-text-primary"
                          }`}
                        >
                          {place.name}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                            selectedPlace === place.name
                              ? "bg-brand-primary/20 text-brand-primary"
                              : "bg-light-bg dark:bg-dark-bg text-light-text-tertiary dark:text-dark-text-tertiary"
                          }`}
                        >
                          {place.count}
                        </span>
                        <ChevronRight
                          size={14}
                          className="text-light-text-tertiary dark:text-dark-text-tertiary"
                        />
                      </div>
                    </button>
                  ))}

                  {/* Unknown location bucket */}
                  {unknownCount > 0 && (
                    <button
                      onClick={handleShowUnknown}
                      className={`w-full flex items-center justify-between px-4 py-3 transition-colors border-t border-light-border dark:border-dark-border ${
                        showUnknown
                          ? "bg-brand-primary/10"
                          : "hover:bg-light-bg dark:hover:bg-dark-bg"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <ImageOff
                          size={16}
                          className={
                            showUnknown
                              ? "text-brand-primary"
                              : "text-light-text-tertiary dark:text-dark-text-tertiary"
                          }
                        />
                        <span
                          className={`font-medium text-sm ${
                            showUnknown
                              ? "text-brand-primary"
                              : "text-light-text-secondary dark:text-dark-text-secondary"
                          }`}
                        >
                          Unknown location
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                            showUnknown
                              ? "bg-brand-primary/20 text-brand-primary"
                              : "bg-light-bg dark:bg-dark-bg text-light-text-tertiary dark:text-dark-text-tertiary"
                          }`}
                        >
                          {unknownCount}
                        </span>
                        <ChevronRight
                          size={14}
                          className="text-light-text-tertiary dark:text-dark-text-tertiary"
                        />
                      </div>
                    </button>
                  )}
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Right content - Photo grid */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Selection info */}
          <div className="flex items-center gap-2 mb-4">
            <span className="text-sm font-bold text-light-text-tertiary dark:text-dark-text-tertiary uppercase tracking-widest">
              {selectedPlace
                ? `${selectedPlace}`
                : showUnknown
                ? "Unknown location"
                : "All locations"}
            </span>
            <span className="text-sm text-light-text-tertiary dark:text-dark-text-tertiary">
              ({filteredPhotos.length} photos)
            </span>
            {photosLoading && (
              <Loader2 size={14} className="animate-spin text-brand-primary" />
            )}
          </div>

          {/* Photo grid */}
          {filteredPhotos.length === 0 ? (
            <EmptyState
              icon={MapPin}
              title="No photos"
              description={
                showUnknown
                  ? "All your photos have location data!"
                  : "No photos found for this location."
              }
            />
          ) : (
            <div className="flex-1 overflow-y-auto custom-scrollbar pr-2">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                {filteredPhotos.map((photo) => (
                  <Card
                    key={photo.id}
                    id={`photo-${photo.id}`}
                    className={`aspect-square group relative cursor-pointer transition-all ${
                      selectedPhotoId === photo.id
                        ? "ring-4 ring-brand-primary ring-offset-2 ring-offset-light-bg dark:ring-offset-dark-bg"
                        : ""
                    }`}
                    onClick={() => handlePhotoClick(photo)}
                  >
                    <img
                      src={convertFileSrc(photo.file_path)}
                      alt={photo.file_path}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                      loading="lazy"
                    />
                    {/* Hover overlay */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                      <div className="absolute bottom-2 left-2 right-2">
                        {photo.date_taken && (
                          <p className="text-white text-xs font-medium truncate">
                            {new Date(photo.date_taken).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                    </div>
                    {/* Selected indicator */}
                    {selectedPhotoId === photo.id && (
                      <div className="absolute top-2 right-2">
                        <div className="w-6 h-6 bg-brand-primary rounded-full flex items-center justify-center">
                          <MapPin size={14} className="text-white" />
                        </div>
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PlacesView;
