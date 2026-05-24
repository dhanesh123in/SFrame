"use client";

import { useState } from "react";
import { Download } from "lucide-react";
import { BeforeAfterSlider } from "@/components/BeforeAfterSlider";
import { CropWorkspace } from "@/components/CropWorkspace";
import { ImageUploader } from "@/components/ImageUploader";
import { HistoryPanel } from "@/components/HistoryPanel";
import { SuperResolutionPanel } from "@/components/SuperResolutionPanel";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { AssetResponse, JobResponse } from "@/lib/api";
import { downloadUrl, formatBytes, previewUrl } from "@/lib/api";

type Step = "import" | "crop" | "enhance" | "export";
type MainTab = "workflow" | "history";

export default function HomePage() {
  const [mainTab, setMainTab] = useState<MainTab>("workflow");
  const [step, setStep] = useState<Step>("import");
  const [original, setOriginal] = useState<AssetResponse | null>(null);
  const [workingId, setWorkingId] = useState<string | null>(null);
  const [workingSize, setWorkingSize] = useState({ width: 0, height: 0 });
  const [upscaleJob, setUpscaleJob] = useState<JobResponse | null>(null);

  const activeId = workingId ?? original?.asset_id ?? null;

  const handleUploaded = (asset: AssetResponse) => {
    setOriginal(asset);
    setWorkingId(asset.asset_id);
    setWorkingSize({ width: asset.width, height: asset.height });
    setUpscaleJob(null);
    setStep("crop");
  };

  const handleCropped = (croppedId: string, width: number, height: number) => {
    setWorkingId(croppedId);
    setWorkingSize({ width, height });
    setUpscaleJob(null);
    setStep("enhance");
  };

  const handleUpscaleComplete = (job: JobResponse) => {
    setUpscaleJob(job);
    setStep("export");
  };

  const reset = () => {
    setOriginal(null);
    setWorkingId(null);
    setWorkingSize({ width: 0, height: 0 });
    setUpscaleJob(null);
    setStep("import");
  };

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-4 py-10">
      <header className="mb-10">
        <h1 className="text-3xl font-bold tracking-tight">SFrame</h1>
        <p className="mt-1 text-muted-foreground">
          Crop DSLR images at full resolution, then upscale with UltraSharpV2 (default) or AuraSR
        </p>
      </header>

      <Tabs value={mainTab} onValueChange={(v) => setMainTab(v as MainTab)} className="mb-6">
        <TabsList>
          <TabsTrigger value="workflow">Workflow</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>
        <TabsContent value="history" className="mt-6">
          <HistoryPanel />
        </TabsContent>
      </Tabs>

      {mainTab === "workflow" && (
      <Tabs value={step} onValueChange={(v) => setStep(v as Step)}>
        <TabsList className="mb-6 grid w-full grid-cols-4">
          <TabsTrigger value="import" disabled={!original && step !== "import"}>
            Import
          </TabsTrigger>
          <TabsTrigger value="crop" disabled={!original}>
            Crop
          </TabsTrigger>
          <TabsTrigger value="enhance" disabled={!activeId}>
            Enhance
          </TabsTrigger>
          <TabsTrigger value="export" disabled={!upscaleJob?.result_asset_id}>
            Export
          </TabsTrigger>
        </TabsList>

        <TabsContent value="import">
          <ImageUploader onUploaded={handleUploaded} />
        </TabsContent>

        <TabsContent value="crop">
          {original && (
            <CropWorkspace asset={original} onCropped={handleCropped} />
          )}
        </TabsContent>

        <TabsContent value="enhance">
          {activeId && workingSize.width > 0 && (
            <div className="grid gap-6 lg:grid-cols-2">
              <div className="overflow-hidden rounded-lg border">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={previewUrl(activeId)}
                  alt="Cropped preview"
                  className="max-h-[min(50vh,480px)] w-full object-contain"
                />
              </div>
              <SuperResolutionPanel
                assetId={activeId}
                width={workingSize.width}
                height={workingSize.height}
                onComplete={handleUpscaleComplete}
              />
            </div>
          )}
        </TabsContent>

        <TabsContent value="export">
          {activeId && upscaleJob?.result_asset_id && (
            <div className="space-y-6">
              <div className="space-y-2 rounded-md border bg-muted/30 p-4 text-sm text-muted-foreground">
                <p className="font-medium text-foreground">Checking in Mac Preview</p>
                <ul className="list-inside list-disc space-y-1">
                  <li>
                    Select the upscaled file → <strong>Tools → Show Inspector</strong> (⌘I). Width and
                    height must be exactly <strong>4×</strong> the cropped file (e.g. 3000×2000 →
                    12000×8000).
                  </li>
                  <li>
                    <strong>Exact 25% zoom in Preview:</strong> open the upscaled file → if needed{" "}
                    <strong>View → Show Toolbar</strong> → click the <strong>zoom percentage</strong>{" "}
                    in the toolbar (e.g. “Fit to Window” or “12%”) → choose <strong>25%</strong> from
                    the menu, or type <strong>25</strong> and press Return. (⌘+ and ⌘− only step zoom;
                    they do not jump to 25%.)
                  </li>
                  <li>
                    Fair compare: cropped TIFF at <strong>100%</strong> (View → Actual Size, ⌘0) vs
                    upscaled PNG at <strong>25%</strong> — same on-screen scale. Both at “fit to window”
                    look equally soft.
                  </li>
                  <li>
                    AuraSR-v2 on clean DSLR/CR2 output is intentionally subtle (less fake texture than
                    v1). Use <strong>Reduce grain = 0%</strong> and look at edges, fabric, and foliage
                    — not overall “wow” at fit-to-window zoom.
                  </li>
                  <li>
                    Download <strong>upscaled</strong> only (not “cropped pre-upscale”). The upscaled
                    PNG is usually much larger on disk.
                  </li>
                </ul>
              </div>
              {upscaleJob.input_width && upscaleJob.result_width && (
                <p className="text-sm">
                  {upscaleJob.input_width} × {upscaleJob.input_height} px →{" "}
                  <strong>
                    {upscaleJob.result_width} × {upscaleJob.result_height} px
                  </strong>
                  {upscaleJob.result_file_size != null && (
                    <> · {formatBytes(upscaleJob.result_file_size)}</>
                  )}
                  {upscaleJob.upscale_mode && (
                    <>
                      {" "}
                      · mode:{" "}
                      {upscaleJob.upscale_mode === "aura"
                        ? "AuraSR"
                        : upscaleJob.upscale_mode === "ultrasharp"
                          ? "UltraSharpV2"
                          : "Lanczos"}
                    </>
                  )}
                </p>
              )}
              <BeforeAfterSlider
                beforeSrc={previewUrl(activeId)}
                afterSrc={previewUrl(upscaleJob.result_asset_id)}
                beforeLabel="Cropped (preview)"
                afterLabel="Upscaled 4× (preview)"
              />
              <div className="flex flex-wrap gap-3">
                <Button asChild>
                  <a
                    href={downloadUrl(upscaleJob.result_asset_id)}
                    download={upscaleJob.result_filename ?? `upscaled.${upscaleJob.output_format ?? "png"}`}
                  >
                    <Download className="h-4 w-4" />
                    Download upscaled ({(upscaleJob.output_format ?? "png").toUpperCase()})
                  </a>
                </Button>
                <Button variant="outline" asChild>
                  <a href={downloadUrl(activeId)} download>
                    Download cropped (pre-upscale)
                  </a>
                </Button>
                <Button variant="ghost" onClick={reset}>
                  Start over
                </Button>
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>
      )}

      {original && mainTab === "workflow" && (
        <aside className="mt-8 rounded-lg border bg-card/50 p-4 text-sm text-muted-foreground">
          <p>
            <strong className="text-foreground">{original.filename}</strong>
            {original.exif_summary && <> · {original.exif_summary}</>}
          </p>
          {workingSize.width > 0 && (
            <p className="mt-1">
              Working: {workingSize.width} × {workingSize.height} px
            </p>
          )}
        </aside>
      )}
    </main>
  );
}
