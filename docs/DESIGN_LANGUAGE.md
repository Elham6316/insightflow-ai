# InsightFlow Design Language

**Status: SUPERSEDED for the homepage, 2026-08-01.** The homepage was
explicitly rebuilt to match a reference design (pill eyebrow badge, a
hub-and-spoke node diagram converging raw rows into KPI cards, mockup-style
metric cards) after direct instruction to discard this system in favor of
it. That reference contradicts several rules below by name: the badge is
the "generic AI cliché" pattern §17 warns against, the hub-and-spoke diagram
is exactly the "network/constellation of connected dots" concept §19
records as rejected twice, and the floating metric cards are the "fake
dashboard mockup" §17 bans outright. This was a deliberate, explicit
decision, not drift, and it is recorded here rather than left as a silent
contradiction between this file and `app/page.tsx`.

This document still governs the dashboard and any other surface not
explicitly rebuilt against the reference. It is not deleted because the
decision could be revisited, and because sections 15, 16, and 20 (motion
ceilings, accessibility floors, the implementation checklist) still apply
to whatever ships. Revision 4 below is otherwise unchanged.

Reopening it further, beyond the homepage exception above, is a deliberate
decision. Section 19 records every default already rejected, so they do not
return quietly elsewhere.

Scope: the entire product. Marketing, authentication, upload, dashboard,
settings, documentation, errors. Nothing here is page-specific.

---

## 0. How To Use This Document

Read section 1 before designing anything. Every rule that follows is derived
from it, and a rule you cannot trace back to it is a rule someone invented
because it looked good.

When reviewing work, the question is never "does this look nice." It is
"which principle produced this decision." If the answer is none, the decision
is decoration and it comes out.

---

## 1. Brand Philosophy

InsightFlow does not sell AI. It sells clarity.

Every customer arrives with the same problem. They have a file, and the file
is a mess: inconsistent columns, duplicate rows, dates in four formats,
numbers stored as text. They do not want a chart library or a model. They
want a competent specialist to read the file and tell them what is true.

The interface is that specialist. It should feel like someone who has already
read your data and is calm about it.

**The mission, in one sentence: transform scattered information into clear
insight.**

### The derivation

Everything in this document descends from that sentence. The chain is short
and worth memorizing, because it is what makes the design feel inevitable
rather than assembled from a menu.

| Because the mission is... | The design must... | Which produces |
|---|---|---|
| clarity, not analysis | remove noise rather than add emphasis | restraint, the Insight Moment (§10), one finding per view |
| a transformation | show the before, not just the after | resolution states (§3.2), Residual Evidence (§12) |
| trustworthy quantitative work | make figures scannable and ordered | Information Design (§11), tabular numerals |
| a specialist's judgment | be legible about what the machine did | Residual Evidence, visible state |
| calm competence | move only with reason | motion vocabulary (§9), one idle element maximum |
| something used for years | avoid what is currently fashionable | Inter and mono, no dark mode, no trend surfaces |

A design decision that cannot be placed in this table does not belong in the
product.

---

## 2. Design Principles

Six. They are ordered by how often they will be argued away.

**1. Clarity is subtraction.** To make something important, remove what
competes with it. Never add glow, scale, weight, or color to assert
importance when reducing the surroundings would achieve it. This principle
produces the Insight Moment and is the single most distinctive position in
this document.

**2. Show the work.** Where the system removes, merges, corrects, or excludes
anything, the change remains visible. We do not present cleaned results as
though the mess never existed. Cleaning is destruction, and destruction
requires receipts.

**3. One finding per view.** Every screen commits to a single most important
thing. A screen with three highlights has made no decision and has pushed the
work onto the reader. If two findings genuinely compete, the view splits.

**4. State is visible, never implied.** Any element is legibly raw, in
progress, or resolved. The user can always tell what the system has and has
not touched. Nothing rests in an ambiguous middle.

**5. Restraint is arithmetic, not taste.** Ratios, counts, and scales are
specified and checkable. "Looks clean" is not a review standard. "Three type
sizes, one Mark, on the modulus, 96px between sections" is.

**6. Structure before surface.** Alignment, rhythm, and hierarchy are the
craft. Shadow, radius, and color are consequences. When a screen feels wrong,
the fault is in the structure, and adjusting the surface will only hide it.

---

## 3. Visual Identity

