/** API service for communicating with FastAPI backend. */

import axios from "axios";

const API_BASE_URL = "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30 second timeout
});

// Add response interceptor for better error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error')) {
      throw new Error('Cannot connect to backend API. Make sure the server is running at http://localhost:8000');
    }
    if (error.response) {
      // Server responded with error status
      throw new Error(error.response.data?.detail || error.response.data?.message || `Server error: ${error.response.status}`);
    }
    throw error;
  }
);

export interface Photo {
  id: number;
  file_path: string;
  date_taken?: string;
  camera_model?: string;
  width?: number;
  height?: number;
  file_size?: number;
  created_at: string;
}

export interface Person {
  id: number;
  cluster_id?: number;
  name?: string;
  face_count: number;
  thumbnail_url?: string;
}

export interface CategorySummary {
  category: string;
  photo_count: number;
}

export interface SceneSummary {
  label: string;
  photo_count: number;
  avg_confidence: number;
}

export interface ScanJob {
  job_id: string;
  status: string;
  message?: string;
}

export interface JobStatus {
  job_id: string;
  status: string;
  progress: number;
  message?: string;
  phase?: "import" | "scanning" | "complete";
}

export interface GlobalScanStatus {
  status: "idle" | "scanning" | "indexing" | "done" | "paused";
  total_photos: number;
  scanned_photos: number;
  progress_percent: number;
  message: string;
  current_job_id?: string;
}

export interface Place {
  name: string;
  count: number;
  lat: number;
  lon: number;
}

export interface PhotoLocation {
  photo_id: number;
  latitude: number;
  longitude: number;
  city?: string;
  region?: string;
  country?: string;
}

export interface BoundingBox {
  min_lat: number;
  max_lat: number;
  min_lon: number;
  max_lon: number;
}

export interface LocationStats {
  total_photos: number;
  photos_with_location: number;
  photos_without_location: number;
  geocoded: number;
  not_geocoded: number;
}

export interface TagSummary {
  tag: string;
  photo_count: number;
}

export interface PhotoMetadata {
  photo_id: number;
  file_info: {
    name: string;
    size?: number;
    format: string;
    width?: number;
    height?: number;
    path: string;
  };
  dates: {
    date_taken?: string;
    date_imported?: string;
  };
  camera: {
    model?: string;
  };
  location?: {
    city?: string;
    region?: string;
    country?: string;
    latitude?: number;
    longitude?: number;
  };
  people: Array<{
    id: number;
    name?: string;
  }>;
  objects: Array<{
    category: string;
    confidence?: number;
  }>;
  scenes: Array<{
    label: string;
    confidence?: number;
  }>;
  custom_tags: string[];
}

export const photosApi = {
  list: async (): Promise<Photo[]> => {
    const response = await api.get<Photo[]>("/photos");
    return response.data;
  },
  get: async (id: number): Promise<Photo> => {
    const response = await api.get<Photo>(`/photos/${id}`);
    return response.data;
  },
  getMetadata: async (id: number): Promise<PhotoMetadata> => {
    const response = await api.get<PhotoMetadata>(`/photos/${id}/metadata`);
    return response.data;
  },
  updateMetadata: async (): Promise<{ status: string; message: string }> => {
    const response = await api.post<{ status: string; message: string }>("/photos/update-metadata");
    return response.data;
  },
  delete: async (id: number): Promise<{ status: string; message: string }> => {
    const response = await api.delete<{ status: string; message: string }>(`/photos/${id}`);
    return response.data;
  },
  deleteMultiple: async (ids: number[]): Promise<{ status: string; deleted: number; not_found: number[]; errors: number[]; message: string }> => {
    const response = await api.post<{ status: string; deleted: number; not_found: number[]; errors: number[]; message: string }>("/photos/delete", ids);
    return response.data;
  },
};

export const peopleApi = {
  list: async (): Promise<Person[]> => {
    const response = await api.get<Person[]>("/people");
    // Add thumbnail URLs to each person
    return response.data.map(person => ({
      ...person,
      thumbnail_url: `${API_BASE_URL}/people/${person.id}/thumbnail?size=200`
    }));
  },
  getPhotos: async (personId: number): Promise<Photo[]> => {
    const response = await api.get<Photo[]>(`/people/${personId}/photos`);
    return response.data;
  },
  updateName: async (personId: number, name: string): Promise<Person> => {
    const response = await api.patch<Person>(`/people/${personId}`, { name });
    return response.data;
  },
  merge: async (sourceId: number, targetId: number): Promise<void> => {
    await api.post("/people/merge", { source_person_id: sourceId, target_person_id: targetId });
  },
  /** Merge multiple people into a single target person */
  mergeMultiple: async (personIds: number[], targetPersonId: number, minConfidence: number = 0.5): Promise<{
    status: string;
    message: string;
    persons_merged: number;
    faces_merged: number;
    target_person_id: number;
  }> => {
    const response = await api.post("/people/merge-multiple", {
      person_ids: personIds,
      target_person_id: targetPersonId,
      min_confidence: minConfidence,
    });
    return response.data;
  },
  /** Delete a person (unassigns faces but keeps them) */
  delete: async (personId: number): Promise<{ status: string; message: string }> => {
    const response = await api.delete<{ status: string; message: string }>(`/people/${personId}`);
    return response.data;
  },
  /** Delete a person AND all their faces completely */
  deleteWithFaces: async (personId: number): Promise<{
    status: string;
    message: string;
    faces_deleted: number;
  }> => {
    const response = await api.delete(`/people/${personId}/with-faces`);
    return response.data;
  },
  cleanupOrphans: async (): Promise<{ deleted_people: number[]; count: number }> => {
    const response = await api.post("/people/cleanup-orphans");
    return response.data;
  },
};

