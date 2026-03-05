"use client";

import { useEffect, useState } from "react";
import { useProjectStore } from "@/stores/useProjectStore";
import type { Project } from "@/lib/api";
import CreateProjectModal from "./CreateProjectModal";
import ConfirmDialog from "./ConfirmDialog";
import EmptyState from "./EmptyState";
import { ProjectListSkeleton } from "./LoadingSkeleton";
import { toastError, toastSuccess } from "@/store/toastStore";

// Project status → overall icon
const PROJECT_STATUS_ICONS: Record<string, string> = {
  created: "○",
  planning: "🔵",
  plan_complete: "📝",
  reviewing: "🔍",
  review_complete: "📋",
  approved: "✅",
  sprint_planning: "📋",
  sprint_ready: "📋",
  sprint_complete: "📋",
  implementing: "🔨",
  testing: "🧪",
  completed: "🎉",
  failed: "❌",
};

// Phase status icons
const PHASE_STATUS: Record<
  string,
  { icon: string; color: string }
> = {
  pending: { icon: "○", color: "text-gray-500" },
  active: { icon: "●", color: "text-blue-400" },
  completed: { icon: "✅", color: "text-green-400" },
  failed: { icon: "❌", color: "text-red-400" },
};

// Determine phase statuses based on project status
function getPhaseStatuses(projectStatus: string) {
  const phases = [
    { key: "idea", label: "아이디어" },
    { key: "planning", label: "기획 구체화" },
    { key: "review", label: "기획 검토" },
    { key: "approve", label: "승인" },
    { key: "implementation", label: "구현" },
    { key: "deploy", label: "배포" },
  ];

  const statusMap: Record<string, number> = {
    created: 0,
    planning: 1,
    plan_complete: 2,
    reviewing: 2,
    review_complete: 3,
    approved: 3,
    sprint_planning: 4,
    sprint_ready: 4,
    sprint_complete: 4,
    implementing: 4,
    testing: 5,
    completed: 5,
    failed: -1,
  };

  const currentIdx = statusMap[projectStatus] ?? -1;

  return phases.map((phase, idx) => {
    let phaseStatus: "pending" | "active" | "completed" | "failed";

    if (projectStatus === "failed") {
      phaseStatus = idx <= currentIdx ? "completed" : "pending";
      if (idx === currentIdx) phaseStatus = "failed";
    } else if (idx < currentIdx) {
      phaseStatus = "completed";
    } else if (idx === currentIdx) {
      if (
        projectStatus === "plan_complete" ||
        projectStatus === "review_complete" ||
        projectStatus === "approved" ||
        projectStatus === "completed"
      ) {
        phaseStatus = "completed";
      } else {
        phaseStatus = "active";
      }
    } else {
      phaseStatus = "pending";
    }

    return { ...phase, status: phaseStatus };
  });
}

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
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchProjects().catch((e) => {
      toastError(`프로젝트 목록 로드 실패: ${(e as Error).message}`);
    });
  }, [fetchProjects]);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteProject(deleteTarget.id);
      toastSuccess(`"${deleteTarget.name}" 프로젝트가 삭제되었습니다.`);
      setDeleteTarget(null);
    } catch (err) {
      toastError(`삭제 실패: ${(err as Error).message}`);
    } finally {
      setDeleting(false);
    }
  };

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
        {loading && <ProjectListSkeleton />}
        {!loading && projects.length === 0 && (
          <EmptyState
            icon="🚀"
            title="프로젝트가 없습니다"
            description="새 프로젝트를 만들어 AI 개발팀과 함께 앱을 만들어보세요."
            action={{
              label: "새 프로젝트 만들기",
              onClick: () => setShowCreate(true),
            }}
          />
        )}
        {projects.map((project) => {
          const phaseStatuses = getPhaseStatuses(project.status);
          const statusIcon =
            PROJECT_STATUS_ICONS[project.status] || "○";

          return (
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
                    <span className="text-xs">{statusIcon}</span>
                    <span className="truncate text-sm font-medium">
                      {project.name}
                    </span>
                  </div>
                  <p className="mt-0.5 truncate text-xs text-gray-500">
                    {project.idea}
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  {/* Expand indicator */}
                  <span className="text-xs text-gray-600">
                    {expandedId === project.id ? "▾" : "▸"}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteTarget(project);
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
              </div>

              {/* Phase tree (expanded) */}
              {expandedId === project.id && (
                <div className="pb-2 pl-8 pr-4">
                  {phaseStatuses.map((phase) => {
                    const cfg = PHASE_STATUS[phase.status];
                    const isActive = phase.status === "active";
                    return (
                      <div
                        key={phase.key}
                        className={`flex items-center gap-2 py-1 text-xs ${cfg.color} ${
                          isActive ? "font-medium" : ""
                        }`}
                      >
                        <span>{cfg.icon}</span>
                        <span>{phase.label}</span>
                        {isActive && (
                          <span className="ml-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-blue-400" />
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <CreateProjectModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        title="프로젝트 삭제"
        description={
          deleteTarget
            ? `"${deleteTarget.name}" 프로젝트를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`
            : ""
        }
        confirmLabel="삭제"
        cancelLabel="취소"
        variant="danger"
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