**The identity is not a single device.** It is not a texture, a gradient, a
shape, or one clever rule. It is the consistency of seven decisions that never
vary across the product. Any one of them alone is unremarkable. Held together
without exception, across every screen, for years, they become recognizable.

This is deliberate. A single-gimmick identity is copied in an afternoon. A
system of disciplines has to be adopted wholesale, and no competitor will
reorganize their product to do it.

### 3.1 The seven vectors

| Vector | What is fixed | Where defined |
|---|---|---|
| **Color discipline** | six colors, fixed proportions, yellow rationed to a single instance | §4 |
| **Typographic structure** | one sans, one mono, mono owns every figure, three sizes per section | §5 |
| **Spatial rhythm** | 8px modulus, 96px between sections, never negotiated down | §6 |
| **Layout structure** | 1152 grid, asymmetry by default, no centered hero | §7 |
| **Information hierarchy** | label register and value register, distinct and consistent | §11 |
| **Motion vocabulary** | five verbs, no others, one idle element maximum | §9 |
| **Interaction signatures** | the Insight Moment, Residual Evidence, resolution states | §10, §12, §3.2 |

Remove any one and the product still reads as InsightFlow. Remove three and
it does not. That redundancy is the point: an identity that depends on a
single element is fragile to the first product surface where that element
does not apply.

### 3.2 Resolution states

The one visual mechanic that appears across every vector. Any element that
represents data exists in exactly one of three states:

| State | Appearance | Meaning |
|---|---|---|
| **Raw** | off-modulus, rotated 6 to 15deg, Cloud Grey | untouched by the system |
| **Resolving** | interpolating toward alignment | in progress, transitional only |
| **Resolved** | on-modulus, unrotated, role color | processed, trustworthy |

Raw is a starting state or an explicit depiction of unprocessed input. No
element rests Raw. Rotation exists only in Raw; a Resolved element is never
rotated, skewed, or perspective-transformed. Resolved elements never overlap,
because overlap reads as unresolved.

This is how the transformation becomes visible rather than claimed.

### 3.3 The logo-removal test

Applied to any screen: cover the logo. The screen should show soft sand
ground, white surfaces, deep navy type at three sizes, generous and even
vertical rhythm, figures in tabular mono, at most one yellow indicator, and
nothing in motion except possibly one slow element.

That combination, held with no exceptions, is the brand.

---

## 4. Color System

Six colors. No others, ever, for any reason.

| Token | Hex | Share | Role |
|---|---|---|---|
| Soft Sand | `#F7F9FC` | 60% | page background |
| White | `#FFFFFF` | 20% | cards and surfaces |
| Ocean Navy | `#1C3B61` | 10% | typography and icons |
| Coastal Blue | `#3490DC` | 5% | primary interaction |
| Meadow Green | `#A8E6CF` | 3% | success only |
| Sunlight Yellow | `#FFD369` | 2% | insight highlights only |
| Cloud Grey | `#E2E8F0` | structural | borders, dividers, raw and residual elements |

### Rules

- **The proportions are enforced, not aspirational.** A screen that is 30
  percent Coastal Blue is wrong even if every individual use was defensible.
  Proportion is the discipline; individual defensibility is not.
- **Never introduce a hue.** Not for charts, not for states, not for
  illustration, not for a future product line.
- **Sunlight Yellow appears once per viewport.** Not once per section. Once.
  It marks the finding and nothing else: never a button, never a brand accent,
  never a decorative touch. This count is load-bearing and will be the first
  rule someone asks to bend.
- **Hierarchy never comes from color.** It comes from space, weight, and
  scale. Color carries role, not rank.
- Permitted alpha steps only: `/10`, `/15`, `/20`, `/25`, `/35`, `/40`,
  `/60`. No arbitrary opacity values.
- **Gradients** are permitted only between two adjacent brand colors, only
  within data visualization, and never on a surface, button, background, or
  text.
- **Severity is the one sanctioned exception.** Warning and critical keep
  conventional amber and red, because a usability convention that prevents
  costly mistakes outranks brand purity. Info uses Coastal Blue, satisfying
  both. Scoped to severity indicators; it extends nowhere else.
- **No dark mode.** A deliberate identity constraint, not a backlog item.
  Reconsidering it means reopening this document, not filing a ticket.

---

## 5. Typography

Two faces. Both already installed. No third.

| Face | Use |
|---|---|
| **Inter** | display and body, differentiated by size, weight, and tracking |
| **JetBrains Mono** | every figure, plus labels and format hints |

