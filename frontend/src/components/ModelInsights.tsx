import { useState } from "react";
import { BarChart3, Database, Grid3x3, LineChart as LineIcon, ListOrdered, Trophy } from "lucide-react";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DiseaseDetail } from "../api";
import { pct } from "../lib";

const TABS = [
  { id: "leaderboard", label: "Model comparison", icon: Trophy },
  { id: "roc", label: "ROC curve", icon: LineIcon },
  { id: "confusion", label: "Confusion matrix", icon: Grid3x3 },
  { id: "importance", label: "Feature importance", icon: BarChart3 },
  { id: "pipeline", label: "Data pipeline", icon: Database },
] as const;
type Tab = (typeof TABS)[number]["id"];

export default function ModelInsights({ detail }: { detail: DiseaseDetail }) {
  const [tab, setTab] = useState<Tab>(
    () => TABS.find((t) => t.id === new URLSearchParams(window.location.search).get("tab"))?.id ?? "leaderboard");
  const m = detail.meta;

  return (
    <section className="card p-5 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Under the hood: {detail.name} model</h3>
          <p className="text-sm text-slate-500">
            {m.leaderboard.length} algorithms compared with {m.cv_folds}-fold stratified cross-validation · trained {m.trained_at}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
          {[["Accuracy", m.holdout.accuracy], ["ROC-AUC", m.holdout.roc_auc], ["F1", m.holdout.f1],
            ["Precision", m.holdout.precision], ["Recall", m.holdout.recall]].map(([k, v]) => (
            <div key={k} className="rounded-xl bg-slate-50 px-3 py-2 text-center">
              <div className="text-[10px] font-medium uppercase tracking-wide text-slate-400">{k}</div>
              <div className="text-base font-bold tabular-nums text-slate-800">{(v as number).toFixed(3)}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="no-print mt-5 flex gap-1 overflow-x-auto border-b border-slate-100">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
                  className={`-mb-px flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition ${
                    tab === t.id ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-700"}`}>
            <t.icon className="h-4 w-4" /> {t.label}
          </button>
        ))}
      </div>

      <div className="pt-5">
        {tab === "leaderboard" && <Leaderboard detail={detail} />}
        {tab === "roc" && <Roc detail={detail} />}
        {tab === "confusion" && <Confusion detail={detail} />}
        {tab === "importance" && <Importance detail={detail} />}
        {tab === "pipeline" && <Pipeline detail={detail} />}
      </div>
      <p className="mt-4 text-[11px] text-slate-400">
        Headline metrics are measured on a stratified 20% hold-out set ({m.holdout.n_test} patients) never seen during
        model selection. The deployed model is then refit on all data.
      </p>
    </section>
  );
}

function Leaderboard({ detail }: { detail: DiseaseDetail }) {
  const rows = detail.meta.leaderboard;
  const lo = Math.min(...rows.map((r) => r.roc_auc)) - 0.03;
  const hi = Math.max(...rows.map((r) => r.roc_auc));
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-sm">
        <thead>
          <tr className="text-left text-[11px] uppercase tracking-wide text-slate-400">
            <th className="pb-2 font-medium">#</th>
            <th className="pb-2 font-medium">Algorithm</th>
            <th className="pb-2 font-medium">CV ROC-AUC</th>
            <th className="pb-2 text-right font-medium">Accuracy</th>
            <th className="pb-2 text-right font-medium">F1</th>
            <th className="pb-2 text-right font-medium">Precision</th>
            <th className="pb-2 text-right font-medium">Recall</th>
            <th className="pb-2 text-right font-medium">Time</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.model} className={`border-t border-slate-100 ${i === 0 ? "bg-brand-50/60" : ""}`}>
              <td className="py-2.5 pl-1 text-slate-400 tabular-nums">{i + 1}</td>
              <td className="py-2.5">
                <div className="flex items-center gap-2 font-medium text-slate-800">
                  {r.model}
                  {i === 0 && <span className="rounded-full bg-brand-600 px-2 py-0.5 text-[10px] font-semibold text-white">DEPLOYED</span>}
                </div>
                {r.members && <div className="text-[11px] text-slate-400">blend of {r.members.join(" + ")}</div>}
              </td>
              <td className="w-56 py-2.5 pr-4">
                <div className="flex items-center gap-2" title={`${r.roc_auc.toFixed(3)} ± ${r.roc_auc_std.toFixed(3)}`}>
                  <div className="h-2 flex-1 rounded-full bg-slate-100">
                    <div className="h-2 rounded-full bg-brand-500"
                         style={{ width: `${Math.max(4, ((r.roc_auc - lo) / (hi - lo)) * 100)}%` }} />
                  </div>
                  <span className="w-11 text-right font-semibold tabular-nums text-slate-700">{r.roc_auc.toFixed(3)}</span>
                </div>
              </td>
              {[r.accuracy, r.f1, r.precision, r.recall].map((v, j) => (
                <td key={j} className="py-2.5 text-right tabular-nums text-slate-600">{v.toFixed(3)}</td>
              ))}
              <td className="py-2.5 text-right tabular-nums text-slate-400">{r.train_time_s.toFixed(1)}s</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-[11px] text-slate-400">Bars are scaled to the range of scores, so small differences are visible. Hover a bar for ± std across folds.</p>
    </div>
  );
}

