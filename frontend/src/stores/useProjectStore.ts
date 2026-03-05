import { create } from "zustand";
import type { Project } from "@/lib/api";
import {
  getProjects,
  createProject as apiCreate,
  deleteProject as apiDelete,
} from "@/lib/api";

interface ProjectState {
  projects: Project[];
  selectedId: string | null;
  loading: boolean;
  error: string | null;
  fetchProjects: () => Promise<void>;
  createProject: (name: string, idea: string) => Promise<Project>;
  deleteProject: (id: string) => Promise<void>;
  selectProject: (id: string | null) => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  selectedId: null,
  loading: false,
  error: null,

  fetchProjects: async () => {
    set({ loading: true, error: null });
    try {
      const projects = await getProjects();
      set({ projects, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  createProject: async (name: string, idea: string) => {
    const project = await apiCreate({ name, idea });
    set({ projects: [project, ...get().projects] });
    return project;
  },

  deleteProject: async (id: string) => {
    await apiDelete(id);
    const projects = get().projects.filter((p) => p.id !== id);
    const selectedId = get().selectedId === id ? null : get().selectedId;
    set({ projects, selectedId });
  },

  selectProject: (id) => set({ selectedId: id }),
}));