Using one sans across display and body is a harder and more durable
discipline than pairing a characterful display face with a neutral body face.
It also removes a dependency and cannot date. A display face may be added
later only with a longevity argument, never a novelty one.

**The numeral rule.** Every figure that is data (KPI values, row counts,
scores, axis labels, table cells, percentages, durations) is JetBrains Mono
with `tabular-nums`. Numbers inside prose stay in Inter. The eye learns to
find data by texture alone, without reading a word. This single rule does
more identity work than any display face would, and it is what makes §11
possible.

### Type scale

| Role | Size / Line | Weight | Tracking | Face |
|---|---|---|---|---|
| Display | 60 / 1.05 | 700 | -0.03em | Inter |
| H2 | 32 / 1.15 | 650 | -0.02em | Inter |
| H3 | 20 / 1.3 | 600 | -0.01em | Inter |
| Body Large | 18 / 1.6 | 400 | 0 | Inter |
| Body | 16 / 1.6 | 400 | 0 | Inter |
| Small | 14 / 1.5 | 400 | 0 | Inter |
| Label | 11 / 1.4 | 500 | 0.08em, uppercase | JetBrains Mono |
| Data | 14 to 48 | 500 | 0 | JetBrains Mono, tabular-nums |

Mobile: Display drops to 36 / 1.1. Everything else holds.

### Rules

- Measure capped at 65ch for body, 46ch for hero subheads.
- **Never more than three type sizes visible in one section.**
- Body never lighter than weight 400, never smaller than 14px.
- Tracking applies to Display and Label only. Never to body text.
- **No em-dashes or en-dashes in any user-visible string.** Use a period, a
  comma, parentheses, or a plain hyphen. Applies to headlines, labels,
  buttons, errors, empty states, tooltips, and alt text.

---

## 6. Spacing

Base modulus 8px, invisible. It is never drawn as a grid, a guide, or a
texture. Alignment is felt, not displayed.

Scale: `4, 8, 12, 16, 24, 32, 48, 64, 96, 128`

4 is a half-step permitted only for optical icon alignment. Every other value
is a multiple of 8. No arbitrary values.

| Relationship | Space |
|---|---|
| Label to its value | 4 |
| Items within a group | 8 to 12 |
| Groups within a card | 16 to 24 |
| Card internal padding | 24 |
| Card to card | 24 |
| Section to section | 96 desktop, 64 mobile |
| Page top and bottom | 128 desktop, 64 mobile |

**96px between sections is the highest-leverage decision in the system.** It
is what separates premium from competent, it costs nothing to implement, and
it will be the first thing sacrificed to fit more above the fold. It is not
negotiable to 48.

---

## 7. Grid

- 12 columns, **1152px** maximum content width (144 x 8, on modulus).
- 24px gutters. 32px page margins desktop, 16px mobile.
- Breakpoints: 640 / 768 / 1024 / 1280.
- Below 1024 the grid collapses to a single column. There is no two-column
  intermediate state, because it produces cramped layouts that read as
  unresolved.

### Composition rules

- **Asymmetry by default.** 7/5 or 5/7 is preferred to 6/6. Symmetry is
  reserved for genuine peer content, such as a row of four equal KPIs.
- **No dead-centered single-column hero.** A hero is a two-anchor
  composition: content anchor and subject anchor.
- Every x-position and width resolves to the modulus, and this is checkable.
- Layouts reserve margin space for Residual Evidence (§12) on surfaces where
  it can appear, so its arrival never reflows the page.

---

## 8. Components

Components are surfaces. A component is defined by what it contains and how it
aligns, not by its chrome.

### Depth

Depth comes from spacing and hierarchy. Shadow is a secondary cue, and there
is exactly one:

```
--shadow-soft: 0 1px 2px rgba(28,59,97,0.04), 0 2px 8px rgba(28,59,97,0.06)
```

There is no shadow scale and no elevation ladder. If two things need
separating, the answer is space. If space has already been tried and failed,
the answer is a 1px Cloud Grey hairline. Shadow is third and last.

### Radius

| Role | Radius |
|---|---|
| Page containers | 0 |
| Sections | 20 |
| Dialogs | 20 |
| Cards | 16 |
| Inputs | 12 |
| Buttons | 12 (10 at small sizes) |
| Chart bars, marks, ghosts | 4 |

The descending scale keeps concentric shapes optically parallel. Larger
container, larger radius.

