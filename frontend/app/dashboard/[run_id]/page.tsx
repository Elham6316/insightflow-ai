"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  BarChart3,
  DollarSign,
  Info,
  ListOrdered,
  Package,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EChart } from "@/components/echart";
import { cn } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Severity = "info" | "warning" | "critical";

type Insight = {
  id: string;
  title: string;
  description: string;
  severity: Severity;
  chart_ref: string | null;
  created_at: string;
};

type Visualization = {
  chart_type: "line" | "bar" | "pie" | "heatmap";
  title: string;
  echarts_option: Record<string, unknown>;
  related_metric: string;
  note?: string | null;
};

type Kpi = {
  label: string;
  value: number | string;
  unit: string;
  format: "currency" | "number" | "percent";
};

type QualityReport = {
  overall_score?: number;
  summary?: string;
  duplicates?: number;
  missing_by_column?: Record<string, number>;
};

type AnalysisRunResponse = {
  run_id: string;
  dataset_id: string;
  dataset_filename: string | null;
  status: string;
  current_agent: string | null;
  started_at: string | null;
  finished_at: string | null;
  data_domain: string | null;
  quality_report: QualityReport;
  kpis: Kpi[];
  visualizations: Visualization[];
  insights: Insight[];
  note?: string;
};

type LoadState = "loading" | "loaded" | "error";

const SEVERITY_STYLES: Record<
  Severity,
  { border: string; badge: string; icon: React.ReactNode }
> = {
  info: {
    border: "border-l-blue-500",
    badge: "border-transparent bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
    icon: <Info className="size-3" />,
  },
  warning: {
    border: "border-l-yellow-500",
    badge:
      "border-transparent bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300",
    icon: <TriangleAlert className="size-3" />,
  },
  critical: {
    border: "border-l-red-500",
    badge: "border-transparent bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
    icon: <ShieldAlert className="size-3" />,
  },
};

function scoreColor(score: number | undefined) {
  if (score === undefined) return { text: "text-muted-foreground", bar: "bg-muted-foreground" };
  if (score >= 80) return { text: "text-green-600 dark:text-green-400", bar: "bg-green-500" };
  if (score >= 60) return { text: "text-yellow-600 dark:text-yellow-400", bar: "bg-yellow-500" };
  return { text: "text-red-600 dark:text-red-400", bar: "bg-red-500" };
}

