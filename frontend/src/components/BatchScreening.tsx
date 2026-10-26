import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle, ArrowUpDown, CheckCircle2, ChevronRight, Download, FileSpreadsheet, Loader2, RefreshCw,
  Search, Upload, XCircle,
} from "lucide-react";
import { api, fileUrl, type BatchResult, type BatchRow, type DiseaseId, type Values } from "../api";
import { RISK_STYLE, pct } from "../lib";

interface Props {
  result: BatchResult | null;
  onResult: (r: BatchResult | null) => void;
  onOpenPatient: (disease: DiseaseId, values: Values) => void;
}

const DISEASES: { id: DiseaseId; name: string }[] = [
  { id: "heart", name: "Heart disease" },
  { id: "diabetes", name: "Diabetes" },
  { id: "liver", name: "Liver disorder" },
];

export default function BatchScreening({ result, onResult, onOpenPatient }: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const upload = async (file: File) => {
    setBusy(file.name);
    setError(null);
    try {
      onResult(await api.batch(file));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const tryDemo = async (id: DiseaseId) => {
    const res = await fetch(fileUrl("sample", id, "csv"));
    upload(new File([await res.blob()], `${id}_patients.csv`, { type: "text/csv" }));
  };

  // ?demo=heart|diabetes|liver runs the sample file straight away (handy for presentations)
  useEffect(() => {
    const demo = new URLSearchParams(window.location.search).get("demo") as DiseaseId | null;
    if (demo && DISEASES.some((d) => d.id === demo)) tryDemo(demo);
  }, []);

  return (
    <div className="space-y-6">
      {(!result || busy) && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
          <DropZone busy={busy} error={error} onFile={upload} onDemo={tryDemo} />
          <FileLibrary />
        </div>
      )}
      {result && !busy && (
        <Results result={result} onReset={() => onResult(null)} onUpload={upload} error={error}
                 onOpen={(row) => onOpenPatient(result.disease, row.values)} />
      )}
    </div>
  );
}

// ------------------------------------------------------------------ upload

function DropZone({ busy, error, onFile, onDemo }: {
  busy: string | null; error: string | null; onFile: (f: File) => void; onDemo: (id: DiseaseId) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  return (
    <div className="card p-5 sm:p-6">
      <button type="button" disabled={!!busy} onClick={() => input.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setOver(true); }}
              onDragLeave={() => setOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setOver(false);
                const f = e.dataTransfer.files[0];
                if (f) onFile(f);
              }}
              className={`flex min-h-[260px] w-full flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition ${
                over ? "border-brand-500 bg-brand-50" : "border-slate-200 bg-slate-50/60 hover:border-brand-500 hover:bg-brand-50/50"}`}>
        {busy ? (
          <>
            <Loader2 className="h-10 w-10 animate-spin text-brand-600" />
            <div>
              <p className="font-semibold text-slate-800">Screening patients…</p>
              <p className="mt-1 text-sm text-slate-500">{busy}</p>
            </div>
          </>
        ) : (
          <>
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white text-brand-600 shadow-sm ring-1 ring-slate-200">
              <Upload className="h-7 w-7" />
            </div>
            <div>
              <p className="text-lg font-semibold text-slate-800">
                Drop a patient file here or <span className="text-brand-600 underline underline-offset-4">browse</span>
              </p>
              <p className="mt-1.5 text-sm text-slate-500">CSV or Excel (.xlsx) · one patient per row · up to 5,000 rows</p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 text-[11px] text-slate-500">
              {["Disease detected automatically", "Kaggle column names accepted", "Blank cells are estimated"].map((t) => (
                <span key={t} className="rounded-full bg-white px-2.5 py-1 ring-1 ring-slate-200">✓ {t}</span>
              ))}
            </div>
          </>
        )}
      </button>
      <input ref={input} type="file" accept=".csv,.xlsx,.xls,.xlsm,text/csv" className="hidden"
             onChange={(e) => {
               const f = e.target.files?.[0];
               if (f) onFile(f);
               e.target.value = "";
             }} />
      {!busy && (
        <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-sm">
          <span className="text-slate-500">No file handy? Try it with 40 real patients:</span>
          {DISEASES.map((d) => (
            <button key={d.id} onClick={() => onDemo(d.id)}
                    className="rounded-full border border-brand-200 bg-white px-3 py-1 text-xs font-semibold text-brand-700 transition hover:bg-brand-50">
              {d.name}
            </button>
          ))}
        </div>
      )}
      {error && (
        <div className="mt-4 flex items-start gap-2 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> {error}
        </div>
      )}
    </div>
  );
}