### Component rules

- **Buttons.** Coastal Blue fill, white text, no shadow, no gradient. One
  primary action per view. Secondary is a bordered surface, not a grey
  button. Never yellow.
- **Inputs.** 1px Cloud Grey border, 2px Coastal Blue focus ring. Label
  always visible above the field. Placeholder is never the label.
- **Cards.** White, 16px radius, 1px hairline, `--shadow-soft`, 24px padding.
- **Tables.** Never a border under every row. Group rows in threes or fours
  with a single hairline between groups. Numeric columns right-aligned in
  tabular mono. Excluded rows render as Residual Evidence beneath the table
  rather than disappearing.
- **Upload.** Dashed 1px Cloud Grey boundary, solid Coastal Blue on
  drag-over. Content resolves as the file parses.
- **Loading.** Elements resolving from Raw to Resolved. **No spinner exists
  anywhere in this product.**

Reusing headless behavior from a component library is fine. Shipping its
visual defaults is not.

---

## 9. Motion

Motion communicates state change. It never decorates, and it never announces
itself. Implemented in `frontend/lib/motion.ts` so the same behavior is
reused everywhere rather than reinvented per page.

Five verbs. Every animation in the product maps to exactly one:

| Verb | Meaning | Spec |
|---|---|---|
| **Reveal** | content arrives | fade + translateY 8px, 0.4s, `power2.out` |
| **Organize** | disorder becomes order | transform to zero, 1.4s, `power2.inOut`, stagger 0.8 random |
| **Flow** | progressive disclosure of a path or value | stroke-dashoffset or count-up, 1.0 to 1.2s, `power2.out` |
| **Merge** | two states reconcile | positional interpolation, 0.6s, `power2.inOut` |
| **Connect** | interactive acknowledgment | 0.2s, `power2.out` |

### Banned

Bounce, elastic, back, flip, spin, zoom, parallax, infinite decorative loops,
spinners, skeleton shimmer, confetti, typewriter, marquee. Rotation is
permitted only on Raw elements resolving.

Easing is restricted to `power2.out`, `power2.inOut`, `sine.inOut`, and
`none`.

### Ceilings

- Interactive feedback: 0.2s
- Content entrance: 0.4s
- Narrative sequences: 1.4s maximum
- **Idle motion: one element per view, maximum.** 3s or slower, opacity only,
  0.9 to 1.0. Never transform. A second idle element is noise.

### Reduced motion

`gsap.matchMedia()` on every animation without exception. Under
`prefers-reduced-motion: reduce`, content renders **Resolved immediately**,
with marks and evidence in place. No animation, no delay, no half-state. The
reduced-motion view is complete and correct, not a degraded fallback.

---

## 10. The Insight Moment

The product's signature interaction. It fires whenever the AI surfaces
something the user should notice: a discovered insight, a detected anomaly, a
KPI that crossed a threshold, a completed analysis.

**The mechanic is recession, not assertion.** Nothing grows, glows, bounces,
or arrives. The surroundings step back and the subject sharpens. This follows
directly from principle 1: clarity is achieved by removing what competes,
not by shouting louder.

### Sequence

| Phase | Duration | What happens |
|---|---|---|
| **Recede** | 300ms | surrounding content drops to 60 percent opacity. Nothing moves. |
| **Sharpen** | 200ms, overlapping | the subject gains definition: label from 60 percent to full navy, value weight up one step, hairline from Cloud Grey to Ocean Navy |
| **Mark** | 200ms | a 3px Sunlight Yellow edge draws top to bottom (Flow), never fades in |
| **Settle** | 400ms | surroundings return to full opacity. The Mark remains. |

Total, roughly 1.1 seconds.

### Rules

- **Nothing moves.** No translate, no scale, no rotation. The entire moment is
  opacity, color, and weight. A layout shift during an Insight Moment is a
  defect.
- **The dimming is transient. The Mark is permanent.** The moment passes; the
  evidence stays until the view changes. A permanently dimmed interface is a
  failure of this pattern.
- **One at a time, one per view.** Insight Moments never overlap and never
  queue into a sequence. If the system found three things, it presents the
  most important and lists the others plainly.
- **It is always accompanied by words.** The moment draws the eye; the
  sentence explains why. A highlight with no explanation is a decoration.
- Under reduced motion, the end state renders immediately: subject sharpened,
  Mark present, no dimming phase.

