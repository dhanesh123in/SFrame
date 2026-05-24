/** Same-origin BFF: Next.js rewrites /api/v1/* → FastAPI (API_URL). Works from LAN clients. */
const API_V1 = "/api/v1";

export type AssetResponse = {
  asset_id: string;
  width: number;
  height: number;
  preview_width: number;
  preview_height: number;
  file_size: number;
  mime_type: string;
  preview_url: string;
  filename: string;
  exif_summary?: string | null;
  kind?: string | null;
};

export type WhiteBalanceMode = "camera" | "auto";

export type CropRequest = {
  x: number;
  y: number;
  width: number;
  height: number;
  rotate?: number;
  flip_horizontal?: boolean;
  flip_vertical?: boolean;
  exposure?: number;
  contrast?: number;
  saturation?: number;
  brightness?: number;
  temperature?: number;
  tint?: number;
  white_balance?: WhiteBalanceMode;
};

export type CropResponse = {
  cropped_asset_id: string;
  width: number;
  height: number;
  preview_url: string;
};

export type OutputFormat = "png" | "jpeg" | "tiff";
export type UpscaleMode = "aura" | "faithful" | "ultrasharp";

export type JobResponse = {
  job_id: string;
  status: string;
  progress: number;
  message?: string | null;
  output_format?: string | null;
  result_filename?: string | null;
  result_asset_id?: string | null;
  result_url?: string | null;
  preview_url?: string | null;
  result_width?: number | null;
  result_height?: number | null;
  result_file_size?: number | null;
  input_width?: number | null;
  input_height?: number | null;
  upscale_mode?: string | null;
  error?: string | null;
};

export type TileWeightType = "checkboard" | "constant";
export type AuraModelId = "fal/AuraSR-v2" | "fal-ai/AuraSR";
export type UltraSharpModelId = "Kim2091/UltraSharpV2" | "Kim2091/UltraSharpV2-Lite";

export type UpscaleRequest = {
  asset_id: string;
  overlapping_tiles?: boolean;
  upscale_factor?: number;
  output_format?: OutputFormat;
  mode?: UpscaleMode;
  denoise_strength?: number;
  tile_weight_type?: TileWeightType;
  max_batch_size?: number;
  model_id?: AuraModelId | UltraSharpModelId;
  aura_seed?: number | null;
};

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function parseError(text: string): string {
  try {
    const json = JSON.parse(text);
    const detail = json.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ");
    }
    return json.message ?? text;
  } catch {
    return text || "Request failed";
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(parseError(await res.text()));
  }
  return res.json() as Promise<T>;
}

export function previewUrl(assetId: string): string {
  return `${API_V1}/assets/${assetId}/preview`;
}

export type ColorAdjustParams = {
  exposure: number;
  contrast: number;
  saturation: number;
  brightness: number;
  temperature: number;
  tint: number;
  whiteBalance: WhiteBalanceMode;
};

export function livePreviewUrl(assetId: string, params: ColorAdjustParams): string {
  const q = new URLSearchParams({
    exposure: String(params.exposure),
    contrast: String(params.contrast),
    saturation: String(params.saturation),
    brightness: String(params.brightness),
    temperature: String(params.temperature),
    tint: String(params.tint),
    white_balance: params.whiteBalance,
  });
  return `${API_V1}/assets/${assetId}/preview/live?${q}`;
}

export async function fetchLivePreview(
  assetId: string,
  params: ColorAdjustParams,
): Promise<Blob> {
  const res = await fetch(livePreviewUrl(assetId, params));
  if (!res.ok) {
    throw new Error(parseError(await res.text()));
  }
  return res.blob();
}

export function downloadUrl(assetId: string): string {
  return `${API_V1}/assets/${assetId}/download`;
}

export async function uploadAsset(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<AssetResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    form.append("file", file);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as AssetResponse);
        } catch {
          reject(new Error("Invalid response from server"));
        }
      } else {
        reject(new Error(parseError(xhr.responseText)));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Upload failed — check network connection")));
    xhr.open("POST", `${API_V1}/assets`);
    xhr.send(form);
  });
}

export async function cropAsset(assetId: string, body: CropRequest): Promise<CropResponse> {
  const res = await fetch(`${API_V1}/assets/${assetId}/crop`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse<CropResponse>(res);
}

export async function startUpscale(body: UpscaleRequest): Promise<JobResponse> {
  const res = await fetch(`${API_V1}/jobs/upscale`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse<JobResponse>(res);
}

export async function getJob(jobId: string): Promise<JobResponse> {
  const res = await fetch(`${API_V1}/jobs/${jobId}`);
  return handleResponse<JobResponse>(res);
}

export type HistoryAssetItem = {
  asset_id: string;
  parent_id?: string | null;
  kind: string;
  filename: string;
  mime_type: string;
  width: number;
  height: number;
  file_size: number;
  created_at: string;
  preview_url: string;
};

export type HistoryJobSummary = {
  job_id: string;
  status: string;
  upscale_mode?: string | null;
  output_format?: string | null;
  created_at: string;
  message?: string | null;
};

export type HistorySession = {
  session_id: string;
  created_at: string;
  root: HistoryAssetItem;
  cropped?: HistoryAssetItem | null;
  upscaled?: HistoryAssetItem | null;
  job?: HistoryJobSummary | null;
};

export type HistoryListResponse = {
  sessions: HistorySession[];
  total: number;
  limit: number;
  offset: number;
};

export type DeleteAssetsResponse = {
  deleted_asset_count: number;
  deleted_storage_count: number;
  deleted_ids: string[];
};

export async function fetchHistory(limit = 50, offset = 0): Promise<HistoryListResponse> {
  const res = await fetch(`${API_V1}/history?limit=${limit}&offset=${offset}`);
  return handleResponse<HistoryListResponse>(res);
}

export async function deleteHistoryAssets(assetIds: string[]): Promise<DeleteAssetsResponse> {
  const res = await fetch(`${API_V1}/history`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ asset_ids: assetIds }),
  });
  return handleResponse<DeleteAssetsResponse>(res);
}

export async function pollJob(
  jobId: string,
  onUpdate: (job: JobResponse) => void,
  intervalMs = 2000,
): Promise<JobResponse> {
  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const job = await getJob(jobId);
        onUpdate(job);
        if (job.status === "completed") {
          resolve(job);
        } else if (job.status === "failed") {
          reject(new Error(job.error ?? "Upscale failed"));
        } else {
          setTimeout(tick, intervalMs);
        }
      } catch (err) {
        reject(err);
      }
    };
    tick();
  });
}
