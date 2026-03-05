"use client";

import { useState } from "react";
import { useProjectStore } from "@/stores/useProjectStore";

interface CreateProjectModalProps {
  open: boolean;
  onClose: () => void;
}

export default function CreateProjectModal({
  open,
  onClose,
}: CreateProjectModalProps) {
  const [name, setName] = useState("");
  const [idea, setIdea] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const createProject = useProjectStore((s) => s.createProject);

  if (!open) return null;

  const handleCreate = async () => {
    if (!name.trim() || !idea.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await createProject(name.trim(), idea.trim());
      setName("");
      setIdea("");
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-lg rounded-xl bg-gray-800 p-6 shadow-2xl">
        <h2 className="text-xl font-bold text-white mb-4">새 프로젝트</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              프로젝트 이름
            </label>
            <input
              type="text"
              placeholder="내 앱 이름"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-gray-600 bg-gray-700 px-4 py-2.5 text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              아이디어
            </label>
            <textarea
              placeholder="어떤 앱을 만들고 싶은지 자유롭게 적어주세요..."
              value={idea}
              onChange={(e) => setIdea(e.target.value)}
              rows={4}
              className="w-full rounded-lg border border-gray-600 bg-gray-700 px-4 py-2.5 text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none resize-none"
            />
          </div>
        </div>
        {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
        <div className="mt-4 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm text-gray-300 hover:text-white transition"
          >
            취소
          </button>
          <button
            onClick={handleCreate}
            disabled={saving || !name.trim() || !idea.trim()}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition"
          >
            {saving ? "생성 중..." : "프로젝트 생성"}
          </button>
        </div>
      </div>
    </div>
  );
}
