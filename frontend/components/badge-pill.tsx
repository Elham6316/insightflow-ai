import type { LucideIcon } from "lucide-react";

export function BadgePill({ icon: Icon, children }: { icon?: LucideIcon; children: React.ReactNode }) {
  return (
    // text-primary on this tint measures ~3.4:1, below the 4.5:1 floor for
    // text, so the label itself is navy; the tint and icon stay blue.
    <span className="inline-flex items-center gap-1.5 rounded-full bg-coastal-blue/10 px-2.5 py-1 type-label text-foreground">
      {Icon && <Icon className="size-2.5 text-primary" aria-hidden />}
      {children}
    </span>
  );
}
