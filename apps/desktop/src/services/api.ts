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

export const photosApi = {
  list: async (): Promise<Photo[]> => {
    const response = await api.get<Photo[]>("/photos");
    return response.data;
  },
  get: async (id: number): Promise<Photo> => {
    const response = await api.get<Photo>(`/photos/${id}`);
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
  getPhotosByCategory: async (category: string): Promise<Photo[]> => {
    const response = await api.get<Photo[]>(`/objects/category/${category}/photos`);
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
