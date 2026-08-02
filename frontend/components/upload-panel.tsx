"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowRight,
  Check,
  FileSpreadsheet,
  ShieldCheck,
  UploadCloud,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { ResolvingIndicator } from "@/components/resolving-indicator";
import { animateInsightMoment } from "@/lib/motion";
import { cn } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ALLOWED_EXTENSIONS = [".csv", ".xlsx", ".xls"];

type Profile = {
  shape: { rows: number; columns: number };
  columns: Record<string, string>;
  sample: Record<string, unknown>[];
  null_counts: Record<string, number>;
};

type UploadResponse = { dataset_id: string; profile: Profile };
type UploadState = "idle" | "uploading" | "uploaded" | "error";
type AnalysisState = "idle" | "running" | "error";

function getExtension(filename: string): string {
  const idx = filename.lastIndexOf(".");
  return idx === -1 ? "" : filename.slice(idx).toLowerCase();
}

function uploadFileWithProgress(
  file: File,
  onProgress: (percent: number) => void
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/upload`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new Error("Server returned an invalid response."));
        }
      } else {
        let message = `Upload failed (HTTP ${xhr.status}).`;
        try {
          const body = JSON.parse(xhr.responseText);
          if (body?.detail) message = body.detail;
        } catch {
          // keep the default message
        }
        reject(new Error(message));
      }
    };

    xhr.onerror = () => reject(new Error("Network error while uploading the file."));

    const formData = new FormData();
    formData.append("file", file);
    xhr.send(formData);
  });
}

/** Label left, figure right, mono and tabular (§11). */
function ValueRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <span className="type-label">{label}</span>
      <span className="type-value text-[14px]">{value}</span>
    </div>
  );
}

export function UploadPanel() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);

  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);

  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);

  const [analysisState, setAnalysisState] = useState<AnalysisState>("idle");
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Profiling finishing is an Insight Moment: the system has learned
  // something about the file and says so (§10).
  useEffect(() => {
    if (uploadState === "uploaded" && profileRef.current) {
      animateInsightMoment(profileRef.current);
    }
  }, [uploadState]);

  const reset = useCallback(() => {
    setFile(null);
    setUploadState("idle");
    setUploadProgress(0);
    setUploadError(null);
    setDatasetId(null);
    setProfile(null);
    setAnalysisState("idle");
    setAnalysisError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  const startUpload = useCallback(async (selected: File) => {
    const ext = getExtension(selected.name);
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setFile(selected);
      setUploadState("error");
      setUploadError(
        `${ext || "That file type"} is not supported. Upload a .csv, .xlsx or .xls file.`
      );
      return;
    }

    setFile(selected);
    setUploadState("uploading");
    setUploadProgress(0);
    setUploadError(null);

    try {
      const result = await uploadFileWithProgress(selected, setUploadProgress);
      setDatasetId(result.dataset_id);
      setProfile(result.profile);
      setUploadState("uploaded");
    } catch (err) {
      setUploadState("error");
      setUploadError(err instanceof Error ? err.message : "Upload failed.");
    }
  }, []);

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setIsDragging(false);
      const dropped = event.dataTransfer.files?.[0];
      if (dropped) startUpload(dropped);
    },
    [startUpload]
  );

  const handleFileInputChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const selected = event.target.files?.[0];
      if (selected) startUpload(selected);
    },
    [startUpload]
  );

  const runAnalysis = useCallback(async () => {
    if (!datasetId) return;
    setAnalysisState("running");
    setAnalysisError(null);

    try {
      const res = await fetch(`${API_URL}/analysis/${datasetId}/run`, { method: "POST" });

      if (!res.ok) {
        let message = `Analysis failed (HTTP ${res.status}).`;
        try {
          const body = await res.json();
          if (body?.detail) message = body.detail;
        } catch {
          // keep the default message
        }
        throw new Error(message);
      }

      const result = await res.json();
      router.push(`/dashboard/${result.run_id}`);
    } catch (err) {
      setAnalysisState("error");
      setAnalysisError(err instanceof Error ? err.message : "Analysis failed.");
    }
  }, [datasetId, router]);

  return (
    <div
      id="upload"
      className="scroll-mt-24 rounded-card border border-border bg-card p-6 shadow-soft"
    >
      <div className="mb-5 flex items-baseline justify-between gap-4">
        <span className="type-body font-semibold text-foreground">Upload a dataset</span>
        <span className="type-label">Accepted: .csv, .xlsx, .xls</span>
      </div>

      {uploadState === "idle" && (
        <>
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                fileInputRef.current?.click();
              }
            }}
            role="button"
            tabIndex={0}
            aria-label="Choose a spreadsheet to upload, or drag one here"
            className={cn(
              "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-input border border-dashed px-6 py-7 text-center transition-colors duration-200",
              "focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none",
              isDragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
            )}
          >
            <span className="flex size-9 items-center justify-center rounded-full bg-primary/10 text-primary">
              <UploadCloud className="size-4" aria-hidden />
            </span>
            <p className="type-body font-medium text-foreground">Drag &amp; drop a file here</p>
            {/* Navy, not coastal-blue: blue-on-white measures ~3.4:1, below
                the 4.5:1 text floor. Underline carries the "link" meaning
                instead of relying on color alone. */}
            <p className="type-small -mt-1">
              <span className="text-label">or </span>
              <span className="font-medium text-foreground underline underline-offset-2">
                click to browse
              </span>
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept={ALLOWED_EXTENSIONS.join(",")}
              onChange={handleFileInputChange}
              className="sr-only"
              tabIndex={-1}
            />
          </div>

          {/* A quiet caption, not a bordered block — the reference doesn't
              carry this element, so it stays subordinate rather than
              competing with the dropzone above it. */}
          <p className="mt-3 flex items-center gap-1.5 type-small text-label">
            <ShieldCheck className="size-3 shrink-0" aria-hidden />
            Your data is never stored or shared.
          </p>
        </>
      )}

      {file && uploadState !== "idle" && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3 rounded-input border border-border px-4 py-3">
            <FileSpreadsheet className="size-5 shrink-0 text-label" aria-hidden />
            <p className="min-w-0 flex-1 truncate type-small font-medium">{file.name}</p>
            {uploadState === "uploaded" && (
              <Check className="size-4 shrink-0 text-green-600" aria-hidden />
            )}
            {uploadState !== "uploading" && (
              <Button variant="ghost" size="icon-sm" onClick={reset} aria-label="Remove file">
                <X className="size-4" />
              </Button>
            )}
          </div>

          {uploadState === "uploading" && (
            <ResolvingIndicator
              label="Reading file"
              value={`${uploadProgress}%`}
              progress={uploadProgress}
            />
          )}
        </div>
      )}

      {uploadState === "error" && uploadError && (
        <div
          role="alert"
          className="mt-4 flex items-start gap-2 rounded-input border border-destructive/30 bg-destructive/5 px-4 py-3 type-small text-destructive"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>{uploadError}</span>
        </div>
      )}

      {uploadState === "uploaded" && profile && (
        <div
          ref={profileRef}
          className="relative mt-4 overflow-hidden rounded-input border border-border bg-background px-4 py-4"
        >
          <span
            data-insight-mark
            aria-hidden
            className="absolute top-0 left-0 h-full w-[3px] bg-sunlight-yellow opacity-0"
          />
          <p data-insight-label className="type-label mb-3 text-label">
            Profiled
          </p>
          <div className="flex flex-col gap-2">
            <ValueRow label="Rows" value={profile.shape.rows.toLocaleString()} />
            <ValueRow label="Columns" value={profile.shape.columns.toLocaleString()} />
          </div>
        </div>
      )}

      {uploadState === "uploaded" && (
        <div className="mt-6 flex flex-col gap-3">
          <Button
            onClick={runAnalysis}
            disabled={analysisState === "running"}
            size="lg"
            className="w-full justify-between px-4"
          >
            {analysisState === "running" ? "Running analysis" : "Run analysis"}
            {analysisState === "running" ? null : <ArrowRight className="size-4" aria-hidden />}
          </Button>

          {analysisState === "running" && (
            <ResolvingIndicator label="Agents working" value="6 stages" />
          )}

          <p aria-live="polite" className="sr-only">
            {analysisState === "running" ? "Analysis in progress." : ""}
          </p>

          {analysisState === "error" && analysisError && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-input border border-destructive/30 bg-destructive/5 px-4 py-3 type-small text-destructive"
            >
              <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
              <span>{analysisError}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
