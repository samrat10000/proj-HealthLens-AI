import { useEffect, useState } from "react";
import { HelpCircle, RotateCcw, UserRound } from "lucide-react";
import type { DiseaseDetail, Feature, Values } from "../api";
import { fieldError, groupBy, normalText, outOfRange } from "../lib";

interface Props {
  detail: DiseaseDetail;
  values: Values;
  onChange: (key: string, v: number | null) => void;
  onLoad: (values: Values) => void;
  onReset: () => void;
}

export default function PatientForm({ detail, values, onChange, onLoad, onReset }: Props) {
  return (
    <div className="card p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Patient parameters</h3>
          <p className="text-sm text-slate-500">Results update live as you edit.</p>
        </div>
        <button onClick={onReset}
                className="no-print inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm text-slate-500 hover:bg-slate-100 hover:text-slate-700">
          <RotateCcw className="h-4 w-4" /> Reset
        </button>
      </div>

      <div className="no-print mt-4 flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-400">Try a real patient:</span>
        {detail.meta.samples.map((s) => (
          <button key={s.label} onClick={() => onLoad(s.values)}
                  className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600 transition hover:border-brand-500 hover:bg-brand-50 hover:text-brand-700">
            <UserRound className="h-3.5 w-3.5" /> {s.label}
          </button>
        ))}
      </div>

      <div className="mt-5 space-y-6">
        {groupBy(detail.features, (f) => f.group).map(([group, feats]) => (
          <fieldset key={group}>
            <legend className="mb-3 text-xs font-semibold uppercase tracking-wider text-brand-700">{group}</legend>
            <div className="grid gap-x-6 gap-y-5 sm:grid-cols-2">
              {feats.map((f) => (
                <Field key={f.key} f={f} value={values[f.key] ?? null} onChange={(v) => onChange(f.key, v)} />
              ))}
            </div>
          </fieldset>
        ))}
      </div>
    </div>
  );
}

function Field({ f, value, onChange }: { f: Feature; value: number | null; onChange: (v: number | null) => void }) {
  const unknown = value === null;
  const err = fieldError(f, value);
  const flag = outOfRange(f, value);
  const normal = normalText(f);

  return (
    <div className={unknown ? "opacity-70" : ""}>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <label className="flex items-center gap-1 text-sm font-medium text-slate-700">
          {f.label}
          {f.help && (
            <span className="group relative">
              <HelpCircle className="h-3.5 w-3.5 cursor-help text-slate-400" />
              <span className="pointer-events-none absolute bottom-5 left-1/2 z-20 hidden w-56 -translate-x-1/2 rounded-lg bg-slate-900 px-3 py-2 text-xs font-normal leading-relaxed text-white shadow-lg group-hover:block">
                {f.help}
              </span>
            </span>
          )}
        </label>
        {f.optional && (
          <label className="flex cursor-pointer select-none items-center gap-1.5 text-[11px] text-slate-400">
            <input type="checkbox" className="h-3 w-3 accent-teal-600" checked={unknown}
                   onChange={(e) => onChange(e.target.checked ? null : f.default)} />
            Not measured
          </label>
        )}
      </div>

      {f.input === "select" ? (
        <SelectInput f={f} value={value} disabled={unknown} onChange={onChange} />
      ) : (
        <NumberInput f={f} value={value} disabled={unknown} invalid={!!err} flag={flag} onChange={onChange} />
      )}

      <div className="mt-1 flex h-4 items-center justify-between text-[11px]">
        {err ? <span className="text-red-600">{err}</span>
          : unknown ? <span className="text-slate-400">Will be estimated by the model</span>
          : flag ? <span className={flag === "high" ? "text-red-600" : "text-amber-600"}>
                     {flag === "high" ? "▲ Above" : "▼ Below"} normal range
                   </span>
          : <span />}
        {normal && <span className="text-slate-400">Normal {normal} {f.unit}</span>}
      </div>
    </div>
  );
}

function SelectInput({ f, value, disabled, onChange }:
  { f: Feature; value: number | null; disabled: boolean; onChange: (v: number) => void }) {
  const opts = f.options ?? [];
  const compact = opts.every((o) => o.label.length <= 12) && opts.length <= 4;
  if (!compact) {
    return (
      <select disabled={disabled} value={value ?? ""} onChange={(e) => onChange(Number(e.target.value))}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50">
        {disabled && <option value="">—</option>}
        {opts.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    );
  }
  return (
    <div className="flex rounded-lg bg-slate-100 p-1">
      {opts.map((o) => (
        <button key={o.value} type="button" disabled={disabled} onClick={() => onChange(o.value)}
                className={`flex-1 rounded-md px-2 py-1.5 text-sm font-medium transition ${
                  value === o.value ? "bg-white text-brand-700 shadow-sm" : "text-slate-500 hover:text-slate-700"
                }`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

function NumberInput({ f, value, disabled, invalid, flag, onChange }: {
  f: Feature; value: number | null; disabled: boolean; invalid: boolean; flag: "low" | "high" | null;
  onChange: (v: number | null) => void;
}) {
  const [draft, setDraft] = useState(value === null ? "" : String(value));
  useEffect(() => {
    if (value === null) setDraft("");
    else if (Number(draft) !== value) setDraft(String(value));
  }, [value]);

  const min = f.min ?? 0;
  const max = f.max ?? 100;
  const p = value === null ? 0 : Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));

  return (
    <div className="flex items-center gap-3">
      <input type="range" min={min} max={max} step={f.step} value={value ?? min} disabled={disabled}
             style={{ ["--pct" as string]: `${p}%` }} className="flex-1"
             onChange={(e) => onChange(Number(e.target.value))} aria-label={f.label} />
      <div className={`flex w-32 items-center rounded-lg border bg-white pr-2 transition focus-within:ring-2 ${
        invalid ? "border-red-300 focus-within:ring-red-100"
          : flag ? "border-amber-300 focus-within:ring-amber-100"
          : "border-slate-200 focus-within:border-brand-500 focus-within:ring-brand-100"}`}>
        <input type="number" inputMode="decimal" disabled={disabled} value={draft} step={f.step}
               className="w-full min-w-0 rounded-lg bg-transparent px-2.5 py-1.5 text-right text-sm font-semibold tabular-nums text-slate-800 outline-none disabled:text-slate-400"
               onChange={(e) => {
                 setDraft(e.target.value);
                 if (e.target.value.trim() === "") return;
                 const n = Number(e.target.value);
                 if (!Number.isNaN(n)) onChange(n);
               }}
               onBlur={() => { if (draft.trim() === "") setDraft(value === null ? "" : String(value)); }} />
        {f.unit && <span className="shrink-0 text-[11px] text-slate-400">{f.unit}</span>}
      </div>
    </div>
  );
}
