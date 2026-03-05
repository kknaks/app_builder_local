"use client";

export interface ReviewResult {
  agent_id: string;
  agent_label: string;
  status: "approve" | "concern" | "reject";
  summary: string;
  details?: string[];
}

const STATUS_CONFIG: Record<
  ReviewResult["status"],
  { icon: string; color: string; bg: string; border: string }
> = {
  approve: {
    icon: "✅",
    color: "text-green-400",
    bg: "bg-green-900/20",
    border: "border-green-700/40",
  },
  concern: {
    icon: "⚠️",
    color: "text-yellow-400",
    bg: "bg-yellow-900/20",
    border: "border-yellow-700/40",
  },
  reject: {
    icon: "❌",
    color: "text-red-400",
    bg: "bg-red-900/20",
    border: "border-red-700/40",
  },
};

const AGENT_COLORS: Record<string, string> = {
  be: "text-green-400",
  fe: "text-blue-400",
  de: "text-pink-400",
  pl: "text-yellow-400",
  pm: "text-purple-400",
};

interface ReviewCardProps {
  review: ReviewResult;
}

export default function ReviewCard({ review }: ReviewCardProps) {
  const config = STATUS_CONFIG[review.status];
  const agentColor = AGENT_COLORS[review.agent_id] || "text-gray-400";

  return (
    <div
      className={`rounded-lg border ${config.border} ${config.bg} p-3 transition-all hover:brightness-110`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-bold ${agentColor}`}>
            [{review.agent_label}]
          </span>
          <span className="text-xs text-gray-500">에이전트</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span>{config.icon}</span>
          <span className={`text-xs font-medium ${config.color}`}>
            {review.status === "approve"
              ? "승인"
              : review.status === "concern"
              ? "우려사항"
              : "반려"}
          </span>
        </div>
      </div>

      {/* Summary */}
      <p className="text-sm text-gray-300 leading-relaxed">{review.summary}</p>

      {/* Details */}
      {review.details && review.details.length > 0 && (
        <ul className="mt-2 space-y-1">
          {review.details.map((detail, i) => (
            <li
              key={i}
              className="flex items-start gap-1.5 text-xs text-gray-400"
            >
              <span className="mt-0.5 flex-shrink-0">•</span>
              <span>{detail}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