This pattern appears on the dashboard when insights arrive, on the upload
screen when profiling completes, and in charts when a standout value is
identified. It is the same choreography every time, which is what makes it a
signature rather than an effect.

---

## 11. Information Design

An information design principle, not the visual identity. It governs
quantitative content and is applied where numbers naturally exist. It is
never forced onto surfaces that have none.

### The Value Column

Where a surface presents figures, it splits into two registers:

| Register | Alignment | Face | Weight | Color |
|---|---|---|---|---|
| **Label** (names, descriptions) | ragged left | Inter | 400 | Ocean Navy at 60 percent |
| **Value** (any figure) | flush right | JetBrains Mono, tabular-nums | 500 | Ocean Navy, full |

- **Align to a shared right edge within a coherent group**: a KPI row, a
  table, a metrics panel, a chart axis. Where several groups sit in one
  column of the layout, extending that edge across them is preferred, because
  it makes the page scannable in a single vertical sweep.
- **Values outweigh their labels.** Full-strength mono against 60 percent
  Inter. This inverts the usual dashboard convention, where the label is
  emphasized and the figure inherits. Here the figure is the content.
- **Figures are never centered.** Centering destroys scannability and is the
  most common accidental violation.
- Applies to KPI tiles, tables, chart axes, insight metrics, row and column
  counts, quality scores, and percentages.

### Where numbers do not exist

Landing, login, settings, documentation, help, errors, and empty states are
first-class surfaces, and they carry the identity without this rule. On those
screens the identity is carried by the other six vectors: color proportion,
type scale, 96px rhythm, grid structure, motion vocabulary, and interaction
patterns. **Do not manufacture figures to create a column.** A page that
invents a statistic to look on-brand has broken a more important rule than
the one it satisfied.

---

## 12. Product Language: Residual Evidence

A product experience principle. Where the system removes, merges, corrects,
or excludes anything, the change stays visible.

When the AI discards duplicate rows, null values, outliers, unparseable
dates, or unusable columns, the discarded items persist as **ghost elements**:
outline only, 1px Cloud Grey, no fill, positioned outside the resolved
structure.

### Rules

- Opacity 25 to 35 percent. Legible as texture, never as content.
- Always **outside** the resolved structure, in the margin or below the
  baseline. Never interleaved with real data.
- Ghost count is proportional to the real discard count, capped at 12 shown.
  Beyond that, the remainder is stated in words.
- Never interactive, never focusable, `aria-hidden`.
- **Never invented.** If nothing was discarded, none is shown. Residual
  Evidence that does not represent a real operation is a lie about the user's
  data, and it is the worst violation available in this system. It is not a
  decorative effect and must never be added to make a screen look richer.

Its most valuable application is on the data quality view, where the report
is literally an account of what was removed, and in charts, where a dropped
outlier stays faintly visible at the position it occupied. That is exactly
where users most want to audit an automated decision.

---

## 13. Interaction Rules

- **Hover.** Hairline to Coastal Blue, `translateY(-2px)`, shadow marginally
  deeper. 0.2s. No glow, no scale, no lift beyond 2px.
- **Focus.** 2px Coastal Blue ring, 2px offset. Always visible. Never removed
  from any element for any reason.
- **Active.** `translateY(1px)`.
- **Disabled.** 50 percent opacity, `cursor: not-allowed`, and a reason
  available nearby. Never a dead control with no explanation.
- **Touch targets.** 44px minimum, 8px minimum separation.
- **Keyboard.** Everything reachable, tab order matching visual order, Escape
  closes overlays, no traps.
- **Interruptibility.** Any animation yields immediately to input. Motion
  never blocks interaction.
- **Hover-only interaction is banned.** Anything reachable by hover is
  reachable by tap and by keyboard.
- **Residual Evidence is inert.** It is evidence, not an affordance.

---

## 14. Data Visualization

Charts are the system at full strength. A bar is a surface. The finding is
the Mark. Excluded points are Residual Evidence.

- **Series palette, in order:** Coastal Blue, Meadow Green, Sunlight Yellow,
  Ocean Navy. No fifth color. A chart needing a fifth series is the wrong
  chart; aggregate or split it.
- **Bar charts are the default.**
- **Pie charts are discouraged.** Above four slices, use a horizontal stacked
  bar. A pie offers no alignment to read.
- **Gridlines:** Cloud Grey, 1px, horizontal only, drawn only where a value
  is read against them.
