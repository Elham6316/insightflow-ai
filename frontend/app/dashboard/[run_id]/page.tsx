"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import gsap from "gsap";
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
import { animateCardIn, animateCountUp, animateHoverReveal, animateInsightMoment } from "@/lib/motion";
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

type CleaningAction = {
  column: string | null;
  action: string;
  detail: string;
  affected: number;
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
  cleaning_actions: CleaningAction[];
  kpis: Kpi[];
  visualizations: Visualization[];
  insights: Insight[];
  note?: string;
};

type LoadState = "loading" | "loaded" | "error";

// Severity stays functionally conventional (info=blue, warning=yellow,
// critical=red) — users expect that regardless of brand. "info" lands on
// coastal-blue specifically, so it reads as conventional and on-brand at
// once. Badge text uses the same mono/uppercase treatment as every other
// label on the site (type-label), not a one-off font.
const SEVERITY_STYLES: Record<Severity, { border: string; badge: string; icon: React.ReactNode }> = {
  info: {
    border: "border-l-coastal-blue",
    badge: "border-transparent bg-coastal-blue/10 text-primary",
    icon: <Info className="size-3" />,
  },
  warning: {
    border: "border-l-yellow-500",
    badge: "border-transparent bg-yellow-500/10 text-yellow-700",
    icon: <TriangleAlert className="size-3" />,
  },
  critical: {
    border: "border-l-red-500",
    badge: "border-transparent bg-red-500/10 text-red-700",
    icon: <ShieldAlert className="size-3" />,
  },
};

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

function kpiDecimals(kpi: Kpi): number {
  if (kpi.format === "currency") return 2;
  if (kpi.format === "percent") return Number.isInteger(kpi.value) ? 0 : 1;
  return 0;
}

// KPI labels are dynamic (domain-dependent: "Total Revenue" vs "Total
// Complaints" vs "Most Complete Column"), so icons are picked by matching
// keywords rather than hardcoding per domain. Every rule uses a low-alpha
// tint behind a small icon — the same restrained chip treatment as the
// homepage's agent icons — instead of a solid-color avatar circle, which
// is the generic-dashboard-template look this page is explicitly not.
const KPI_ICON_RULES: { keywords: RegExp; icon: LucideIcon; colorClasses: string }[] = [
  {
    keywords: /quality|score/,
    icon: ShieldCheck,
    colorClasses: "bg-meadow-green/20 text-[#166534]",
  },
  {
    // Checked before the revenue rule below: "Average Order Value" contains
    // both "average" and "value", and should read as an average (TrendingUp)
    // rather than a raw currency total (DollarSign).
    keywords: /average|avg|mean/,
    icon: TrendingUp,
    colorClasses: "bg-sunlight-yellow/20 text-[#8A6410]",
  },
  {
    keywords: /revenue|amount|price|value/,
    icon: DollarSign,
    colorClasses: "bg-coastal-blue/10 text-primary",
  },
  {
    keywords: /order/,
    icon: Package,
    colorClasses: "bg-ocean-navy/10 text-foreground",
  },
  {
    keywords: /complaint|row|transaction|count|column/,
    icon: ListOrdered,
    colorClasses: "bg-cloud-grey text-foreground",
  },
];
const KPI_ICON_FALLBACK = { icon: BarChart3, colorClasses: "bg-cloud-grey text-foreground" };

function getKpiIcon(label: string) {
  const normalized = label.toLowerCase();
  return KPI_ICON_RULES.find((rule) => rule.keywords.test(normalized)) ?? KPI_ICON_FALLBACK;
}

const SEVERITY_RANK: Record<Severity, number> = { critical: 3, warning: 2, info: 1 };

function DashboardSkeleton() {
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-16 px-4 py-14 md:px-8">
      <div className="flex flex-col gap-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-40" />
      </div>
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-72 w-full" />
        ))}
      </div>
    </div>
  );
}

/** Card/panel-level hover feedback (Connect), wired via the shared helper. */
function useHoverReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  useEffect(() => {
    if (!ref.current) return;
    return animateHoverReveal(ref.current);
  }, []);
  return ref;
}

