"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Cropper,
  CropperRef,
  RectangleStencil,
  ImageRestriction,
} from "react-advanced-cropper";
import type { Coordinates } from "advanced-cropper";
import "react-advanced-cropper/dist/style.css";
import { FlipHorizontal, FlipVertical, RotateCw, ZoomIn, ZoomOut } from "lucide-react";
import { ColorAdjustPanel } from "@/components/ColorAdjustPanel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { useLivePreview } from "@/hooks/useLivePreview";
import {
  DEFAULT_COLOR_ADJUST,
  type ColorAdjustState,
} from "@/lib/color-adjust";
import type { AssetResponse } from "@/lib/api";
import { cropAsset } from "@/lib/api";

const ASPECTS: { label: string; value: number | undefined }[] = [
  { label: "Free", value: undefined },
  { label: "3:2", value: 3 / 2 },
  { label: "4:3", value: 4 / 3 },
  { label: "16:9", value: 16 / 9 },
  { label: "1:1", value: 1 },
];

const BASE_CROP_HEIGHT = 520;
const MAX_CROP_HEIGHT_VH = 88;

type Props = {
  asset: AssetResponse;
  onCropped: (croppedId: string, width: number, height: number) => void;
};

export function CropWorkspace({ asset, onCropped }: Props) {
  const cropperRef = useRef<CropperRef>(null);
  const savedCoordsRef = useRef<Coordinates | null>(null);
  const [aspect, setAspect] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imageZoom, setImageZoom] = useState(1);
  const [color, setColor] = useState<ColorAdjustState>(DEFAULT_COLOR_ADJUST);

  const isRaw = asset.kind === "raw";
  const {
    src: previewSrc,
    loading: previewLoading,
    synced,
    instantFilter,
  } = useLivePreview(asset.asset_id, color);

  const cropViewportHeight = `min(${MAX_CROP_HEIGHT_VH}vh, ${Math.round(BASE_CROP_HEIGHT * Math.max(1, imageZoom))}px)`;

  const saveCropCoords = useCallback(() => {
    const coords = cropperRef.current?.getCoordinates();
    if (coords) savedCoordsRef.current = coords;
  }, []);

  const restoreCropCoords = useCallback(() => {
    const coords = savedCoordsRef.current;
    if (coords) cropperRef.current?.setCoordinates(coords);
  }, []);

  useEffect(() => {
    saveCropCoords();
  }, [previewSrc, saveCropCoords]);

  const scaleToOriginal = useCallback(
    (coords: { left: number; top: number; width: number; height: number }) => {
      const pw = asset.preview_width || asset.width;
      const ph = asset.preview_height || asset.height;
      const scaleX = asset.width / pw;
      const scaleY = asset.height / ph;
      return {
        x: Math.max(0, Math.round(coords.left * scaleX)),
        y: Math.max(0, Math.round(coords.top * scaleY)),
        width: Math.min(asset.width, Math.round(coords.width * scaleX)),
        height: Math.min(asset.height, Math.round(coords.height * scaleY)),
      };
    },
    [asset.width, asset.height, asset.preview_width, asset.preview_height],
  );

  const handleWheel = (e: React.WheelEvent) => {
    if (!(e.ctrlKey || e.metaKey)) return;
    e.preventDefault();
    e.stopPropagation();
    cropperRef.current?.zoomImage(e.deltaY > 0 ? 0.92 : 1.08);
  };

  const handleColorChange = (next: ColorAdjustState) => {
    saveCropCoords();
    setColor(next);
  };

  const applyCrop = async () => {
    const cropper = cropperRef.current;
    if (!cropper) return;
    const coords = cropper.getCoordinates();
    if (!coords) {
      setError("Could not read crop region");
      return;
    }
    const scaled = scaleToOriginal(coords);
    setLoading(true);
    setError(null);
    try {
      const result = await cropAsset(asset.asset_id, {
        ...scaled,
        rotate: 0,
        flip_horizontal: false,
        flip_vertical: false,
        exposure: color.exposure,
        contrast: color.contrast,
        saturation: color.saturation,
        brightness: color.brightness,
        temperature: color.temperature,
        tint: color.tint,
        white_balance: isRaw ? color.whiteBalance : undefined,
      });
      onCropped(result.cropped_asset_id, result.width, result.height);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Crop failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Crop & color</CardTitle>
        <CardDescription>
          {asset.width} × {asset.height} px · <strong>⌘/Ctrl + scroll</strong> to zoom the image
          {isRaw && <> · RAW develop uses the panel settings on Apply crop</>}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px] lg:gap-0">
          <div className="min-w-0 space-y-4 lg:pr-6">
            <div className="flex flex-wrap gap-2">
              {ASPECTS.map((a) => (
                <Button
                  key={a.label}
                  type="button"
                  size="sm"
                  variant={aspect === a.value ? "default" : "outline"}
                  onClick={() => setAspect(a.value)}
                >
                  {a.label}
                </Button>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => cropperRef.current?.rotateImage(90)}
              >
                <RotateCw className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => cropperRef.current?.flipImage(true, false)}
              >
                <FlipHorizontal className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => cropperRef.current?.flipImage(false, true)}
              >
                <FlipVertical className="h-4 w-4" />
              </Button>
              <Button type="button" size="sm" variant="outline" onClick={() => cropperRef.current?.zoomImage(1.15)}>
                <ZoomIn className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => cropperRef.current?.zoomImage(1 / 1.15)}
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => cropperRef.current?.reset()}>
                Reset view
              </Button>
              <span className="text-xs text-muted-foreground">Zoom {Math.round(imageZoom * 100)}%</span>
            </div>

            <div
              className="relative w-full overflow-auto rounded-lg bg-black/40"
              style={{ height: cropViewportHeight, overscrollBehavior: "contain" }}
              onWheel={handleWheel}
            >
              <div
                className="h-full min-h-full w-full transition-[filter] duration-75"
                style={{ filter: instantFilter === "none" ? undefined : instantFilter }}
              >
                <Cropper
                  ref={cropperRef}
                  src={previewSrc}
                  stencilComponent={RectangleStencil}
                  stencilProps={{ aspectRatio: aspect, grid: true }}
                  defaultSize={({ imageSize }) => ({
                    width: imageSize.width,
                    height: imageSize.height,
                  })}
                  imageRestriction={ImageRestriction.stencil}
                  backgroundWrapperProps={{
                    scaleImage: { wheel: false, touch: true },
                    moveImage: { touch: true, mouse: true },
                  }}
                  onReady={restoreCropCoords}
                  onChange={(cropper) => {
                    const state = cropper.getState();
                    if (!state?.visibleArea?.width || !state.imageSize.width) return;
                    const scale = state.imageSize.width / state.visibleArea.width;
                    if (scale > 0) setImageZoom(scale);
                  }}
                  className="cropper h-full min-h-[360px]"
                />
              </div>
            </div>

            <div className="flex items-center justify-between gap-4">
              <Label className="text-muted-foreground text-xs">⌘/Ctrl + scroll to zoom</Label>
              <Button type="button" onClick={applyCrop} disabled={loading}>
                {loading ? (isRaw ? "Developing RAW…" : "Applying…") : "Apply crop"}
              </Button>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>

          <div className="border-t pt-6 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0">
            <div className="lg:sticky lg:top-4 lg:max-h-[min(88vh,720px)]">
              <ColorAdjustPanel
                color={color}
                onChange={handleColorChange}
                isRaw={isRaw}
                previewLoading={previewLoading}
                previewSynced={synced}
              />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
