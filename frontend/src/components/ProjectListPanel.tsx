"use client";

import { useEffect, useState } from "react";
import { useProjectStore } from "@/stores/useProjectStore";
import CreateProjectModal from "./CreateProjectModal";

const STATUS_ICONS: Record<string, string> = {
  pending: "○",
  running: "●",
  completed: "✅",
  failed: "❌",
};

const PHASE_LABELS = [
  { key: "idea", label: "아이디어" },
  { key: "planning", label: "기획" },
  { key: "review", label: "검토" },
  { key: "implementation", label: "구현" },
  { key: "deploy", label: "배포" },
];

export default function ProjectListPanel() {
  const {
    projects,
    selectedId,
    loading,
    fetchProjects,
    deleteProject,
    selectProject,
  } = useProjectStore();

  const [showCreate, setShowCreate] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  return (
    <div className="flex h-full flex-col bg-gray-900 text-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-700 px-4 py-3">
        <h2 className="text-sm font-bold tracking-wide text-gray-300 uppercase">
          프로젝트
        </h2>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-md bg-blue-600 px-3 py-1 text-xs font-medium hover:bg-blue-500 transition"
        >
          + 새 프로젝트
        </button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {loading && (
          <p className="p-4 text-sm text-gray-500">로딩 중...</p>
        )}
        {!loading && projects.length === 0 && (
          <p className="p-4 text-sm text-gray-500">
            프로젝트가 없습니다.
          </p>
        )}
        {projects.map((project) => (
          <div
            key={project.id}
            className={`border-b border-gray-800 ${
              selectedId === project.id ? "bg-gray-800" : ""
            }`}
          >
            {/* Project card */}
            <div
              className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-800/60 transition"
              onClick={() => {
                selectProject(project.id);
                setExpandedId(
                  expandedId === project.id ? null : project.id
                );
              }}
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs">
                    {STATUS_ICONS[project.status] || "○"}
                  </span>
                  <span className="truncate text-sm font-medium">
                    {project.name}
                  </span>
                </div>
                <p className="mt-0.5 truncate text-xs text-gray-500">
                  {project.idea}
                </p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm(`"${project.name}" 프로젝트를 삭제하시겠습니까?`)) {
                    deleteProject(project.id);
                  }
                }}
                className="ml-2 flex-shrink-0 rounded p-1 text-gray-500 hover:bg-red-900/30 hover:text-red-400 transition"
                title="삭제"
              >
                <svg
                  className="h-4 w-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            </div>

            {/* Phase tree (expanded) */}
            {expandedId === project.id && (
              <div className="pb-2 pl-8 pr-4">
                {PHASE_LABELS.map((phase) => (
                  <div
                    key={phase.key}
                    className="flex items-center gap-2 py-1 text-xs text-gray-400"
                  >
                    <span>{STATUS_ICONS.pending}</span>
                    <span>{phase.label}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <CreateProjectModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
      />
    </div>
  );
}