- **Excluded points render as ghosts** at the position they would have
  occupied.
- No 3D, bevels, shadows on data, or background fills beneath lines.
- **All numerals in tabular mono**, including axis ticks and tooltips.
- Charts draw on (Flow), never pop. Entrance is disabled under reduced
  motion; the chart renders complete.
- **The Insight Moment applies**: the single most important bar or point
  takes the Mark, and the caption states why in words.
- Every chart has an empty state and an error state with retry. A blank axis
  frame is never shown.

---

## 15. Iconography and Imagery

**We do not illustrate.** No illustrations, spot graphics, character art,
isometric scenes, stock photography, laptop mockups, fake dashboard
screenshots, or abstract AI imagery. Where another product places a graphic,
InsightFlow places structured content or nothing. If a surface seems to need
an illustration, it needs better typography.

**Icons.** Lucide, 1.5px stroke, 20px or 24px only. Outline only, no filled
or duotone variants, no mixing families. Ocean Navy by default, Coastal Blue
when interactive, never Sunlight Yellow. Icons support labels rather than
replacing them; icon-only controls require `aria-label`. No emoji in the
interface, anywhere. No hand-drawn SVG paths.

---

## 16. Accessibility

Non-negotiable, and never simplified for velocity.

- **Contrast.** Body text 4.5:1 minimum, large text 3:1, UI boundaries 3:1.
  - Ocean Navy on Soft Sand passes comfortably. The default pairing.
  - Coastal Blue on white passes for large text and UI. **Not for body text.**
  - **Sunlight Yellow fails against white and Soft Sand.** It is never used
    for text, never as a text background, and never as the sole carrier of
    meaning. It is a positional indicator paired with a label. This
    constraint is precisely why the Insight Moment is defined as sharpening
    plus a sentence rather than as a color change.
  - Meadow Green fails as text. Fill and border only; success text uses a
    darker readable green.
- **Never color alone.** Every state distinguished by color is also
  distinguished by icon, label, or position.
