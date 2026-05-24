"use client";

import {
  ReactCompareSlider,
  ReactCompareSliderImage,
} from "react-compare-slider";

type Props = {
  beforeSrc: string;
  afterSrc: string;
  beforeLabel?: string;
  afterLabel?: string;
};

export function BeforeAfterSlider({
  beforeSrc,
  afterSrc,
  beforeLabel = "Before",
  afterLabel = "After (4×)",
}: Props) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{beforeLabel}</span>
        <span>{afterLabel}</span>
      </div>
      <div className="overflow-hidden rounded-lg border">
        <ReactCompareSlider
          itemOne={
            <ReactCompareSliderImage
              src={beforeSrc}
              alt={beforeLabel}
              style={{ objectFit: "contain", maxHeight: "min(70vh, 800px)", width: "100%" }}
            />
          }
          itemTwo={
            <ReactCompareSliderImage
              src={afterSrc}
              alt={afterLabel}
              style={{ objectFit: "contain", maxHeight: "min(70vh, 800px)", width: "100%" }}
            />
          }
          className="w-full"
        />
      </div>
    </div>
  );
}
