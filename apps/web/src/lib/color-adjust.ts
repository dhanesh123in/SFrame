import type { WhiteBalanceMode } from "@/lib/api";

export type ColorAdjustState = {
  exposure: number;
  contrast: number;
  saturation: number;
  brightness: number;
  temperature: number;
  tint: number;
  whiteBalance: WhiteBalanceMode;
};

export const DEFAULT_COLOR_ADJUST: ColorAdjustState = {
  exposure: 0,
  contrast: 1,
  saturation: 1,
  brightness: 1,
  temperature: 0,
  tint: 0,
  whiteBalance: "camera",
};

export function isDefaultColorAdjust(c: ColorAdjustState): boolean {
  return (
    c.exposure === 0 &&
    c.contrast === 1 &&
    c.saturation === 1 &&
    c.brightness === 1 &&
    c.temperature === 0 &&
    c.tint === 0 &&
    c.whiteBalance === "camera"
  );
}

/** Instant CSS preview while the server renders a matching WebP. */
export function previewCssFilter(c: ColorAdjustState): string {
  const expBright = 2 ** (c.exposure * 0.5) * c.brightness;
  const warm = c.temperature / 100;
  const tintShift = c.tint * 0.35;
  const parts = [
    `brightness(${expBright.toFixed(3)})`,
    `contrast(${c.contrast.toFixed(3)})`,
    `saturate(${c.saturation.toFixed(3)})`,
    `hue-rotate(${tintShift.toFixed(1)}deg)`,
  ];
  if (warm > 0) {
    parts.push(`sepia(${(warm * 0.22).toFixed(3)})`);
  } else if (warm < 0) {
    parts.push(`hue-rotate(${(warm * 12).toFixed(1)}deg)`);
  }
  return parts.join(" ");
}
