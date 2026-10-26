import type { Feature, Values } from "./api";

export const RISK_STYLE = {
  low: { label: "Low risk", color: "#10b981", bg: "bg-emerald-50", text: "text-emerald-700", ring: "ring-emerald-200" },
  moderate: { label: "Moderate risk", color: "#f59e0b", bg: "bg-amber-50", text: "text-amber-700", ring: "ring-amber-200" },
  high: { label: "High risk", color: "#ef4444", bg: "bg-red-50", text: "text-red-700", ring: "ring-red-200" },
} as const;

export const pct = (v: number, digits = 1) => `${(v * 100).toFixed(digits)}%`;

export function defaults(features: Feature[]): Values {
  return Object.fromEntries(features.map((f) => [f.key, f.default]));
}

export function fieldError(f: Feature, v: number | null): string | null {
  if (v === null) return f.optional ? null : "Required";
  if (f.input === "number" && (v < (f.min ?? -Infinity) || v > (f.max ?? Infinity)))
    return `Must be ${f.min}–${f.max}`;
  return null;
}

export function outOfRange(f: Feature, v: number | null): "low" | "high" | null {
  if (v === null || !f.normal) return null;
  const [lo, hi] = f.normal;
  if (lo !== null && v < lo) return "low";
  if (hi !== null && v > hi) return "high";
  return null;
}

export function normalText(f: Feature): string | null {
  if (!f.normal) return null;
  const [lo, hi] = f.normal;
  if (lo === null) return `≤ ${hi}`;
  if (hi === null) return `≥ ${lo}`;
  return `${lo}–${hi}`;
}

export function groupBy<T>(items: T[], key: (t: T) => string): [string, T[]][] {
  const map = new Map<string, T[]>();
  for (const it of items) {
    const k = key(it);
    if (!map.has(k)) map.set(k, []);
    map.get(k)!.push(it);
  }
  return [...map.entries()];
}
