import gsap from "gsap";

// Shared motion primitives (DESIGN_LANGUAGE.md §9). Every animation in the
// product is built from these five meanings: Reveal, Connect, Organize,
// Merge, Flow. Never bounce, elastic, back, flip, spin or zoom.

export const OCEAN_NAVY = "#1C3B61";
export const LABEL_NAVY = "rgba(28,59,97,0.6)";

/** True when the user has asked for reduced motion. */
export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/** Reveal: cards entering — fade + a short lift, nothing more elaborate. */
export function animateCardIn(
  targets: gsap.TweenTarget,
  opts: { stagger?: number; delay?: number } = {}
) {
  return gsap.from(targets, {
    autoAlpha: 0,
    y: 8,
    duration: 0.4,
    ease: "power2.out",
    stagger: opts.stagger ?? 0,
    delay: opts.delay ?? 0,
  });
}

/**
 * Connect: hover feedback — border draws in, surface lifts slightly, shadow
 * deepens slightly. No glow, no bounce. Returns a cleanup function.
 */
export function animateHoverReveal(el: HTMLElement) {
  const enter = () =>
    gsap.to(el, {
      y: -2,
      borderColor: "var(--coastal-blue, #3490DC)",
      boxShadow: "0 2px 4px 0 rgba(28,59,97,0.06), 0 8px 20px -6px rgba(28,59,97,0.14)",
      duration: 0.2,
      ease: "power2.out",
    });
  const leave = () =>
    gsap.to(el, {
      y: 0,
      borderColor: "var(--border)",
      boxShadow: "var(--shadow-soft)",
      duration: 0.2,
      ease: "power2.out",
    });
  el.addEventListener("pointerenter", enter);
  el.addEventListener("pointerleave", leave);
  return () => {
    el.removeEventListener("pointerenter", enter);
    el.removeEventListener("pointerleave", leave);
  };
}

/** Organize: numbers count up smoothly instead of jumping to their value. */
export function animateCountUp(
  el: HTMLElement,
  target: number,
  opts: { duration?: number; decimals?: number } = {}
) {
  const proxy = { value: 0 };
  const decimals = opts.decimals ?? 0;
  return gsap.to(proxy, {
    value: target,
    duration: opts.duration ?? 1,
    ease: "power2.out",
    onUpdate: () => {
      el.textContent = proxy.value.toFixed(decimals);
    },
  });
}

/**
 * The Insight Moment (§10). Fires when the AI surfaces something the user
 * should notice.
 *
 * The mechanic is recession, not assertion: the surroundings step back, the
 * subject sharpens, the Mark draws in, the surroundings return. Nothing
 * translates, scales or rotates, so the moment can never shift layout. The
 * dimming is transient; the Mark persists until the view changes.
 *
 * The subject may contain [data-insight-label] and [data-insight-mark].
 */
export function animateInsightMoment(
  subject: HTMLElement,
  opts: { siblings?: Element[]; delay?: number } = {}
) {
  const label = subject.querySelector<HTMLElement>("[data-insight-label]");
  const mark = subject.querySelector<HTMLElement>("[data-insight-mark]");
  const siblings = opts.siblings?.filter((el) => el !== subject) ?? [];

  if (prefersReducedMotion()) {
    setInsightMomentResolved(subject);
    return null;
  }

  const tl = gsap.timeline({ delay: opts.delay ?? 0 });

  // Recede: surroundings drop back. Nothing moves.
  if (siblings.length) {
    tl.to(siblings, { opacity: 0.6, duration: 0.3, ease: "power2.out" }, 0);
  }

  // Sharpen: the subject gains definition, overlapping the recede.
  tl.to(subject, { borderColor: OCEAN_NAVY, duration: 0.2, ease: "power2.out" }, 0.15);
  if (label) {
    tl.to(label, { color: OCEAN_NAVY, duration: 0.2, ease: "power2.out" }, 0.15);
  }

  // Mark: draws top to bottom (Flow). Absolutely positioned, so scaling it
  // reveals the edge without displacing any content.
  if (mark) {
    tl.fromTo(
      mark,
      { scaleY: 0, autoAlpha: 1 },
      { scaleY: 1, duration: 0.2, ease: "power2.out", transformOrigin: "top center" },
      0.35
    );
  }

  // Settle: surroundings return. The Mark stays.
  if (siblings.length) {
    tl.to(siblings, { opacity: 1, duration: 0.4, ease: "power2.out" }, 0.55);
  }

  return tl;
}

/** The Insight Moment's end state, applied instantly (reduced motion). */
export function setInsightMomentResolved(subject: HTMLElement) {
  const label = subject.querySelector<HTMLElement>("[data-insight-label]");
  const mark = subject.querySelector<HTMLElement>("[data-insight-mark]");
  gsap.set(subject, { borderColor: OCEAN_NAVY });
  if (label) gsap.set(label, { color: OCEAN_NAVY });
  if (mark) gsap.set(mark, { scaleY: 1, autoAlpha: 1, transformOrigin: "top center" });
}

/** Flow: an SVG path draws itself on, never "pops" in. */
export function animateChartDraw(
  pathEl: SVGPathElement,
  opts: { duration?: number; delay?: number } = {}
) {
  const length = pathEl.getTotalLength();
  gsap.set(pathEl, { strokeDasharray: length, strokeDashoffset: length });
  return gsap.to(pathEl, {
    strokeDashoffset: 0,
    duration: opts.duration ?? 1.2,
    delay: opts.delay ?? 0,
    ease: "power2.out",
  });
}
