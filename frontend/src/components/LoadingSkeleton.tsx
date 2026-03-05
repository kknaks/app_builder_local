"use client";

interface SkeletonProps {
  className?: string;
}

/** Generic skeleton bar */
export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div
      className={`animate-skeleton rounded bg-gray-700/60 ${className}`}
    />
  );
}

/** Skeleton for project list items */
export function ProjectListSkeleton() {
  return (
    <div className="space-y-1 px-4 py-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 py-2">
          <Skeleton className="h-4 w-4 rounded-full" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3.5 w-3/4" />
            <Skeleton className="h-2.5 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Skeleton for dashboard/flow view */
export function DashboardSkeleton() {
  return (
    <div className="flex h-full items-center justify-center p-8">
      <div className="flex items-center gap-8">
        {/* Simulated flow nodes */}
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4">
            <Skeleton className="h-12 w-28 rounded-lg" />
            {i < 3 && <Skeleton className="h-0.5 w-12" />}
          </div>
        ))}
      </div>
    </div>
  );
}

/** Skeleton for chat messages */
export function ChatSkeleton() {
  return (
    <div className="space-y-3 px-4 py-3">
      {/* Agent message */}
      <div className="flex justify-start">
        <div className="max-w-[80%] space-y-1.5">
          <Skeleton className="h-3 w-12" />
          <Skeleton className="h-16 w-56 rounded-lg" />
        </div>
      </div>
      {/* User message */}
      <div className="flex justify-end">
        <Skeleton className="h-10 w-40 rounded-lg" />
      </div>
      {/* Agent message */}
      <div className="flex justify-start">
        <div className="max-w-[80%] space-y-1.5">
          <Skeleton className="h-3 w-12" />
          <Skeleton className="h-20 w-64 rounded-lg" />
        </div>
      </div>
    </div>
  );
}