function Roc({ detail }: { detail: DiseaseDetail }) {
  const data = detail.meta.holdout.roc_curve.map((p) => ({ ...p, chance: p.fpr }));
  return (
    <div className="grid items-center gap-6 md:grid-cols-[1fr_240px]">
      <div className="h-72">
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 18, left: 0 }}>
            <defs>
              <linearGradient id="roc" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#14b8a6" stopOpacity={0.25} />
                <stop offset="100%" stopColor="#14b8a6" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#f1f5f9" />
            <XAxis dataKey="fpr" type="number" domain={[0, 1]} tickCount={6} tick={{ fontSize: 11, fill: "#94a3b8" }}
                   label={{ value: "False positive rate", position: "insideBottom", offset: -10, fontSize: 11, fill: "#64748b" }} />
            <YAxis type="number" domain={[0, 1]} tickCount={6} tick={{ fontSize: 11, fill: "#94a3b8" }} width={36} />
            <Tooltip formatter={(v: number, n: string) => [v.toFixed(3), n === "tpr" ? "True positive rate" : "Chance"]}
                     labelFormatter={(v: number) => `FPR ${Number(v).toFixed(3)}`}
                     contentStyle={{ borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 12 }} />
            <Line dataKey="chance" stroke="#cbd5e1" strokeDasharray="4 4" dot={false} strokeWidth={1.5} isAnimationActive={false} />
            <Area dataKey="tpr" type="stepAfter" stroke="#0d9488" strokeWidth={2} fill="url(#roc)" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-xl bg-slate-50 p-4">
        <div className="text-xs font-medium uppercase tracking-wide text-slate-400">Area under curve</div>
        <div className="text-4xl font-extrabold tabular-nums text-slate-900">{detail.meta.holdout.roc_auc.toFixed(3)}</div>
        <p className="mt-2 text-xs leading-relaxed text-slate-500">
          The probability the model ranks a random sick patient above a random healthy one. 0.5 is a coin flip
          (dashed line), 1.0 is perfect.
        </p>
      </div>
    </div>
  );
}

