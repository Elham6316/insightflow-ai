"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

// InsightFlow AI brand colors, used as the default series color cycle for
// every chart (line/bar/pie draw from this in order; the heatmap ignores it
// and uses its own visualMap.inRange gradient instead, set in
// backend/app/agents/visualization.py).
const BRAND_CHART_COLORS = ["#3490DC", "#A8E6CF", "#FFD369", "#1C3B61"];

export function EChart({
  option,
  style,
}: {
  option: Record<string, unknown>;
  style?: React.CSSProperties;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;

    const chart = echarts.init(ref.current);
    // animation: false — ECharts' default entrance animations (bar grow-in,
    // pie fade-in) drive their first paint off requestAnimationFrame, which
    // browsers throttle or skip entirely for a backgrounded/unfocused tab,
    // leaving series shapes permanently unpainted while static text (axis
    // labels, titles) still renders. Disabling animation paints everything
    // synchronously on the first frame instead.
    chart.setOption({ color: BRAND_CHART_COLORS, animation: false, ...option });

    const handleResize = () => chart.resize();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.dispose();
    };
  }, [option]);

  return <div ref={ref} style={{ width: "100%", height: 260, ...style }} />;
}
