"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { BarChart3 } from "lucide-react";
import { animateChartDraw } from "@/lib/motion";

// The hero's visual centerpiece: messy raw rows on the left converge through
// a processing hub into clean, quantified metrics on the right.
//
// The connector paths are NOT authored as hand-guessed coordinates against a
// notional frame — that was the previous approach, and it drifted from the
// actual card edges because card padding/gaps are fixed px while an
// SVG-viewBox-based layout scales proportionally, so the two disagreed at
// any rendered width other than the exact reference size. Instead, path
// endpoints are measured from the real DOM (each row's element, each card's
// actual edge) after layout, in the same effect that builds the timeline, so
// they are exact by construction rather than approximated.

const FRAME_W = 640;
const FRAME_H = 270;
const HUB = { x: 320, y: 135 };

// 12 rows, not 8 — taller so the card's natural (content-driven) height
// closes the gap with the upload card on the left, and thematically more
// "raw rows" reads as more mess, not emptier padding.
const RAW_ROWS = [
  { width: 72, dot: null },
  { width: 55, dot: "#3490DC" },
  { width: 80, dot: null },
  { width: 60, dot: "#A8E6CF" },
  { width: 68, dot: null },
  { width: 50, dot: "#FFD369" },
  { width: 76, dot: null },
  { width: 58, dot: "#3490DC" },
  { width: 64, dot: null },
  { width: 48, dot: "#A8E6CF" },
  { width: 70, dot: null },
  { width: 56, dot: "#FFD369" },
];

// `color` renders graphics only (sparkline, connector, dot); WCAG's
// non-text floor for those is 3:1. `textColor` renders the delta figure,
// which needs the 4.5:1 text floor, so it's a darkened variant of the same
// hue rather than the same value.
const METRICS = [
  {
    label: "Sales Revenue",
    prefix: "$",
    target: 8.45,
    decimals: 2,
    suffix: "M",
    delta: "+12.5%",
    color: "#3490DC",
    textColor: "#1C3B61",
    spark: "0,20 10,16 20,17 30,10 40,12 50,6 60,8 70,2",
  },
  {
    label: "Customers",
    prefix: "",
    target: 24.6,
    decimals: 1,
    suffix: "K",
    delta: "+8.1%",
    color: "#2F9E58",
    textColor: "#166534",
    spark: "0,18 10,15 20,15 30,11 40,12 50,7 60,9 70,4",
  },
  {
    label: "Growth Rate",
    prefix: "",
    target: 18.7,
    decimals: 1,
    suffix: "%",
    delta: "+3.4%",
    color: "#C9982E",
    textColor: "#8A6410",
    spark: "0,15 10,17 20,12 30,13 40,9 50,10 60,5 70,6",
  },
  {
    label: "Avg. Order",
    prefix: "$",
    target: 142,
    decimals: 0,
    suffix: "",
    delta: "+5.2%",
    color: "#3490DC",
    textColor: "#1C3B61",
    spark: "0,19 10,14 20,16 30,11 40,13 50,8 60,10 70,3",
  },
];

function pct(value: number, total: number): string {
  return `${(value / total) * 100}%`;
}

/** A point in the SVG's viewBox space, converted from a real DOM rect. */
function toFrame(px: number, py: number, container: DOMRect) {
  return {
    x: ((px - container.left) / container.width) * FRAME_W,
    y: ((py - container.top) / container.height) * FRAME_H,
  };
}