- **Residual Evidence is `aria-hidden`.** The authoritative record of what was
  discarded is always a text summary in the accessibility tree ("12 duplicate
  rows removed"). The visual is a redundant encoding of that fact, never the
  only one. A sighted-only audit trail is not an audit trail.
- **Motion.** `prefers-reduced-motion` honored everywhere, delivering a
  complete resolved view.
- **Focus.** Always visible, never removed.
- **Semantics.** Real headings in order, real buttons, real labels tied to
  inputs, live regions for async status, alt text on anything meaningful.
- **Zoom.** Usable to 200 percent without horizontal scroll.
- **Targets.** 44px minimum.

---

## 17. Do and Don't

### Do

- Make things important by reducing what competes with them.
- Show what the system changed, every time there is something real to show.
- Mark exactly one finding per viewport.
- Set every figure in tabular mono, and align figures within their group.
- Let spacing carry hierarchy.
- Ship 96px between sections.
- Give every animation one of the five verbs, and be able to name it.
- Write plainly. Active voice, specific nouns, no filler.
- Provide empty, loading, error, and success states for every async surface.
- Trace every decision back to section 1.

### Don't

- No new colors. Not one.
- No second yellow highlight in a viewport.
- No invented Residual Evidence.
- No manufactured figures to satisfy an alignment rule.
- No drawn grid, dot grid, or graph-paper background.
- No blobs, mesh gradients, glassmorphism, neon glow, floating particles,
  abstract shapes, fake dashboards, laptop mockups, or stock illustration.
- No spinners. Loading is content resolving.
- No dark mode.
- No shadow scale.
- No bounce, elastic, back, flip, spin, zoom, or infinite decorative loops.
- No movement during an Insight Moment.
- No rotation on a Resolved element.
- No yellow buttons, yellow text, or yellow as a brand accent.
- No hierarchy from color.
- No centered figures.
- No em-dashes or en-dashes in user-visible copy.
- No emoji in the interface.
- No border under every table row.
- No pie chart above four slices.
- No hover-only interaction.
- No removed focus rings.
- No centered single-column hero.
- No shipped component-library visual defaults.

---

## 18. Future Scalability

This document is written to survive surfaces that do not exist yet.

### What may never change

These are the invariants. Changing one is a rebrand, not a revision.

1. The six colors and their proportions.
2. Sunlight Yellow means insight, appears once per viewport, and is never an
   accent.
3. Clarity is subtraction. Emphasis by recession, never assertion.
4. Residual Evidence is never invented.
5. The 8px modulus, never drawn.
6. No spinners.
7. Hierarchy never comes from color.

### What may change with justification

Type scale values, spacing scale extensions, radius values, motion durations,
component inventory, chart types, and breakpoints. These are calibration, not
identity.

### Adding a new surface

Before designing one, answer four questions. If any answer is "no", the
surface is not ready.

1. Which of the seven vectors (§3.1) carry the identity here, given that not
   all will apply?
2. What is the single most important thing on this screen, and how is it
   marked?
3. What are its empty, loading, error, and success states?
4. Does anything here exist only because it looked good?

### Internationalization

The type scale must survive strings 40 percent longer than English without
reflow. Under right-to-left languages the label and value registers mirror:
labels ragged right, figures flush left, with tabular alignment preserved.
Figures themselves remain in the locale's numeral system, still tabular. The
identity is the register separation, not the direction.

### Scaling the team

This document is the review standard. A design review asks which principle
produced each decision, not whether the result is attractive. New designers
read sections 1, 2, and 3 before touching anything, and section 19 before
proposing anything that feels new.

### Growth beyond the current product

If InsightFlow adds surfaces with no data at all (a careers page, a pricing
page, a changelog), section 11 does not apply and the remaining vectors carry
the brand unaided. This is the reason the identity was built as a system
rather than a single device: it degrades gracefully, and it was designed to.

---

## 19. Rejected Defaults

Permanent record. Each of these was proposed during design and cut. They are
gravitational, and they will try to return.

**The dot-grid background.** Proposed as the signature surface. It is the most
copied texture in developer tooling (Figma, Framer, Miro, tldraw, Vercel and
Linear marketing). It does not say InsightFlow, it says "made this year." The
8px modulus survives as invisible math and is never drawn.

**"Structured Calm" as a principle set.** Precision, restraint, alignment,
generous whitespace, deep navy, geometric sans. That is a description of
Linear. Adopting a competitor's virtues produces a competent copy.

**Space Grotesk as a display face.** The default choice of the current AI
startup cohort. It dates the product to its moment and fails the timelessness
requirement.

**Residual Evidence as the visual identity.** It is conditional: on a clean
dataset, an empty state, or a marketing page there is nothing to shed and the
identity would vanish. Demoted to a product principle (§12), where it is
mandatory but not load-bearing for the brand.

**The Value Column as the visual identity.** The same error made twice, in
the opposite direction. Elevating one rule to carry the brand forced the
absurd position that a screen without figures should not exist, which would
have broken login, settings, documentation, and errors. Demoted to an
information design principle (§11). The identity is the system (§3), not any
single device.

**A single-gimmick identity, generally.** The lesson from the two rejections
above. Whenever a proposal claims one element makes the product recognizable,
test it against the surface where that element cannot appear. If the identity
disappears there, the proposal is wrong.

---

## 20. Implementation Deltas

Current state versus what this document requires. Ordered by dependency, so
implementation is a known sequence rather than a discovery exercise.

| Priority | Item | Current | Required |
|---|---|---|---|
| 1 | Section spacing | 48 to 64px | 96px desktop, 64 mobile |
| 2 | Type scale | partially applied, Space Grotesk display | Inter throughout at §5 values |
| 3 | Value registers | KPI values left-aligned under labels, some centered | label 60 percent Inter, value full mono, right-aligned within group |
| 4 | Numerals | partially mono | every figure, tabular |
| 5 | Insight Moment | does not exist | build in `lib/motion.ts`, apply to insights and quality score |
| 6 | Spinners | `Loader2` in upload and analysis | replace with resolving content |
| 7 | Residual Evidence | does not exist | build; apply first to data quality view |
| 8 | Resolution states | ad hoc, inline in hero | extract to shared primitive |
| 9 | Color proportions | applied on homepage | audit and extend to dashboard |
| 10 | Empty and error states | partial | complete for every async surface |
| — | Radius tokens | 0 / 20 / 20 / 16 / 12 / 12 / 4 | done |
| — | Shadow token | `--shadow-soft` | done |
| — | Max width | 1152 | done |
| — | Motion helpers | `lib/motion.ts` exists | extend with Insight Moment |

Items 1 through 4 are typography and spacing, and they will change the
product's character more than items 5 through 8 will. They are also the
cheapest. Do them first, and evaluate before building new mechanics.
