import { HeroFlowDiagram } from "@/components/hero-flow-diagram";
import { UploadPanel } from "@/components/upload-panel";
import { Reveal } from "@/components/reveal";

// Homepage. Sections sit 96px apart on desktop (DESIGN_LANGUAGE.md §6),
// inside a 1152px grid (§7).

export default function Home() {
  return (
    <>
      {/* Hero */}
      <section className="mx-auto max-w-[1152px] px-4 pt-6 pb-16 md:px-8 md:pb-24 lg:pt-8">
        {/* Headline spans full width above both panels, so the upload card
            and the diagram start from the same baseline below it — that's
            what makes "match the upload card's height" a sane target for
            the diagram's cards, rather than comparing two panels that never
            started at the same place. */}
        <Reveal className="flex flex-col gap-4 lg:max-w-[46ch]">
          <h1 className="type-display text-balance text-[27px] leading-[1.1] md:text-[43px] md:leading-[1.05]">
            <span className="text-foreground">Raw data in.</span>
            <br />
            <span className="text-primary">Clear answers out.</span>
          </h1>
          <p className="type-body-lg text-label">
          Upload your data. Discover insights in seconds.
          </p>
        </Reveal>

        <div className="relative mt-8">
          {/* Ambient light behind the card row, not a visible shape — large
              blur radius, low alpha, coastal-blue. -z-10 keeps it behind the
              cards regardless of DOM order; the cards' own opaque fill does
              the rest. */}
          <div
            aria-hidden
            className="pointer-events-none absolute -inset-x-6 -inset-y-8 -z-10 rounded-[48px] bg-coastal-blue/10 blur-3xl"
          />

          <div className="grid grid-cols-1 items-start gap-10 lg:grid-cols-12">
            <Reveal delay={0.1} className="lg:col-span-5">
              <UploadPanel />
            </Reveal>

            <Reveal delay={0.2} className="lg:col-span-7">
              <HeroFlowDiagram />
            </Reveal>
          </div>
        </div>
      </section>
    </>
  );
}
