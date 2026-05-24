"use client";

import { useCallback, useEffect, useState } from "react";
import { Download, RefreshCw, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import type { HistoryAssetItem, HistorySession } from "@/lib/api";
import { deleteHistoryAssets, downloadUrl, fetchHistory, formatBytes } from "@/lib/api";

const KIND_LABEL: Record<string, string> = {
  raw: "RAW",
  original: "Original",
  cropped: "Cropped",
  upscaled: "Upscaled 4×",
};

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

type SelectableAsset = HistoryAssetItem & { sessionId: string };

function collectSessionAssets(session: HistorySession): SelectableAsset[] {
  const out: SelectableAsset[] = [
    { ...session.root, sessionId: session.session_id },
  ];
  if (session.cropped) {
    out.push({ ...session.cropped, sessionId: session.session_id });
  }
  if (session.upscaled) {
    out.push({ ...session.upscaled, sessionId: session.session_id });
  }
  return out;
}

export function HistoryPanel() {
  const [sessions, setSessions] = useState<HistorySession[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHistory();
      setSessions(data.sessions);
      setTotal(data.total);
      setSelected(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load history");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggleAsset = (assetId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(assetId)) next.delete(assetId);
      else next.add(assetId);
      return next;
    });
  };

  const toggleSession = (session: HistorySession) => {
    const ids = collectSessionAssets(session).map((a) => a.asset_id);
    const allSelected = ids.every((id) => selected.has(id));
    setSelected((prev) => {
      const next = new Set(prev);
      for (const id of ids) {
        if (allSelected) next.delete(id);
        else next.add(id);
      }
      return next;
    });
  };

  const selectAll = () => {
    const ids = sessions.flatMap((s) => collectSessionAssets(s).map((a) => a.asset_id));
    setSelected(new Set(ids));
  };

  const clearSelection = () => setSelected(new Set());

  const handleDelete = async () => {
    if (selected.size === 0) return;
    const n = selected.size;
    if (
      !window.confirm(
        `Delete ${n} asset(s) and their files from disk? Child outputs (crop/upscale) of selected items are removed too.`,
      )
    ) {
      return;
    }
    setDeleting(true);
    setError(null);
    try {
      await deleteHistoryAssets([...selected]);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <CardTitle>History</CardTitle>
            <CardDescription>
              {total} import{total === 1 ? "" : "s"} · select items to remove from database and
              storage
            </CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" size="sm" variant="outline" onClick={load} disabled={loading}>
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={selectAll} disabled={loading}>
              Select all
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={clearSelection}
              disabled={selected.size === 0}
            >
              Clear
            </Button>
            <Button
              type="button"
              size="sm"
              variant="destructive"
              onClick={handleDelete}
              disabled={deleting || selected.size === 0}
            >
              <Trash2 className="h-4 w-4" />
              Delete ({selected.size})
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p className="text-sm text-destructive">{error}</p>}
        {loading && sessions.length === 0 && (
          <p className="text-sm text-muted-foreground">Loading…</p>
        )}
        {!loading && sessions.length === 0 && (
          <p className="text-sm text-muted-foreground">No processed images yet.</p>
        )}
        <ul className="space-y-4">
          {sessions.map((session) => {
            const assets = collectSessionAssets(session);
            const sessionSelected = assets.every((a) => selected.has(a.asset_id));

            return (
              <li
                key={session.session_id}
                className="rounded-lg border bg-card/50 p-4"
              >
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-input"
                      checked={sessionSelected}
                      onChange={() => toggleSession(session)}
                      aria-label="Select entire session"
                    />
                    <span className="text-sm font-medium">{session.root.filename}</span>
                    <span className="text-xs text-muted-foreground">
                      {formatDate(session.created_at)}
                    </span>
                  </div>
                  {session.job && (
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
                      {session.job.status}
                      {session.job.upscale_mode && ` · ${session.job.upscale_mode}`}
                    </span>
                  )}
                </div>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {assets.map((asset) => (
                    <AssetHistoryCard
                      key={asset.asset_id}
                      asset={asset}
                      selected={selected.has(asset.asset_id)}
                      onToggle={() => toggleAsset(asset.asset_id)}
                    />
                  ))}
                </div>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}

function AssetHistoryCard({
  asset,
  selected,
  onToggle,
}: {
  asset: SelectableAsset;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      className={`flex gap-3 rounded-md border p-2 transition-colors ${
        selected ? "border-primary bg-primary/5" : "border-border"
      }`}
    >
      <input
        type="checkbox"
        className="mt-1 h-4 w-4 shrink-0 rounded border-input"
        checked={selected}
        onChange={onToggle}
        aria-label={`Select ${asset.filename}`}
      />
      <div className="min-w-0 flex-1">
        <div className="mb-2 aspect-video overflow-hidden rounded bg-black/40">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={asset.preview_url}
            alt=""
            className="h-full w-full object-contain"
            loading="lazy"
          />
        </div>
        <Label className="text-xs font-medium">{KIND_LABEL[asset.kind] ?? asset.kind}</Label>
        <p className="truncate text-xs text-muted-foreground" title={asset.filename}>
          {asset.filename}
        </p>
        <p className="text-xs text-muted-foreground">
          {asset.width} × {asset.height} · {formatBytes(asset.file_size)}
        </p>
        <Button asChild size="sm" variant="ghost" className="mt-1 h-7 px-2 text-xs">
          <a href={downloadUrl(asset.asset_id)} download={asset.filename}>
            <Download className="mr-1 h-3 w-3" />
            Download
          </a>
        </Button>
      </div>
    </div>
  );
}