function FileLibrary() {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-2">
        <FileSpreadsheet className="h-5 w-5 text-brand-600" />
        <h3 className="font-semibold text-slate-900">Need a file?</h3>
      </div>
      <p className="mt-1 text-sm text-slate-500">
        <b className="font-medium text-slate-700">Sample patients</b> are 40 real records with their recorded diagnosis.
        A <b className="font-medium text-slate-700">template</b> has the right columns for your own data.
      </p>
      <ul className="mt-4 divide-y divide-slate-100">
        {DISEASES.map((d) => (
          <li key={d.id} className="py-3">
            <div className="text-sm font-medium text-slate-800">{d.name}</div>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              <DownloadChip href={fileUrl("sample", d.id, "csv")} label="Sample CSV" primary />
              <DownloadChip href={fileUrl("sample", d.id, "xlsx")} label="Sample Excel" primary />
              <DownloadChip href={fileUrl("template", d.id, "csv")} label="Template" />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function DownloadChip({ href, label, primary }: { href: string; label: string; primary?: boolean }) {
  return (
    <a href={href} download
       className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium transition ${
         primary ? "bg-brand-50 text-brand-700 hover:bg-brand-100" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>
      <Download className="h-3 w-3" /> {label}
    </a>
  );
}

// ------------------------------------------------------------------ results

type Filter = "all" | "high" | "moderate" | "low" | "errors";

function Results({ result, onReset, onUpload, onOpen, error }: {
  result: BatchResult; onReset: () => void; onUpload: (f: File) => void; onOpen: (row: BatchRow) => void;
  error: string | null;
}) {
  const s = result.summary;
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [byRisk, setByRisk] = useState(true);
  const input = useRef<HTMLInputElement>(null);
  const hasActual = s.labelled > 0;

  const rows = useMemo(() => {
    let r = result.rows.filter((row) =>
      filter === "all" ? true : filter === "errors" ? row.errors.length > 0 : row.risk_level === filter);
    if (query.trim()) r = r.filter((row) => row.patient_id.toLowerCase().includes(query.trim().toLowerCase()));
    if (byRisk) r = [...r].sort((a, b) => (b.probability ?? -1) - (a.probability ?? -1));
    return r;
  }, [result, filter, query, byRisk]);

  const tiles: { label: string; value: string; sub?: string; tone?: string }[] = [
    { label: "Patients screened", value: String(s.scored), sub: `of ${s.total} rows` },
    { label: "High risk", value: String(s.high), sub: s.scored ? pct(s.high / s.scored, 0) : "", tone: "text-red-600" },
    { label: "Moderate risk", value: String(s.moderate), sub: s.scored ? pct(s.moderate / s.scored, 0) : "", tone: "text-amber-600" },
    { label: "Low risk", value: String(s.low), sub: s.scored ? pct(s.low / s.scored, 0) : "", tone: "text-emerald-600" },
  ];
  if (hasActual) tiles.push({ label: "Matches recorded diagnosis", value: pct(s.agreement ?? 0, 0), sub: `${s.labelled} labelled patients` });
  if (s.errors) tiles.push({ label: "Rows needing fixes", value: String(s.errors), tone: "text-red-600" });

  return (
    <div className="space-y-6">
      <div className="card p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
              <FileSpreadsheet className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h3 className="truncate text-lg font-semibold text-slate-900">{result.filename}</h3>
              <p className="text-sm text-slate-500">
                {result.auto_detected ? "Detected" : "Screened as"}{" "}
                <b className="font-semibold text-brand-700">{result.disease_name}</b> data · {s.scored} patients scored in{" "}
                {(result.elapsed_ms / 1000).toFixed(2)} s · {result.model}
              </p>
            </div>
          </div>
          <div className="no-print flex flex-wrap gap-2">
            <button onClick={() => exportCsv(result)}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-brand-700">
              <Download className="h-4 w-4" /> Download results
            </button>
            <button onClick={() => input.current?.click()}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
              <Upload className="h-4 w-4" /> New file
            </button>
            <button onClick={onReset} title="Back to upload"
                    className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-slate-500 hover:bg-slate-50">
              <RefreshCw className="h-4 w-4" />
            </button>
            <input ref={input} type="file" accept=".csv,.xlsx,.xls,.xlsm" className="hidden"
                   onChange={(e) => { const f = e.target.files?.[0]; if (f) onUpload(f); e.target.value = ""; }} />
          </div>
        </div>
        {error && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {tiles.map((t) => (
            <div key={t.label} className="rounded-xl bg-slate-50 px-4 py-3">
              <div className="text-[11px] font-medium text-slate-500">{t.label}</div>
              <div className={`mt-0.5 text-2xl font-bold tabular-nums ${t.tone ?? "text-slate-900"}`}>{t.value}</div>
              {t.sub && <div className="text-[11px] text-slate-400">{t.sub}</div>}
            </div>
          ))}
        </div>

        {s.scored > 0 && <RiskBar low={s.low} moderate={s.moderate} high={s.high} />}

        <details className="mt-4 text-sm">
          <summary className="cursor-pointer select-none text-slate-500 hover:text-slate-700">
            How your columns were read ({result.columns.recognised.length} recognised
            {result.columns.ignored.length ? `, ${result.columns.ignored.length} ignored` : ""})
          </summary>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {result.columns.recognised.map((c) => (
              <span key={c.column} className="rounded-md bg-emerald-50 px-2 py-1 text-xs text-emerald-800">
                {c.column} {norm(c.column) !== norm(c.feature) && <span className="text-emerald-600">→ {c.feature}</span>}
              </span>
            ))}
            {result.columns.id_column && <span className="rounded-md bg-sky-50 px-2 py-1 text-xs text-sky-800">{result.columns.id_column} → patient ID</span>}
            {result.columns.target_column && <span className="rounded-md bg-sky-50 px-2 py-1 text-xs text-sky-800">{result.columns.target_column} → recorded diagnosis</span>}
            {result.columns.ignored.map((c) => <span key={c} className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-500 line-through">{c}</span>)}
            {result.columns.not_provided.map((c) => <span key={c} className="rounded-md bg-amber-50 px-2 py-1 text-xs text-amber-800">{c}: not in file, estimated</span>)}
          </div>
        </details>
      </div>

      <div className="card overflow-hidden">
        <div className="no-print flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-3">
          <div className="flex flex-wrap gap-1.5">
            {([["all", "All", s.total], ["high", "High", s.high], ["moderate", "Moderate", s.moderate],
               ["low", "Low", s.low], ["errors", "Errors", s.errors]] as [Filter, string, number][])
              .filter(([id, , n]) => id === "all" || n > 0)
              .map(([id, label, n]) => (
                <button key={id} onClick={() => setFilter(id)}
                        className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                          filter === id ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>
                  {label} <span className="tabular-nums opacity-70">{n}</span>
                </button>
              ))}
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 rounded-lg border border-slate-200 px-2.5 py-1.5 focus-within:border-brand-500">
              <Search className="h-3.5 w-3.5 text-slate-400" />
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Find patient ID"
                     className="w-32 bg-transparent text-sm outline-none placeholder:text-slate-400" />
            </label>
            <button onClick={() => setByRisk((v) => !v)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50">
              <ArrowUpDown className="h-3.5 w-3.5" /> {byRisk ? "Highest risk first" : "File order"}
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-sm">
            <thead className="bg-slate-50/80 text-left text-[11px] uppercase tracking-wide text-slate-400">
              <tr>
                <th className="px-5 py-2.5 font-medium">Patient</th>
                <th className="py-2.5 font-medium">Risk</th>
                <th className="py-2.5 font-medium">Result</th>
                <th className="py-2.5 font-medium">Main reasons</th>
                {hasActual && <th className="py-2.5 font-medium">Recorded</th>}
                <th className="py-2.5" />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => <Row key={row.row} row={row} hasActual={hasActual} onOpen={() => onOpen(row)} />)}
              {!rows.length && (
                <tr><td colSpan={6} className="px-5 py-10 text-center text-sm text-slate-400">No patients match this filter.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Row({ row, hasActual, onOpen }: { row: BatchRow; hasActual: boolean; onOpen: () => void }) {
  if (row.errors.length) {
    return (
      <tr className="border-t border-slate-100 bg-red-50/40">
        <td className="px-5 py-3 align-top">
          <div className="font-medium text-slate-800">{row.patient_id}</div>
          <div className="text-[11px] text-slate-400">row {row.row}</div>
        </td>
        <td colSpan={hasActual ? 5 : 4} className="py-3 pr-5">
          <div className="flex items-start gap-2 text-xs text-red-700">
            <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>Not scored: {row.errors.join(" · ")}</span>
          </div>
        </td>
      </tr>
    );
  }
  const st = RISK_STYLE[row.risk_level!];
  const correct = row.actual !== null && row.actual === row.predicted;
  return (
    <tr className="group border-t border-slate-100 transition hover:bg-slate-50/70">
      <td className="px-5 py-3">
        <div className="font-medium text-slate-800">{row.patient_id}</div>
        <div className="text-[11px] text-slate-400">
          row {row.row}{row.imputed!.length > 0 && ` · ${row.imputed!.length} estimated`}
        </div>
      </td>
      <td className="w-48 py-3 pr-4">
        <div className="flex items-center gap-2.5">
          <span className="w-10 text-right font-bold tabular-nums text-slate-900">{pct(row.probability!, 0)}</span>
          <div className="h-1.5 flex-1 rounded-full bg-slate-100">
            <div className="h-1.5 rounded-full" style={{ width: `${Math.max(2, row.probability! * 100)}%`, background: st.color }} />
          </div>
        </div>
      </td>
      <td className="py-3 pr-4">
        <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${st.bg} ${st.text} ${st.ring}`}>
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: st.color }} />
          {st.label}
        </span>
        <div className="mt-0.5 text-[11px] text-slate-500">{row.prediction}</div>
      </td>
      <td className="max-w-[300px] py-3 pr-4">
        {row.top_factors!.length ? (
          <div className="flex flex-wrap gap-1">
            {row.top_factors!.map((f) => (
              <span key={f.feature} title={`+${(f.impact * 100).toFixed(1)} pts · typical healthy: ${f.baseline_display}`}
                    className="rounded-md bg-red-50 px-1.5 py-0.5 text-[11px] text-red-700">
                {f.label}: {f.display}
              </span>
            ))}
          </div>
        ) : <span className="text-[11px] text-slate-400">No strong risk factors</span>}
      </td>
      {hasActual && (
        <td className="py-3 pr-4">
          {row.actual === null ? <span className="text-slate-300">—</span> : (
            <span className={`inline-flex items-center gap-1 text-xs font-medium ${correct ? "text-emerald-700" : "text-slate-500"}`}>
              {correct ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5 text-slate-400" />}
              {row.actual ? "Disease" : "Healthy"}
            </span>
          )}
        </td>
      )}
      <td className="py-3 pr-5 text-right">
        <button onClick={onOpen}
                className="no-print inline-flex items-center gap-0.5 rounded-lg px-2 py-1 text-xs font-medium text-brand-700 opacity-70 transition hover:bg-brand-50 group-hover:opacity-100">
          Details <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </td>
    </tr>
  );
}

function RiskBar({ low, moderate, high }: { low: number; moderate: number; high: number }) {
  const total = low + moderate + high;
  const parts = [
    { n: low, label: "Low", color: RISK_STYLE.low.color },
    { n: moderate, label: "Moderate", color: RISK_STYLE.moderate.color },
    { n: high, label: "High", color: RISK_STYLE.high.color },
  ].filter((p) => p.n > 0);
  return (
    <div className="mt-5">
      <div className="flex h-3 gap-0.5 overflow-hidden rounded-full">
        {parts.map((p) => (
          <div key={p.label} title={`${p.label} risk: ${p.n} patients (${pct(p.n / total, 0)})`}
               style={{ width: `${(p.n / total) * 100}%`, background: p.color }} />
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-4 text-[11px] text-slate-500">
        {parts.map((p) => (
          <span key={p.label} className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
            {p.label} risk · {p.n}
          </span>
        ))}
      </div>
    </div>
  );
}

const norm = (s: string) => s.toLowerCase().replace(/\(.*?\)/g, "").replace(/[^a-z0-9]/g, "");

function exportCsv(result: BatchResult) {
  const header = ["Patient ID", "Row", "Risk %", "Risk level", "Prediction", "Recorded diagnosis", "Match",
                  "Main reasons", "Out-of-range values", "Estimated values", "Errors"];
  const esc = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const lines = result.rows.map((r) => [
    r.patient_id, r.row,
    r.probability !== undefined ? (r.probability * 100).toFixed(1) : "",
    r.risk_level ?? "", r.prediction ?? "",
    r.actual === null ? "" : r.actual ? "Disease" : "Healthy",
    r.actual === null || r.predicted === undefined ? "" : r.actual === r.predicted ? "Yes" : "No",
    (r.top_factors ?? []).map((f) => `${f.label}: ${f.display}`).join("; "),
    (r.flags ?? []).join("; "), (r.imputed ?? []).join("; "), r.errors.join("; "),
  ].map(esc).join(","));
  const blob = new Blob(["﻿" + [header.map(esc).join(","), ...lines].join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = result.filename.replace(/\.[^.]+$/, "") + "_results.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}