function Confusion({ detail }: { detail: DiseaseDetail }) {
  const [[tn, fp], [fn, tp]] = detail.meta.holdout.confusion_matrix;
  const max = Math.max(tn, fp, fn, tp);
  const cell = (v: number, label: string, good: boolean) => (
    <div className="flex aspect-[4/3] flex-col items-center justify-center rounded-xl ring-1 ring-slate-200/60"
         title={`${label}: ${v} patients`}
         style={{ background: `rgba(13,148,136,${0.08 + (v / max) * 0.62})` }}>
      <span className={`text-3xl font-extrabold tabular-nums ${v / max > 0.55 ? "text-white" : "text-slate-800"}`}>{v}</span>
      <span className={`text-[11px] font-medium ${v / max > 0.55 ? "text-white/85" : "text-slate-600"}`}>
        {good ? "✓" : "✗"} {label}
      </span>
    </div>
  );
  const total = tn + fp + fn + tp;
  return (
    <div className="grid items-center gap-6 md:grid-cols-[1fr_260px]">
      <div className="mx-auto w-full max-w-md">
        <div className="mb-2 grid grid-cols-[80px_1fr_1fr] gap-2 text-center text-[11px] font-medium text-slate-500">
          <span /><span>Predicted: {detail.negative_label}</span><span>Predicted: {detail.positive_label}</span>
        </div>
        <div className="grid grid-cols-[80px_1fr_1fr] gap-2">
          <span className="self-center text-right text-[11px] font-medium text-slate-500">Actual: healthy</span>
          {cell(tn, "True negative", true)}{cell(fp, "False positive", false)}
          <span className="self-center text-right text-[11px] font-medium text-slate-500">Actual: disease</span>
          {cell(fn, "False negative", false)}{cell(tp, "True positive", true)}
        </div>
      </div>
      <dl className="space-y-3 rounded-xl bg-slate-50 p-4 text-sm">
        {[["Sensitivity (recall)", tp / (tp + fn)], ["Specificity", tn / (tn + fp)],
          ["Positive predictive value", tp / (tp + fp)], ["Overall accuracy", (tp + tn) / total]].map(([k, v]) => (
          <div key={k as string} className="flex justify-between gap-2">
            <dt className="text-slate-500">{k}</dt>
            <dd className="font-semibold tabular-nums text-slate-800">{pct(v as number)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function Importance({ detail }: { detail: DiseaseDetail }) {
  const rows = detail.meta.feature_importance;
  const max = Math.max(...rows.map((r) => r.importance), 0.001);
  return (
    <div>
      <p className="mb-4 flex items-center gap-1.5 text-xs text-slate-500">
        <ListOrdered className="h-3.5 w-3.5" /> Permutation importance: how much ROC-AUC drops when a feature is shuffled.
      </p>
      <ul className="space-y-2">
        {rows.map((r) => (
          <li key={r.feature} className="grid grid-cols-[minmax(120px,200px)_1fr_56px] items-center gap-3 text-sm"
              title={`${r.label}: AUC drop ${r.importance.toFixed(4)}`}>
            <span className="truncate text-slate-600">{r.label}</span>
            <div className="h-2.5 rounded-full bg-slate-100">
              <div className="h-2.5 rounded-full bg-brand-500 transition-all"
                   style={{ width: `${Math.max(0, (r.importance / max) * 100)}%` }} />
            </div>
            <span className="text-right text-xs tabular-nums text-slate-500">{r.importance.toFixed(3)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Pipeline({ detail }: { detail: DiseaseDetail }) {
  const c = detail.meta.cleaning;
  const missing = Object.entries(c.missing_after_cleaning);
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
      <ol className="relative space-y-4 border-l-2 border-brand-100 pl-6">
        {c.steps.map((s, i) => (
          <li key={i} className="relative">
            <span className="absolute -left-[33px] flex h-4 w-4 items-center justify-center rounded-full bg-brand-600 text-[9px] font-bold text-white">
              {i + 1}
            </span>
            <div className="text-sm font-semibold text-slate-800">{s.action}</div>
            <div className="text-xs text-slate-500">{s.detail}</div>
          </li>
        ))}
      </ol>
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          {[["Raw records", c.rows_raw], ["After cleaning", c.rows_clean],
            ["With disease", c.class_counts.positive], ["Healthy", c.class_counts.negative]].map(([k, v]) => (
            <div key={k} className="rounded-xl bg-slate-50 px-3 py-2">
              <div className="text-[10px] font-medium uppercase tracking-wide text-slate-400">{k}</div>
              <div className="text-lg font-bold tabular-nums text-slate-800">{v}</div>
            </div>
          ))}
        </div>
        {missing.length > 0 && (
          <div className="rounded-xl bg-slate-50 p-3">
            <div className="mb-2 text-[10px] font-medium uppercase tracking-wide text-slate-400">Missing values imputed</div>
            {missing.map(([k, v]) => (
              <div key={k} className="mb-1.5 text-xs">
                <div className="flex justify-between text-slate-600"><span>{k}</span><span className="tabular-nums">{v} ({pct(v / c.rows_clean, 0)})</span></div>
                <div className="mt-0.5 h-1.5 rounded-full bg-slate-200">
                  <div className="h-1.5 rounded-full bg-amber-400" style={{ width: `${(v / c.rows_clean) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