export const scanApi = {
  start: async (folderPath: string, recursive: boolean = true): Promise<ScanJob> => {
    const response = await api.post<ScanJob>("/scan", { folder_path: folderPath, recursive });
    return response.data;
  },
  getStatus: async (jobId: string): Promise<JobStatus> => {
    const response = await api.get<JobStatus>(`/scan/status/${jobId}`);
    return response.data;
  },
  /** Get global scan status for progress tracking */
  getGlobalStatus: async (): Promise<GlobalScanStatus> => {
    const response = await api.get<GlobalScanStatus>("/scan/status");
    return response.data;
  },
  scanFaces: async (): Promise<ScanJob> => {
    const response = await api.post<ScanJob>("/scan/faces");
    return response.data;
  },
};

export const searchApi = {
  search: async (query?: string, personId?: number, category?: string): Promise<Photo[]> => {
    const response = await api.post<Photo[]>("/search", {
      query,
      person_id: personId,
      category,
    });
    return response.data;
  },
};

export const objectsApi = {
  getCategories: async (): Promise<string[]> => {
    const response = await api.get<string[]>("/objects/categories");
    return response.data;
  },
  getCategorySummary: async (): Promise<CategorySummary[]> => {
    const response = await api.get<CategorySummary[]>("/objects/categories/summary");
    return response.data;
  },
  getPhotosByCategory: async (category: string): Promise<Photo[]> => {
    const response = await api.get<Photo[]>(`/objects/category/${category}/photos`);
    return response.data;
  },
};

export const scenesApi = {
  getLabelSummary: async (options?: {
    prefix?: string;
    minPhotoCount?: number;
    minAvgConfidence?: number;
  }): Promise<SceneSummary[]> => {
    const response = await api.get<SceneSummary[]>("/scenes/summary", {
      params: {
        prefix: options?.prefix,
        min_photo_count: options?.minPhotoCount,
        min_avg_confidence: options?.minAvgConfidence,
      },
    });
    return response.data;
  },
  getPhotosByLabel: async (label: string): Promise<Photo[]> => {
    const response = await api.get<Photo[]>(`/scenes/label/${label}/photos`);
    return response.data;
  },
};

export const statsApi = {
  get: async () => {
    const response = await api.get("/stats");
    return response.data;
  },
};

export const healthApi = {
  check: async (): Promise<boolean> => {
    try {
      const response = await api.get("/health");
      return response.data?.status === "healthy";
    } catch {
      return false;
    }
  },
};

export const placesApi = {
  /** Get top places with photo counts */
  getPlaces: async (limit: number = 50): Promise<Place[]> => {
    const response = await api.get<Place[]>("/places", { params: { limit } });
    return response.data;
  },

  /** Get all photo locations for map display */
  getMapLocations: async (): Promise<PhotoLocation[]> => {
    const response = await api.get<PhotoLocation[]>("/places/map");
    return response.data;
  },

  /** Get photos within a bounding box */
  getPhotosByBbox: async (bbox: BoundingBox): Promise<Photo[]> => {
    const response = await api.get<Photo[]>("/places/photos", { params: bbox });
    return response.data;
  },

  /** Get photos by place name */
  getPhotosByPlace: async (placeName: string): Promise<Photo[]> => {
    const response = await api.get<Photo[]>(`/places/by-name/${encodeURIComponent(placeName)}`);
    return response.data;
  },

  /** Get photos without location data */
  getPhotosWithoutLocation: async (): Promise<Photo[]> => {
    const response = await api.get<Photo[]>("/places/unknown");
    return response.data;
  },

  /** Trigger lazy geocoding for a photo */
  geocodePhoto: async (photoId: number): Promise<PhotoLocation> => {
    const response = await api.post<PhotoLocation>(`/places/geocode/${photoId}`);
    return response.data;
  },

  /** Get location statistics */
  getStats: async (): Promise<LocationStats> => {
    const response = await api.get<LocationStats>("/places/stats");
    return response.data;
  },
};

export const tagsApi = {
  /** Get all custom tags with photo counts */
  getAllTags: async (): Promise<TagSummary[]> => {
    const response = await api.get<TagSummary[]>("/tags");
    return response.data;
  },

  /** Get photos by tag */
  getPhotosByTag: async (tag: string): Promise<Photo[]> => {
    const response = await api.get<Photo[]>(`/tags/${encodeURIComponent(tag)}/photos`);
    return response.data;
  },

  /** Get tags for a specific photo */
  getPhotoTags: async (photoId: number): Promise<string[]> => {
    const response = await api.get<string[]>(`/tags/photo/${photoId}`);
    return response.data;
  },

  /** Add a tag to a photo */
  addTag: async (photoId: number, tag: string): Promise<{ status: string; tag: string }> => {
    const response = await api.post(`/tags/photo/${photoId}`, { tag });
    return response.data;
  },

  /** Add multiple tags to a photo */
  addTags: async (photoId: number, tags: string[]): Promise<{ status: string; added_tags: string[] }> => {
    const response = await api.post(`/tags/photo/${photoId}/multiple`, { tags });
    return response.data;
  },

  /** Remove a tag from a photo */
  removeTag: async (photoId: number, tag: string): Promise<{ status: string; message: string }> => {
    const response = await api.delete(`/tags/photo/${photoId}/${encodeURIComponent(tag)}`);
    return response.data;
  },

  /** Remove all tags from a photo */
  removeAllTags: async (photoId: number): Promise<{ status: string; deleted_count: number }> => {
    const response = await api.delete(`/tags/photo/${photoId}`);
    return response.data;
  },
};
