import { Activity, AlertTriangle, Info, Loader2, Printer, Stethoscope, Zap } from "lucide-react";
import type { DiseaseDetail, Prediction } from "../api";
import { RISK_STYLE, pct } from "../lib";
import ContributionChart from "./ContributionChart";
import RiskGauge from "./RiskGauge";

interface Props {
  detail: DiseaseDetail;
  prediction: Prediction | null;
  loading: boolean;
  error: string | null;
}

export default function ResultPanel({ detail, prediction, loading, error }: Props) {
  if (!prediction) {
    return (
      <div className="card flex min-h-[420px] flex-col items-center justify-center gap-3 p-6 text-slate-400">
        {error ? <><AlertTriangle className="h-8 w-8 text-amber-500" /><p className="text-center text-sm">{error}</p></>
          : <><Loader2 className="h-8 w-8 animate-spin" /><p className="text-sm">Running model…</p></>}
      </div>
    );
  }

  const s = RISK_STYLE[prediction.risk_level];
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <Activity className="h-4 w-4 text-brand-600" /> Diagnostic result
        </div>
        <div className="flex items-center gap-3 text-[11px] text-slate-400">
          {loading ? <span className="flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" /> updating</span>
            : <span className="flex items-center gap-1"><Zap className="h-3 w-3" /> {prediction.latency_ms} ms</span>}
          <button onClick={() => window.print()} className="no-print rounded p-1 hover:bg-slate-100 hover:text-slate-600"
                  title="Print / save report as PDF">
            <Printer className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className={`relative px-5 pt-5 pb-4 transition-opacity ${loading ? "opacity-70" : ""}`}>
        {error && (
          <div className="mb-3 flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {error}
          </div>
        )}
        <div className="flex flex-col items-center">
          <RiskGauge probability={prediction.probability} level={prediction.risk_level} bands={detail.risk_bands} />
          <div className="-mt-3 text-center">
            <div className="text-5xl font-extrabold tracking-tight tabular-nums text-slate-900">
              {pct(prediction.probability, 0)}
            </div>
            <div className="mt-1 text-xs text-slate-500">probability of {detail.positive_label.toLowerCase()}</div>
          </div>
          <span className={`mt-3 inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold ring-1 ${s.bg} ${s.text} ${s.ring}`}>
            <span className="pulse-dot relative inline-block h-2 w-2 rounded-full" style={{ background: s.color, color: s.color }} />
            {s.label}
          </span>
        </div>

        <div className={`mt-5 flex gap-3 rounded-xl p-3.5 text-sm ${s.bg}`}>
          <Stethoscope className={`mt-0.5 h-4 w-4 shrink-0 ${s.text}`} />
          <p className="leading-relaxed text-slate-700">{prediction.advice}</p>
        </div>
      </div>

      <div className="border-t border-slate-100 px-5 py-4">
        <h4 className="mb-1 text-sm font-semibold text-slate-800">What's driving this result</h4>
        <p className="mb-3 text-xs text-slate-500">
          Change in risk vs. a typical healthy patient's value. <span className="text-red-500">Red raises</span>,{" "}
          <span className="text-emerald-600">green lowers</span> risk.
        </p>
        <ContributionChart items={prediction.contributions} />
      </div>

      {prediction.flags.length > 0 && (
        <div className="border-t border-slate-100 px-5 py-4">
          <h4 className="mb-2 text-sm font-semibold text-slate-800">Outside clinical reference range</h4>
          <ul className="space-y-1.5">
            {prediction.flags.map((fl) => (
              <li key={fl.feature} className="flex items-center justify-between gap-2 text-xs">
                <span className="flex items-center gap-1.5 text-slate-600">
                  <span className={`rounded px-1.5 py-0.5 font-semibold ${fl.status === "high" ? "bg-red-50 text-red-600" : "bg-amber-50 text-amber-700"}`}>
                    {fl.status === "high" ? "HIGH" : "LOW"}
                  </span>
                  {fl.label}
                </span>
                <span className="tabular-nums text-slate-500">{fl.value} <span className="text-slate-300">/ {fl.range}</span></span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex items-start gap-2 border-t border-slate-100 bg-slate-50/70 px-5 py-3 text-[11px] leading-relaxed text-slate-500">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <span>
          Model: {prediction.model}
          {prediction.imputed.length > 0 && <> · Estimated (not measured): {prediction.imputed.join(", ")}</>}
          . Educational decision-support only — not a medical diagnosis.
        </span>
      </div>
    </div>
  );
}