export function HeroFlowDiagram() {
  const ref = useRef<HTMLDivElement>(null);
  const rawCardRef = useRef<HTMLDivElement>(null);
  const cleanCardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = ref.current;
    const rawCard = rawCardRef.current;
    const cleanCard = cleanCardRef.current;
    if (!root || !rawCard || !cleanCard) return;

    const inPaths = Array.from(root.querySelectorAll<SVGPathElement>("[data-in-path]"));
    const outPaths = Array.from(root.querySelectorAll<SVGPathElement>("[data-out-path]"));
    const dots = Array.from(root.querySelectorAll<HTMLElement>("[data-raw-dot]"));
    const hub = root.querySelector<HTMLElement>("[data-hub]");
    const hubGlow = root.querySelector<HTMLElement>("[data-hub-glow]");
    const metricRows = Array.from(root.querySelectorAll<HTMLElement>("[data-metric]"));
    const sparks = Array.from(root.querySelectorAll<SVGPolylineElement>("[data-spark]"));
    const values = Array.from(root.querySelectorAll<HTMLElement>("[data-count]"));

    // Measure the real card edges and real row centers, then build each
    // path so its endpoint sits exactly on the card boundary, aligned with
    // the row it belongs to. No hand-guessed coordinates.
    // `root`/`rawCard`/`cleanCard` are re-read as non-null here (rather than
    // relying on the guard above) because this closure also runs from the
    // resize observer, after the guard's narrowing no longer applies.
    const layoutPaths = () => {
      if (!root || !rawCard || !cleanCard) return false;
      const containerRect = root.getBoundingClientRect();
      if (containerRect.width === 0) return false; // not laid out yet
      const rawEdgeX = rawCard.getBoundingClientRect().right;
      const cleanEdgeX = cleanCard.getBoundingClientRect().left;

      inPaths.forEach((path, i) => {
        const dotRect = dots[i].getBoundingClientRect();
        const centerY = dotRect.top + dotRect.height / 2;
        const start = toFrame(rawEdgeX, centerY, containerRect);
        const midX = start.x + (HUB.x - start.x) * 0.45;
        path.setAttribute(
          "d",
          `M${start.x},${start.y} C${midX},${start.y} ${HUB.x - (HUB.x - midX)},${HUB.y} ${HUB.x},${HUB.y}`
        );
      });

      outPaths.forEach((path, i) => {
        const rowRect = metricRows[i].getBoundingClientRect();
        const centerY = rowRect.top + rowRect.height / 2;
        const end = toFrame(cleanEdgeX, centerY, containerRect);
        const midX = HUB.x + (end.x - HUB.x) * 0.55;
        path.setAttribute(
          "d",
          `M${HUB.x},${HUB.y} C${midX},${HUB.y} ${end.x - (end.x - midX)},${end.y} ${end.x},${end.y}`
        );
      });
      return true;
    };

    gsap.set([...inPaths, ...outPaths], { autoAlpha: 0 });
    gsap.set(dots, { scale: 0 });
    gsap.set(hub, { scale: 0, rotation: -30 });
    gsap.set(metricRows, { autoAlpha: 0, x: 16 });
    gsap.set(sparks, { autoAlpha: 0 });
    gsap.set(values, { textContent: "0" });

    let idle: gsap.core.Tween | null = null;
    let started = false;
    const mm = gsap.matchMedia();

    // The grid this component sits in hasn't necessarily resolved its
    // column tracks by the time this effect first runs, so the container
    // can genuinely report zero width on the first measurement — a
    // ResizeObserver (rather than a one-shot measurement, or a window
    // resize listener that never fires again if nothing resizes) is what
    // guarantees layoutPaths() gets a real, non-zero size before the
    // entrance animation reads any path length.
    const ro = new ResizeObserver(() => {
      const laidOut = layoutPaths();
      if (laidOut && !started) {
        started = true;
        startAnimation();
      }
    });
    ro.observe(root);

    function startAnimation() {
      mm.add(
        { reduce: "(prefers-reduced-motion: reduce)", full: "(prefers-reduced-motion: no-preference)" },
        (context) => {
        const { reduce } = context.conditions as { reduce: boolean };

        if (reduce) {
          gsap.set([...inPaths, ...outPaths, dots, sparks, metricRows], { autoAlpha: 1 });
          gsap.set(dots, { scale: 1 });
          gsap.set(hub, { scale: 1, rotation: 0 });
          gsap.set(metricRows, { x: 0 });
          METRICS.forEach((m, i) => {
            const el = values[i];
            if (el) el.textContent = m.target.toFixed(m.decimals);
          });
          return;
        }

        const tl = gsap.timeline({ delay: 0.15 });

        tl.to(dots, { scale: 1, duration: 0.4, ease: "back.out(2)", stagger: 0.06 });
        inPaths.forEach((p, i) => {
          tl.add(animateChartDraw(p, { duration: 0.5 }), i === 0 ? "-=0.2" : "<0.08");
          tl.set(p, { autoAlpha: 1 }, "<");
        });

        tl.to(hub, { scale: 1, rotation: 0, duration: 0.5, ease: "back.out(1.8)" }, "-=0.2");

        outPaths.forEach((p, i) => {
          tl.add(animateChartDraw(p, { duration: 0.45 }), i === 0 ? "-=0.1" : "<0.08");
          tl.set(p, { autoAlpha: 1 }, "<");
        });

        tl.to(metricRows, { autoAlpha: 1, x: 0, duration: 0.4, ease: "power2.out", stagger: 0.1 }, "-=0.3");
        tl.to(sparks, { autoAlpha: 1, duration: 0.3 }, "<");
        sparks.forEach((s, i) => tl.add(animateChartDraw(s, { duration: 0.6 }), i === 0 ? "<" : "<0.1"));

        values.forEach((el, i) => {
          const m = METRICS[i];
          tl.to(
            el,
            {
              textContent: m.target,
              duration: 0.9,
              ease: "power2.out",
              snap: { textContent: m.decimals === 0 ? 1 : 1 / 10 ** m.decimals },
              onUpdate: function () {
                const v = Number(this.targets()[0].textContent);
                el.textContent = v.toFixed(m.decimals);
              },
            },
            i === 0 ? "-=0.5" : "<0.1"
          );
        });

        tl.call(() => {
          idle = gsap.to(hubGlow, {
            opacity: 0.55,
            scale: 1.12,
            duration: 2.2,
            ease: "sine.inOut",
            yoyo: true,
            repeat: -1,
          });
        });

          return () => {
            tl.kill();
            idle?.kill();
          };
        }
      );
    }

    return () => {
      ro.disconnect();
      idle?.kill();
      mm.revert();
    };
  }, []);

  return (
    <div
      ref={ref}
      className="relative w-full"
      style={{ aspectRatio: `${FRAME_W} / ${FRAME_H}` }}
    >
      {/* Raw data card */}
      <div
        ref={rawCardRef}
        className="absolute -top-2 left-0 w-[38%] rounded-card border border-border bg-card p-5 shadow-soft"
      >
        <div className="flex items-center justify-between">
          <span className="type-small font-semibold text-foreground">Raw data</span>
          <span className="rounded-full bg-cloud-grey px-2 py-0.5 type-label text-[10px] text-label">
            Messy
          </span>
        </div>
        <div className="mt-5 flex flex-col gap-3">
          {RAW_ROWS.map((row, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <span
                className="h-[7px] rounded-mark bg-cloud-grey"
                style={{ width: `${row.width}%` }}
              />
              <span
                data-raw-dot
                className="size-1.5 shrink-0 rounded-full"
                style={{ backgroundColor: row.dot ?? "#E2E8F0" }}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Clean insights card */}
      <div
        ref={cleanCardRef}
        className="absolute top-[1%] right-0 w-[38%] rounded-card border border-border bg-card p-5 shadow-soft"
      >
        <div className="flex items-center justify-between">
          <span className="type-small font-semibold text-foreground">Clean insights</span>
          <span className="rounded-full bg-[#2F9E58]/10 px-2 py-0.5 type-label text-[10px] text-[#166534]">
            Clear
          </span>
        </div>
        <div className="mt-5 flex flex-col gap-5">
          {METRICS.map((m) => (
            <div key={m.label} data-metric className="flex items-center justify-between gap-2">
              <div>
                <p className="type-label text-[9px] text-label">{m.label}</p>
                <div className="mt-0.5 flex items-baseline gap-1.5">
                  <span className="type-value text-[15px] text-foreground">
                    {m.prefix}
                    <span data-count>0</span>
                    {m.suffix}
                  </span>
                  <span className="type-label text-[9px]" style={{ color: m.textColor }}>
                    {m.delta}
                  </span>
                </div>
              </div>
              <svg viewBox="0 0 70 24" className="h-4 w-12 shrink-0">
                <polyline
                  data-spark
                  points={m.spark}
                  fill="none"
                  stroke={m.color}
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
          ))}
        </div>
      </div>

      {/* Connectors + hub, absolutely positioned over both cards. Paths
          start with an empty `d` — real coordinates are set in the effect
          above, once actual card/row positions are known. */}
      <svg
        viewBox={`0 0 ${FRAME_W} ${FRAME_H}`}
        className="pointer-events-none absolute inset-0 h-full w-full"
        aria-hidden
      >
        {RAW_ROWS.map((row, i) => (
          <path
            key={`in-${i}`}
            data-in-path
            fill="none"
            stroke={row.dot ?? "#E2E8F0"}
            strokeWidth={1}
            opacity={0.7}
          />
        ))}
        {METRICS.map((m, i) => (
          <path
            key={`out-${i}`}
            data-out-path
            fill="none"
            stroke={m.color}
            strokeWidth={1}
            opacity={0.7}
          />
        ))}
      </svg>

      {/* Hub, an HTML element so it can host a real box-shadow glow. Small —
          a connecting accent between the two cards, not a focal element. */}
      <div
        className="absolute z-10 -translate-x-1/2 -translate-y-1/2"
        style={{ left: pct(HUB.x, FRAME_W), top: pct(HUB.y, FRAME_H) }}
      >
        <span
          data-hub-glow
          aria-hidden
          className="absolute inset-0 -z-10 rounded-full bg-coastal-blue opacity-30 blur-md"
        />
        <div
          data-hub
          className="flex size-8 items-center justify-center rounded-lg bg-coastal-blue text-white shadow-soft"
        >
          <BarChart3 className="size-3.5" aria-hidden />
        </div>
      </div>
    </div>
  );
}