function formatTimestamp(value: string | null) {
  if (!value) return null;
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function formatKpiValue(kpi: Kpi): string {
  if (typeof kpi.value === "string") return kpi.value;
  if (kpi.format === "currency") {
    return `${kpi.unit}${kpi.value.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }
  if (kpi.format === "percent") {
    return `${kpi.value}${kpi.unit}`;
  }
  return `${kpi.value.toLocaleString()}${kpi.unit}`;
}

// KPI labels are dynamic (domain-dependent, e.g. "Total Revenue" vs "Total
// Complaints" vs "Most Complete Column"), so icons are picked by matching
// keywords in the label rather than hardcoding per domain — this keeps it
// working for sales/finance/complaints/generic KPI sets without special-
// casing each one.
const KPI_ICON_RULES: { keywords: RegExp; icon: LucideIcon; colorClasses: string }[] = [
  {
    keywords: /quality|score/,
    icon: ShieldCheck,
    colorClasses: "bg-teal-100 text-teal-600 dark:bg-teal-950 dark:text-teal-400",
  },
  {
    // Checked before the revenue rule below: labels like "Average Order
    // Value" contain both "average" and "value", and should read as an
    // average-type KPI (TrendingUp), not a raw currency total (DollarSign).
    keywords: /average|avg|mean/,
    icon: TrendingUp,
    colorClasses: "bg-orange-100 text-orange-600 dark:bg-orange-950 dark:text-orange-400",
  },
  {
    keywords: /revenue|amount|price|value/,
    icon: DollarSign,
    colorClasses: "bg-emerald-100 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400",
  },
  {
    keywords: /order/,
    icon: Package,
    colorClasses: "bg-purple-100 text-purple-600 dark:bg-purple-950 dark:text-purple-400",
  },
  {
    keywords: /complaint|row|transaction|count|column/,
    icon: ListOrdered,
    colorClasses: "bg-purple-100 text-purple-600 dark:bg-purple-950 dark:text-purple-400",
  },
];
const KPI_ICON_FALLBACK = {
  icon: BarChart3,
  colorClasses: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

function getKpiIcon(label: string) {
  const normalized = label.toLowerCase();
  const match = KPI_ICON_RULES.find((rule) => rule.keywords.test(normalized));
  return match ?? KPI_ICON_FALLBACK;
}

function DashboardSkeleton() {
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-10">
      <div className="flex flex-col gap-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-40" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {[0, 1].map((i) => (
          <Skeleton key={i} className="h-80 w-full" />
        ))}
      </div>
      <Skeleton className="h-40 w-full" />
    </div>
  );
}

export default function DashboardPage({ params }: { params: { run_id: string } }) {
  const { run_id } = params;

  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalysisRunResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setState("loading");
      setError(null);
      try {
        const res = await fetch(`${API_URL}/analysis/${run_id}`);
        if (!res.ok) {
          if (res.status === 404) {
            throw new Error("This analysis run could not be found.");
          }
          let message = `Failed to load analysis (HTTP ${res.status}).`;
          try {
            const body = await res.json();
            if (body?.detail) message = body.detail;
          } catch {
            // ignore, use default message
          }
          throw new Error(message);
        }
        const body: AnalysisRunResponse = await res.json();
        if (!cancelled) {
          setData(body);
          setState("loaded");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load analysis.");
          setState("error");
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [run_id]);

  if (state === "loading") {
    return <DashboardSkeleton />;
  }

  if (state === "error" || !data) {
    return (
      <div className="mx-auto flex max-w-xl flex-col items-center gap-4 px-4 py-24 text-center">
        <AlertTriangle className="size-10 text-destructive" />
        <h1 className="text-xl font-semibold">Couldn&apos;t load this analysis</h1>
        <p className="text-muted-foreground">{error}</p>
        <Link href="/" className="text-sm font-medium text-primary underline-offset-4 hover:underline">
          Back to upload
        </Link>
      </div>
    );
  }

  const { text: scoreText, bar: scoreBar } = scoreColor(data.quality_report?.overall_score);
  const timestamp = formatTimestamp(data.finished_at || data.started_at);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-10">
      {/* Header */}
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold">
            {data.dataset_filename || "Untitled dataset"}
          </h1>
          {data.data_domain && (
            <Badge variant="secondary" className="capitalize">
              {data.data_domain}
            </Badge>
          )}
        </div>
        {timestamp && <p className="text-sm text-muted-foreground">Analyzed {timestamp}</p>}
      </div>

      {/* done_with_errors banner */}
      {data.status === "done_with_errors" && data.note && (
        <div className="flex items-start gap-2 rounded-lg border border-yellow-300 bg-yellow-50 px-4 py-3 text-sm text-yellow-900 dark:border-yellow-900 dark:bg-yellow-950 dark:text-yellow-200">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          <span>{data.note}</span>
        </div>
      )}

      {/* KPIs */}
      {data.kpis?.length > 0 && (
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {data.kpis.map((kpi, i) => {
            const { icon: KpiIcon, colorClasses } = getKpiIcon(kpi.label);
            return (
              <Card key={i}>
                <CardContent className="flex items-start justify-between gap-2 pt-4">
                  <div>
                    <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                      {kpi.label}
                    </p>
                    <p className="mt-1 text-2xl font-bold">{formatKpiValue(kpi)}</p>
                  </div>
                  <span
                    className={cn(
                      "flex size-9 shrink-0 items-center justify-center rounded-full",
                      colorClasses
                    )}
                  >
                    <KpiIcon className="size-5" />
                  </span>
                </CardContent>
              </Card>
            );
          })}
        </section>
      )}

      {/* Insights */}
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Insights</h2>
        {data.insights.length === 0 ? (
          <p className="text-sm text-muted-foreground">No insights were generated for this run.</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {data.insights.map((insight) => {
              const style = SEVERITY_STYLES[insight.severity] ?? SEVERITY_STYLES.info;
              return (
                <Card key={insight.id} size="sm" className={cn("gap-2 border-l-4", style.border)}>
                  <CardHeader className="flex-row items-start justify-between gap-2 space-y-0">
                    <CardTitle className="text-xs leading-snug font-semibold">
                      {insight.title}
                    </CardTitle>
                    <Badge className={cn(style.badge, "shrink-0")}>
                      <span className="flex items-center gap-1">
                        {style.icon}
                        {insight.severity}
                      </span>
                    </Badge>
                  </CardHeader>
                  <CardContent>
                    <p className="line-clamp-2 text-xs text-muted-foreground">
                      {insight.description}
                    </p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </section>

      {/* Charts */}
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Charts</h2>
        {data.visualizations.length === 0 ? (
          <p className="text-sm text-muted-foreground">No charts were generated for this run.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {data.visualizations.map((viz, i) => (
              <Card key={`${viz.chart_type}-${i}`}>
                <CardHeader>
                  <CardTitle className="text-sm">{viz.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <EChart option={viz.echarts_option} />
                  {viz.note && (
                    <p className="mt-2 text-xs text-muted-foreground italic">{viz.note}</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      {/* Data Quality */}
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Data Quality</h2>
        <Card>
          <CardContent className="flex flex-col gap-4 pt-4 sm:flex-row sm:items-center">
            <div className="flex flex-col items-center gap-1 sm:w-40">
              <span className={cn("text-5xl font-bold", scoreText)}>
                {data.quality_report?.overall_score ?? "—"}
              </span>
              <span className="text-xs text-muted-foreground">/ 100</span>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className={cn("h-full rounded-full", scoreBar)}
                  style={{
                    width: `${Math.min(100, Math.max(0, data.quality_report?.overall_score ?? 0))}%`,
                  }}
                />
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              {data.quality_report?.summary || "No data quality summary available for this run."}
            </p>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
