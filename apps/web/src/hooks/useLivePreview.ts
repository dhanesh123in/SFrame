"use client";

import { useEffect, useRef, useState } from "react";
import {
  type ColorAdjustState,
  isDefaultColorAdjust,
  previewCssFilter,
} from "@/lib/color-adjust";
import { fetchLivePreview, previewUrl } from "@/lib/api";

function colorEqual(a: ColorAdjustState, b: ColorAdjustState): boolean {
  return (
    a.exposure === b.exposure &&
    a.contrast === b.contrast &&
    a.saturation === b.saturation &&
    a.brightness === b.brightness &&
    a.temperature === b.temperature &&
    a.tint === b.tint &&
    a.whiteBalance === b.whiteBalance
  );
}

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}

export function useLivePreview(assetId: string, color: ColorAdjustState) {
  const debounced = useDebounced(color, 320);
  const [src, setSrc] = useState(() => previewUrl(assetId));
  const [loading, setLoading] = useState(false);
  const [synced, setSynced] = useState(true);
  const blobRef = useRef<string | null>(null);

  const revokeBlob = () => {
    if (blobRef.current) {
      URL.revokeObjectURL(blobRef.current);
      blobRef.current = null;
    }
  };

  useEffect(() => {
    setSrc(previewUrl(assetId));
    setSynced(true);
    revokeBlob();
  }, [assetId]);

  useEffect(() => {
    if (isDefaultColorAdjust(debounced)) {
      revokeBlob();
      setSrc(previewUrl(assetId));
      setSynced(true);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setSynced(false);

    fetchLivePreview(assetId, debounced)
      .then((blob) => {
        if (cancelled) return;
        revokeBlob();
        const url = URL.createObjectURL(blob);
        blobRef.current = url;
        setSrc(url);
        setSynced(true);
      })
      .catch(() => {
        if (!cancelled) setSynced(false);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [assetId, debounced]);

  useEffect(() => () => revokeBlob(), []);

  const pendingServer = !colorEqual(color, debounced);
  const instantFilter =
    pendingServer || loading || !synced ? previewCssFilter(color) : "none";

  return { src, loading, synced, instantFilter, debouncedColor: debounced };
}
