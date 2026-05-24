"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import type {
  AuraModelId,
  JobResponse,
  OutputFormat,
  TileWeightType,
  UltraSharpModelId,
  UpscaleMode,
} from "@/lib/api";
import { pollJob, startUpscale } from "@/lib/api";
import { JobProgress } from "@/components/JobProgress";

type Props = {
  assetId: string;
  width: number;
  height: number;
  onComplete: (job: JobResponse) => void;
};

const FORMATS: { id: OutputFormat; label: string }[] = [
  { id: "png", label: "PNG" },
  { id: "tiff", label: "TIFF" },
  { id: "jpeg", label: "JPEG" },
];

export function SuperResolutionPanel({ assetId, width, height, onComplete }: Props) {
  const [mode, setMode] = useState<UpscaleMode>("ultrasharp");
  const [overlappingTiles, setOverlappingTiles] = useState(true);
  const [tileWeight, setTileWeight] = useState<TileWeightType>("checkboard");
  const [maxBatchSize, setMaxBatchSize] = useState(8);
  const [auraModelId, setAuraModelId] = useState<AuraModelId>("fal/AuraSR-v2");
  const [ultrasharpModelId, setUltrasharpModelId] =
    useState<UltraSharpModelId>("Kim2091/UltraSharpV2");
  const [fixedSeed, setFixedSeed] = useState(true);
  const [denoiseStrength, setDenoiseStrength] = useState(60);
  const [outputFormat, setOutputFormat] = useState<OutputFormat>("png");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [job, setJob] = useState<JobResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const longEdge = Math.max(width, height);
  const largeWarning = longEdge > 4096;
  const isAiMode = mode === "aura" || mode === "ultrasharp";

  const runUpscale = async () => {
    setLoading(true);
    setError(null);
    try {
      const started = await startUpscale({
        asset_id: assetId,
        overlapping_tiles: overlappingTiles,
        upscale_factor: 4,
        output_format: outputFormat,
        mode,
        denoise_strength: isAiMode ? denoiseStrength / 100 : 0,
        tile_weight_type: tileWeight,
        max_batch_size: maxBatchSize,
        model_id: mode === "ultrasharp" ? ultrasharpModelId : auraModelId,
        aura_seed: mode === "aura" && fixedSeed ? 42 : null,
      });
      setJob(started);
      const finished = await pollJob(started.job_id, setJob);
      onComplete(finished);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upscale failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5" />
          Super-Resolution
        </CardTitle>
        <CardDescription>
          {width} × {height} → {width * 4} × {height * 4} px
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {mode === "faithful" && (
          <p className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
            Faithful (Lanczos) only enlarges pixels — no AI detail. Use AuraSR or UltraSharp for
            enhancement.
          </p>
        )}
        {mode === "aura" && (
          <p className="rounded-md border border-primary/30 bg-primary/10 px-3 py-2 text-xs text-muted-foreground">
            AuraSR-v2 — subtle GAN upscale, DSLR-friendly. Compare downloads at matched zoom (see
            Export tab).
          </p>
        )}
        {mode === "ultrasharp" && (
          <p className="rounded-md border border-primary/30 bg-primary/10 px-3 py-2 text-xs text-muted-foreground">
            <a
              href="https://huggingface.co/Kim2091/UltraSharpV2"
              className="underline"
              target="_blank"
              rel="noreferrer"
            >
              UltraSharpV2
            </a>{" "}
            (DAT2) — strong detail &amp; decompression for photos, art, and JPEG restoration. First
            run downloads ~140 MB from Hugging Face.
          </p>
        )}

        <div className="space-y-2">
          <Label>Upscale mode</Label>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              variant={mode === "ultrasharp" ? "default" : "outline"}
              onClick={() => setMode("ultrasharp")}
              disabled={loading}
            >
              UltraSharp v2
            </Button>
            <Button
              type="button"
              size="sm"
              variant={mode === "aura" ? "default" : "outline"}
              onClick={() => setMode("aura")}
              disabled={loading}
            >
              AuraSR
            </Button>
            <Button
              type="button"
              size="sm"
              variant={mode === "faithful" ? "default" : "outline"}
              onClick={() => setMode("faithful")}
              disabled={loading}
            >
              Faithful
            </Button>
          </div>
        </div>

        {mode === "ultrasharp" && (
          <div className="space-y-2">
            <Label>UltraSharp variant</Label>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant={ultrasharpModelId === "Kim2091/UltraSharpV2" ? "default" : "outline"}
                onClick={() => setUltrasharpModelId("Kim2091/UltraSharpV2")}
                disabled={loading}
              >
                Full (DAT2)
              </Button>
              <Button
                type="button"
                size="sm"
                variant={
                  ultrasharpModelId === "Kim2091/UltraSharpV2-Lite" ? "default" : "outline"
                }
                onClick={() => setUltrasharpModelId("Kim2091/UltraSharpV2-Lite")}
                disabled={loading}
              >
                Lite (faster)
              </Button>
            </div>
          </div>
        )}

        {isAiMode && (
          <>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="tiles">
                  {mode === "ultrasharp" ? "Tiled processing" : "Overlapping tiles"}
                </Label>
                <p className="text-xs text-muted-foreground">
                  {mode === "ultrasharp"
                    ? "512 px tiles with overlap — off uses larger tiles (more VRAM)"
                    : "Two-pass blend — reduces seams (AuraSR)"}
                </p>
              </div>
              <Switch
                id="tiles"
                checked={overlappingTiles}
                onCheckedChange={setOverlappingTiles}
                disabled={loading}
              />
            </div>

            {mode === "aura" && overlappingTiles && (
              <div className="space-y-2">
                <Label>Tile blend</Label>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant={tileWeight === "checkboard" ? "default" : "outline"}
                    onClick={() => setTileWeight("checkboard")}
                    disabled={loading}
                  >
                    Checkerboard
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant={tileWeight === "constant" ? "default" : "outline"}
                    onClick={() => setTileWeight("constant")}
                    disabled={loading}
                  >
                    Constant 50/50
                  </Button>
                </div>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="denoise">Reduce grain ({denoiseStrength}%)</Label>
              <input
                id="denoise"
                type="range"
                min={0}
                max={60}
                value={denoiseStrength}
                onChange={(e) => setDenoiseStrength(Number(e.target.value))}
                disabled={loading}
                className="w-full"
              />
            </div>

            {mode === "aura" && (
              <>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="w-full"
                  onClick={() => setShowAdvanced((v) => !v)}
                >
                  {showAdvanced ? "Hide" : "Show"} advanced AuraSR settings
                </Button>

                {showAdvanced && (
                  <div className="space-y-4 rounded-md border bg-muted/20 p-4">
                    <div className="space-y-2">
                      <Label>AuraSR version</Label>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant={auraModelId === "fal/AuraSR-v2" ? "default" : "outline"}
                          onClick={() => setAuraModelId("fal/AuraSR-v2")}
                          disabled={loading}
                        >
                          v2
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant={auraModelId === "fal-ai/AuraSR" ? "default" : "outline"}
                          onClick={() => setAuraModelId("fal-ai/AuraSR")}
                          disabled={loading}
                        >
                          v1
                        </Button>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="batch">GPU batch size ({maxBatchSize})</Label>
                      <input
                        id="batch"
                        type="range"
                        min={1}
                        max={16}
                        value={maxBatchSize}
                        onChange={(e) => setMaxBatchSize(Number(e.target.value))}
                        disabled={loading}
                        className="w-full"
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <Label htmlFor="seed">Fixed random seed</Label>
                      <Switch
                        id="seed"
                        checked={fixedSeed}
                        onCheckedChange={setFixedSeed}
                        disabled={loading}
                      />
                    </div>
                  </div>
                )}
              </>
            )}
          </>
        )}

        <div className="space-y-2">
          <Label>Export format</Label>
          <div className="flex flex-wrap gap-2">
            {FORMATS.map((f) => (
              <Button
                key={f.id}
                type="button"
                size="sm"
                variant={outputFormat === f.id ? "default" : "outline"}
                onClick={() => setOutputFormat(f.id)}
                disabled={loading}
              >
                {f.label}
              </Button>
            ))}
          </div>
        </div>

        {largeWarning && (
          <p className="text-xs text-amber-400">
            Long edge exceeds 4096 px. Crop tighter before upscaling.
          </p>
        )}
        <Button type="button" className="w-full" onClick={runUpscale} disabled={loading || largeWarning}>
          {loading ? "Upscaling…" : "Upscale 4×"}
        </Button>
        {job && <JobProgress job={job} />}
        {error && <p className="text-sm text-destructive">{error}</p>}
      </CardContent>
    </Card>
  );
}
