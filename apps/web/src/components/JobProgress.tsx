"use client";

import type { JobResponse } from "@/lib/api";

type Props = {
  job: JobResponse;
};

export function JobProgress({ job }: Props) {
  const statusLabel: Record<string, string> = {
    pending: "Queued",
    running: "Processing",
    completed: "Complete",
    failed: "Failed",
  };

  return (
    <div className="space-y-2 rounded-md border bg-muted/30 p-4">
      <div className="flex justify-between text-sm">
        <span>{statusLabel[job.status] ?? job.status}</span>
        <span>{job.progress}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full bg-primary transition-all duration-300"
          style={{ width: `${job.progress}%` }}
        />
      </div>
      {job.message && (
        <p className="text-xs text-muted-foreground">{job.message}</p>
      )}
      {job.error && (
        <p className="text-xs text-destructive">{job.error}</p>
      )}
    </div>
  );
}
