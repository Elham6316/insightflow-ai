"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  CheckCircle2,
  FileSpreadsheet,
  Loader2,
  UploadCloud,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ALLOWED_EXTENSIONS = [".csv", ".xlsx", ".xls"];

type Profile = {
  shape: { rows: number; columns: number };
  columns: Record<string, string>;
  sample: Record<string, unknown>[];
  null_counts: Record<string, number>;
};

type UploadResponse = {
  dataset_id: string;
  profile: Profile;
};

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
          // ignore, use default message
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

export default function Home() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);

  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);

  const [analysisState, setAnalysisState] = useState<AnalysisState>("idle");
  const [analysisError, setAnalysisError] = useState<string | null>(null);

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
        `Unsupported file type "${ext || "unknown"}". Allowed types: ${ALLOWED_EXTENSIONS.join(", ")}.`
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
      const res = await fetch(`${API_URL}/analysis/${datasetId}/run`, {
        method: "POST",
      });

      if (!res.ok) {
        let message = `Analysis failed (HTTP ${res.status}).`;
        try {
          const body = await res.json();
          if (body?.detail) message = body.detail;
        } catch {
          // ignore, use default message
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
    <main className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center gap-8 px-4 py-12">
      <div className="flex flex-col items-center gap-2 text-center">
        <h1 className="text-4xl font-bold">InsightFlow AI</h1>
        <p className="max-w-md text-muted-foreground">
          Upload a dataset and let AI agents profile it, check its quality, and
          surface insights.
        </p>
      </div>

      <Card className="w-full max-w-xl">
        <CardHeader>
          <CardTitle>Upload a dataset</CardTitle>
          <CardDescription>Accepted formats: .csv, .xlsx, .xls</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {uploadState === "idle" && (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
              }}
              className={cn(
                "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-border px-6 py-12 text-center transition-colors",
                isDragging ? "border-primary bg-muted" : "hover:bg-muted/50"
              )}
            >
              <UploadCloud className="size-8 text-muted-foreground" />
              <div>
                <p className="font-medium">Drag & drop a file here</p>
                <p className="text-sm text-muted-foreground">or click to browse</p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept={ALLOWED_EXTENSIONS.join(",")}
                onChange={handleFileInputChange}
                className="hidden"
              />
            </div>
          )}

          {file && uploadState !== "idle" && (
            <div className="flex items-center gap-3 rounded-lg border border-border px-4 py-3">
              <FileSpreadsheet className="size-5 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{file.name}</p>
                {uploadState === "uploading" && (
                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary transition-all"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                )}
              </div>
              {uploadState === "uploading" && (
                <Loader2 className="size-4 shrink-0 animate-spin text-muted-foreground" />
              )}
              {uploadState === "uploaded" && (
                <CheckCircle2 className="size-5 shrink-0 text-primary" />
              )}
              {uploadState !== "uploading" && (
                <Button variant="ghost" size="icon-sm" onClick={reset} aria-label="Remove file">
                  <X className="size-4" />
                </Button>
              )}
            </div>
          )}

          {uploadState === "error" && uploadError && (
            <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              <span>{uploadError}</span>
            </div>
          )}

          {uploadState === "uploaded" && profile && (
            <div className="rounded-lg border border-border px-4 py-3 text-sm">
              <p className="font-medium">File profiled successfully</p>
              <p className="text-muted-foreground">
                {profile.shape.rows.toLocaleString()} rows &middot;{" "}
                {profile.shape.columns.toLocaleString()} columns
              </p>
            </div>
          )}

          {uploadState === "uploaded" && (
            <>
              <Button onClick={runAnalysis} disabled={analysisState === "running"}>
                {analysisState === "running" ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Running analysis&hellip; this can take 10-20 seconds
                  </>
                ) : (
                  "Run Analysis"
                )}
              </Button>

              {analysisState === "error" && analysisError && (
                <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                  <AlertCircle className="mt-0.5 size-4 shrink-0" />
                  <span>{analysisError}</span>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
