import type { Contribution } from "../api";

export default function ContributionChart({ items }: { items: Contribution[] }) {
  const top = items.filter((c) => Math.abs(c.impact) >= 0.002).slice(0, 7);
  if (!top.length)
    return <p className="text-sm text-slate-500">All values match the typical healthy patient profile.</p>;
  const max = Math.max(...top.map((c) => Math.abs(c.impact)), 0.05);

  return (
    <ul className="space-y-2.5">
      {top.map((c) => {
        const up = c.impact > 0;
        const w = (Math.abs(c.impact) / max) * 50;
        return (
          <li key={c.feature} className="group">
            <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
              <span className="truncate font-medium text-slate-700">
                {c.label} <span className="font-normal text-slate-400">· {c.display}</span>
              </span>
              <span className={`shrink-0 font-semibold tabular-nums ${up ? "text-red-600" : "text-emerald-600"}`}>
                {up ? "+" : "−"}{Math.abs(c.impact * 100).toFixed(1)} pts
              </span>
            </div>
            <div className="relative h-2 rounded-full bg-slate-100">
              <div className="absolute inset-y-0 left-1/2 w-px bg-slate-300" />
              <div
                className={`absolute inset-y-0 rounded-full transition-all duration-500 ${up ? "bg-red-400" : "bg-emerald-400"}`}
                style={up ? { left: "50%", width: `${w}%` } : { right: "50%", width: `${w}%` }}
              />
            </div>
            <p className="mt-0.5 hidden text-[11px] text-slate-400 group-hover:block">
              Typical healthy value: {c.baseline_display}
            </p>
          </li>
        );
      })}
    </ul>
  );
}
