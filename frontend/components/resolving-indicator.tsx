"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";

// There are no spinners in this product (DESIGN_LANGUAGE.md §8, §17).
// Loading is content resolving: eight units settle from Raw to Resolved,
// left to right, on a loop. Label left, figure right (§11).
//
// Determinate mode (progress supplied) fills units to match real progress.
// Indeterminate mode cycles, because the duration is genuinely unknown.

const UNITS = 8;

export function ResolvingIndicator({
  label,
  value,
  progress,
}: {
  label: string;
  value?: string;
  progress?: number;
}) {
  const trackRef = useRef<HTMLDivElement>(null);
  const isDeterminate = typeof progress === "number";

  useEffect(() => {
    const track = trackRef.current;
    if (!track) return;

    const units = Array.from(track.querySelectorAll<HTMLElement>("[data-unit]"));
    const mm = gsap.matchMedia();

    mm.add(
      {
        reduce: "(prefers-reduced-motion: reduce)",
        full: "(prefers-reduced-motion: no-preference)",
      },
      (context) => {
        const { reduce } = context.conditions as { reduce: boolean };

        if (isDeterminate) {
          const filled = Math.round(((progress ?? 0) / 100) * UNITS);
          units.forEach((unit, i) => {
            gsap.to(unit, {
              backgroundColor: i < filled ? "#3490DC" : "#E2E8F0",
              duration: reduce ? 0 : 0.2,
              ease: "power2.out",
            });
          });
          return;
        }

        if (reduce) {
          gsap.set(units, { backgroundColor: "#3490DC", opacity: 0.6 });
          return;
        }

        const tl = gsap.timeline({ repeat: -1 });
        tl.to(units, {
          backgroundColor: "#3490DC",
          duration: 0.28,
          ease: "power2.out",
          stagger: 0.08,
        }).to(units, {
          backgroundColor: "#E2E8F0",
          duration: 0.28,
          ease: "power2.out",
          stagger: 0.08,
        });

        return () => {
          tl.kill();
        };
      }
    );

    return () => mm.revert();
  }, [progress, isDeterminate]);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-4">
        <span className="type-label">{label}</span>
        {value && <span className="type-value text-[14px]">{value}</span>}
      </div>
      <div
        ref={trackRef}
        role="progressbar"
        aria-label={label}
        aria-valuenow={isDeterminate ? progress : undefined}
        aria-valuemin={isDeterminate ? 0 : undefined}
        aria-valuemax={isDeterminate ? 100 : undefined}
        className="flex gap-1"
      >
        {Array.from({ length: UNITS }).map((_, i) => (
          <span key={i} data-unit className="h-1 flex-1 rounded-mark bg-cloud-grey" />
        ))}
      </div>
    </div>
  );
}
