"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";

// Reveal (DESIGN_LANGUAGE.md §9): content arrives with a fade and an 8px
// lift, once, when it first enters the viewport. IntersectionObserver rather
// than a scroll listener, and it disconnects after firing so nothing is
// observed for the life of the page.

export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const mm = gsap.matchMedia();

    mm.add(
      {
        reduce: "(prefers-reduced-motion: reduce)",
        full: "(prefers-reduced-motion: no-preference)",
      },
      (context) => {
        const { reduce } = context.conditions as { reduce: boolean };

        if (reduce) {
          gsap.set(el, { autoAlpha: 1, y: 0 });
          return;
        }

        gsap.set(el, { autoAlpha: 0, y: 8 });

        const observer = new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => {
              if (!entry.isIntersecting) return;
              observer.disconnect();
              gsap.to(el, {
                autoAlpha: 1,
                y: 0,
                duration: 0.4,
                delay,
                ease: "power2.out",
              });
            });
          },
          { threshold: 0.1, rootMargin: "0px 0px -48px 0px" }
        );

        observer.observe(el);

        return () => observer.disconnect();
      }
    );

    return () => mm.revert();
  }, [delay]);

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}