function KpiCard({ kpi, primary }: { kpi: Kpi; primary: boolean }) {
  const cardRef = useHoverReveal<HTMLDivElement>();
  const valueRef = useRef<HTMLSpanElement>(null);
  const { icon: KpiIcon, colorClasses } = getKpiIcon(kpi.label);
  const numeric = typeof kpi.value === "number";

  useEffect(() => {
    if (!numeric || !valueRef.current) return;
    animateCountUp(valueRef.current, kpi.value as number, { decimals: kpiDecimals(kpi) });
  }, [numeric, kpi]);

  const prefix = kpi.format === "currency" ? kpi.unit : "";
  const suffix = kpi.format !== "currency" ? kpi.unit : "";

  return (
    <Card
      ref={cardRef}
      className={cn("stagger-card relative overflow-hidden", primary && "border-foreground/20")}
    >
      {/* The Insight Moment's Mark — drawn only on the primary KPI. */}
      {primary && (
        <span
          data-insight-mark
          aria-hidden
          className="absolute top-0 left-0 h-full w-[3px] bg-sunlight-yellow opacity-0"
        />
      )}
      <CardContent className="flex items-start justify-between gap-3 pt-4">
        <div>
          <p data-insight-label className="type-label text-label">
            {kpi.label}
          </p>
          <p className="type-value mt-1.5 text-2xl text-foreground">
            {numeric ? (
              <>
                {prefix}
                <span ref={valueRef}>0</span>
                {suffix}
              </>
            ) : (
              formatKpiValue(kpi)
            )}
          </p>
        </div>
        <span className={cn("flex size-8 shrink-0 items-center justify-center rounded-mark", colorClasses)}>
          <KpiIcon className="size-4" />
        </span>
      </CardContent>
    </Card>
  );
}

function InsightCard({ insight }: { insight: Insight }) {
  const cardRef = useHoverReveal<HTMLDivElement>();
  const style = SEVERITY_STYLES[insight.severity] ?? SEVERITY_STYLES.info;
  return (
    <Card ref={cardRef} size="sm" className={cn("stagger-card gap-2 border-l-[3px]", style.border)}>
      <CardHeader className="flex-row items-start justify-between gap-2 space-y-0">
        <CardTitle className="text-xs leading-snug font-semibold">{insight.title}</CardTitle>
        <Badge className={cn(style.badge, "type-label shrink-0")}>
          <span className="flex items-center gap-1">
            {style.icon}
            {insight.severity}
          </span>
        </Badge>
      </CardHeader>
      <CardContent>
        <p className="line-clamp-2 type-small text-label">{insight.description}</p>
      </CardContent>
    </Card>
  );
}

