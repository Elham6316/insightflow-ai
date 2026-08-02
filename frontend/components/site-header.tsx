import Image from "next/image";
import Link from "next/link";

// Height sits at 72px (9 modulus units), inside the 80px ceiling. Separated
// from the page by a hairline rather than a shadow: depth comes from
// spacing and hierarchy first (DESIGN_LANGUAGE.md §8).
export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur-[2px]">
      <div className="mx-auto flex h-[72px] max-w-[1152px] items-center justify-between px-4 md:px-8">
        <Link
          href="/"
          aria-label="InsightFlow AI, home"
          className="inline-flex items-center rounded-button focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
        >
          {/* Intrinsic size of the asset (3.28:1), so the reserved space
              matches what renders and the header cannot shift on load. The
              explicit auto/auto stops Tailwind preflight's
              `img { height: auto }` from modifying one axis alone. */}
          <Image
            src="/logo.png"
            alt="InsightFlow AI"
            width={128}
            height={39}
            priority
            style={{ width: "auto", height: "auto" }}
          />
        </Link>

        {/* min-h-11 keeps the tap target at the 44px floor (§13); the label
            itself is only 11px tall. */}
        <Link
          href="#upload"
          className="type-label inline-flex min-h-11 items-center rounded-button px-3 text-label transition-colors duration-200 hover:text-foreground focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:outline-none"
        >
          Upload a file
        </Link>
      </div>
    </header>
  );
}
