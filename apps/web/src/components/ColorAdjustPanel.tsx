"use client";

import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  DEFAULT_COLOR_ADJUST,
  type ColorAdjustState,
} from "@/lib/color-adjust";

type Props = {
  color: ColorAdjustState;
  onChange: (color: ColorAdjustState) => void;
  isRaw: boolean;
  previewLoading?: boolean;
  previewSynced?: boolean;
};

export function ColorAdjustPanel({
  color,
  onChange,
  isRaw,
  previewLoading = false,
  previewSynced = true,
}: Props) {
  const patch = (partial: Partial<ColorAdjustState>) =>
    onChange({ ...color, ...partial });

  return (
    <aside className="flex h-full flex-col gap-4">
      <div>
        <h3 className="text-sm font-semibold">Color & balance</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Adjustments update the crop preview live. Export uses full resolution on Apply crop.
        </p>
        {previewLoading && (
          <p className="mt-2 flex items-center gap-1.5 text-xs text-primary">
            <Loader2 className="h-3 w-3 animate-spin" />
            Updating preview…
          </p>
        )}
        {!previewLoading && !previewSynced && (
          <p className="mt-2 text-xs text-amber-400">Preview approximate — retrying server render</p>
        )}
      </div>

      {isRaw && (
        <div className="space-y-2">
          <Label className="text-xs">White balance</Label>
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              className="flex-1"
              variant={color.whiteBalance === "camera" ? "default" : "outline"}
              onClick={() => patch({ whiteBalance: "camera" })}
            >
              As shot
            </Button>
            <Button
              type="button"
              size="sm"
              className="flex-1"
              variant={color.whiteBalance === "auto" ? "default" : "outline"}
              onClick={() => patch({ whiteBalance: "auto" })}
            >
              Auto
            </Button>
          </div>
        </div>
      )}

      <div className="flex-1 space-y-4 overflow-y-auto pr-1">
        <SliderRow
          id="exposure"
          label="Exposure"
          min={-1}
          max={1}
          step={0.05}
          value={color.exposure}
          display={(v) => (v > 0 ? `+${v.toFixed(2)}` : v.toFixed(2))}
          onChange={(exposure) => patch({ exposure })}
        />
        <SliderRow
          id="brightness"
          label="Brightness"
          min={0.5}
          max={1.5}
          step={0.02}
          value={color.brightness}
          display={(v) => `${Math.round(v * 100)}%`}
          onChange={(brightness) => patch({ brightness })}
        />
        <SliderRow
          id="contrast"
          label="Contrast"
          min={0.5}
          max={1.5}
          step={0.02}
          value={color.contrast}
          display={(v) => `${Math.round(v * 100)}%`}
          onChange={(contrast) => patch({ contrast })}
        />
        <SliderRow
          id="saturation"
          label="Saturation"
          min={0}
          max={2}
          step={0.02}
          value={color.saturation}
          display={(v) => `${Math.round(v * 100)}%`}
          onChange={(saturation) => patch({ saturation })}
        />
        <SliderRow
          id="temperature"
          label="Temperature"
          hint="cool ← → warm"
          min={-100}
          max={100}
          step={1}
          value={color.temperature}
          display={(v) => `${v > 0 ? "+" : ""}${v}`}
          onChange={(temperature) => patch({ temperature })}
        />
        <SliderRow
          id="tint"
          label="Tint"
          hint="green ← → magenta"
          min={-100}
          max={100}
          step={1}
          value={color.tint}
          display={(v) => `${v > 0 ? "+" : ""}${v}`}
          onChange={(tint) => patch({ tint })}
        />
      </div>

      <Button
        type="button"
        size="sm"
        variant="outline"
        className="w-full shrink-0"
        onClick={() => onChange(DEFAULT_COLOR_ADJUST)}
      >
        Reset color
      </Button>
    </aside>
  );
}

function SliderRow({
  id,
  label,
  hint,
  min,
  max,
  step,
  value,
  display,
  onChange,
}: {
  id: string;
  label: string;
  hint?: string;
  min: number;
  max: number;
  step: number;
  value: number;
  display: (v: number) => string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between gap-2 text-sm">
        <Label htmlFor={id} className="leading-tight">
          {label}
          {hint && (
            <span className="mt-0.5 block text-xs font-normal text-muted-foreground">{hint}</span>
          )}
        </Label>
        <span className="shrink-0 tabular-nums text-muted-foreground">{display(value)}</span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-primary"
      />
    </div>
  );
}