function ChartCard({ viz }: { viz: Visualization }) {
  const cardRef = useHoverReveal<HTMLDivElement>();
  return (
    <Card ref={cardRef} className="stagger-card h-full">
      <CardHeader>
        <CardTitle className="type-small font-semibold text-foreground">{viz.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <EChart option={viz.echarts_option} />
        {viz.note && <p className="mt-2 type-small text-label italic">{viz.note}</p>}
      </CardContent>
    </Card>
  );
}

// One compact card, one line per action — column name (if any) plus the
// backend's own human-readable detail string, so the phrasing only lives
// in one place (backend/app/agents/cleaning.py) rather than being
// re-derived here from the raw action/affected fields.
function CleaningSection({ actions }: { actions: CleaningAction[] }) {
  const cardRef = useHoverReveal<HTMLDivElement>();
  return (
    <section className="flex flex-col gap-5">
      <h2 className="type-label text-label">Data Cleaning</h2>
      <Card ref={cardRef} className="stagger-card">
        <CardContent className="flex flex-col gap-2.5 pt-4">
          {actions.map((a, i) => (
            <div key={i} className="flex items-baseline gap-2">
              <span className="mt-1.5 size-1 shrink-0 rounded-full bg-cloud-grey" aria-hidden />
              <p className="type-small text-foreground">
                {a.column && <span className="font-medium">{a.column}: </span>}
                <span className="text-label">{a.detail}</span>
              </p>
            </div>
          ))}
        </CardContent>
      </Card>
    </section>
  );
}

// Denser chart types get more room (2 of 3 desktop columns) instead of
// competing for the same 1/3 width as a simple bar/pie/line. Only heatmaps
// exist today, but this is a type check, not a hardcoded list, so any
// future chart type can opt in by widening this predicate.
function isWideChart(viz: Visualization): boolean {
  return viz.chart_type === "heatmap";
}

type ChartItem = { viz: Visualization; wide: boolean };
type ChartRow = ChartItem[];

const ROW_CAPACITY = 3;

/**
 * Groups charts into rows for a 3-column desktop grid, avoiding a lone
 * chart stranded alone in the final row.
 *
 * Wide charts cost 2 units of the 3-unit row capacity, normal charts cost
 * 1. Charts are packed in their original order (greedy first-fit), so the
 * dashboard's chart order is preserved. The only special case is the very
 * end: if that leaves a trailing row containing exactly one normal chart,
 * one chart is borrowed back from the previous (full) row so the last two
 * rows become an even 2-2 split instead of 3-1. This is the same fix for
 * every remainder case — n%3==0 never triggers it, n%3==1 turns a trailing
 * "3, 1" into "2, 2", and n%3==2 already ends in a natural 2 with nothing
 * to fix.
 */
function groupChartsIntoRows(visualizations: Visualization[]): ChartRow[] {
  const items: ChartItem[] = visualizations.map((viz) => ({ viz, wide: isWideChart(viz) }));
  const rows: ChartRow[] = [];
  let current: ChartRow = [];
  let currentUnits = 0;

  for (const item of items) {
    const cost = item.wide ? 2 : 1;
    if (currentUnits + cost > ROW_CAPACITY && current.length > 0) {
      rows.push(current);
      current = [];
      currentUnits = 0;
    }
    current.push(item);
    currentUnits += cost;
  }
  if (current.length > 0) rows.push(current);

  if (rows.length >= 2) {
    const last = rows[rows.length - 1];
    const isLoneNormalOrphan = last.length === 1 && !last[0].wide;
    if (isLoneNormalOrphan) {
      const prev = rows[rows.length - 2];
      const prevAllNormal = prev.every((item) => !item.wide);
      if (prevAllNormal && prev.length >= 2) {
        const borrowed = prev.pop()!;
        last.unshift(borrowed);
      }
    }
  }

  return rows;
}

function rowUnits(row: ChartRow): number {
  return row.reduce((sum, item) => sum + (item.wide ? 2 : 1), 0);
}

// One row = one flex container, sized so its items line up exactly with a
// native 3-column desktop grid (same 1.5rem/gap-6 gap). A row that doesn't
// fill all 3 units centers itself instead of left-aligning with a visible
// gap on the right. Below desktop, wide charts simply take the full row
// and normal charts pair up two-per-row — the exact orphan-avoidance math
// is a 3-column-desktop-specific concern, per the task.
function ChartRowView({ row }: { row: ChartRow }) {
  const full = rowUnits(row) >= ROW_CAPACITY;
  return (
    <div
      className={cn(
        "flex flex-col gap-6 md:flex-row md:flex-wrap lg:flex-nowrap",
        !full && "lg:justify-center"
      )}
    >
      {row.map((item, i) => (
        <div
          key={i}
          className={cn(
            "min-w-0",
            item.wide
              ? "w-full md:w-full lg:w-[calc((100%-3rem)/3*2+1.5rem)]"
              : "w-full md:w-[calc((100%-1.5rem)/2)] lg:w-[calc((100%-3rem)/3)]"
          )}
        >
          <ChartCard viz={item.viz} />
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage({ params }: { params: { run_id: string } }) {
  const { run_id } = params;

  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalysisRunResponse | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

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

  // One orchestrated entrance (Reveal), same restrained one-shot as the
  // homepage — runs once per loaded run, no scroll triggers, no loops.
  // Once settled, the primary KPI gets the Insight Moment: the rest recede
  // briefly, it sharpens, and it keeps the Mark — the same mechanic used on
  // the homepage's "Profiled" panel, reused rather than reinvented.
  useEffect(() => {
    if (state !== "loaded" || !rootRef.current) return;
    const root = rootRef.current;
    const cards = Array.from(root.querySelectorAll<HTMLElement>(".stagger-card"));
    if (!cards.length) return;

    const mm = gsap.matchMedia();
    mm.add(
      { reduce: "(prefers-reduced-motion: reduce)", full: "(prefers-reduced-motion: no-preference)" },
      (context) => {
        const { reduce } = context.conditions as { reduce: boolean };
        if (reduce) return;

        const tween = animateCardIn(cards, { stagger: 0.06 });
        const primaryKpi = root.querySelector<HTMLElement>('[data-insight-mark]')?.closest(".stagger-card");
        if (primaryKpi instanceof HTMLElement) {
          const kpiCards = root.querySelectorAll<HTMLElement>("[data-kpi-section] .stagger-card");
          tween?.eventCallback("onComplete", () => {
            animateInsightMoment(primaryKpi, { siblings: Array.from(kpiCards) });
          });
        }
      }
    );

    return () => mm.revert();
  }, [state, data]);

  if (state === "loading") {
    return <DashboardSkeleton />;
  }

  if (state === "error" || !data) {
    return (
      <div className="mx-auto flex max-w-xl flex-col items-center gap-4 px-4 py-24 text-center">
        <AlertTriangle className="size-10 text-destructive" />
        <h1 className="type-h3">Couldn&apos;t load this analysis</h1>
        <p className="type-small text-label">{error}</p>
        <Link href="/" className="type-small font-medium text-primary underline-offset-4 hover:underline">
          Back to upload
        </Link>
      </div>
    );
  }

  const timestamp = formatTimestamp(data.finished_at || data.started_at);
  const sortedInsights = [...data.insights].sort(
    (a, b) => (SEVERITY_RANK[b.severity] ?? 0) - (SEVERITY_RANK[a.severity] ?? 0)
  );
  const chartRows = groupChartsIntoRows(data.visualizations);

  return (
    <div ref={rootRef} className="mx-auto flex max-w-6xl flex-col gap-16 px-4 py-14 md:px-8">
      {/* Header */}
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="type-h2 text-foreground">{data.dataset_filename || "Untitled dataset"}</h1>
          {data.data_domain && (
            <Badge className="type-label border-transparent bg-coastal-blue/10 capitalize text-primary">
              {data.data_domain}
            </Badge>
          )}
        </div>
        {timestamp && <p className="type-small text-label">Analyzed {timestamp}</p>}
      </div>

      {/* done_with_errors banner */}
      {data.status === "done_with_errors" && data.note && (
        <div className="-mt-10 flex items-start gap-2 rounded-input border border-yellow-500/30 bg-yellow-500/5 px-4 py-3 type-small text-yellow-800">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          <span>{data.note}</span>
        </div>
      )}

      {/* KPIs */}
      {data.kpis?.length > 0 && (
        <section data-kpi-section className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {data.kpis.map((kpi, i) => (
            <KpiCard key={i} kpi={kpi} primary={i === 0} />
          ))}
        </section>
      )}

      {/* Insights */}
      <section className="flex flex-col gap-5">
        <h2 className="type-label text-label">Insights</h2>
        {sortedInsights.length === 0 ? (
          <p className="type-small text-label">No insights were generated for this run.</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {sortedInsights.map((insight) => (
              <InsightCard key={insight.id} insight={insight} />
            ))}
          </div>
        )}
      </section>

      {/* Data Cleaning — only when CleaningAgent actually did something */}
      {data.cleaning_actions?.length > 0 && <CleaningSection actions={data.cleaning_actions} />}

      {/* Charts */}
      <section className="flex flex-col gap-5">
        <h2 className="type-label text-label">Charts</h2>
        {data.visualizations.length === 0 ? (
          <p className="type-small text-label">No charts were generated for this run.</p>
        ) : (
          <div className="flex flex-col gap-6">
            {chartRows.map((row, i) => (
              <ChartRowView key={i} row={row} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
