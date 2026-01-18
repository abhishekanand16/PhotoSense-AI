/** API service for communicating with FastAPI backend. */

import axios from "axios";

const API_BASE_URL = "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

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
};

export const peopleApi = {
  list: async (): Promise<Person[]> => {
    const response = await api.get<Person[]>("/people");
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

export const statsApi = {
  get: async () => {
    const response = await api.get("/stats");
    return response.data;
  },
};
