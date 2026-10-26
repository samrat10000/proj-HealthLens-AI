import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, ArrowRight, Brain, Droplet, FileSpreadsheet, FlaskConical, HeartPulse, ShieldCheck, UserRound,
} from "lucide-react";
import {
  api, type BatchResult, type DiseaseDetail, type DiseaseId, type DiseaseSummary, type Prediction, type Values,
} from "./api";
import { defaults, fieldError } from "./lib";
import BatchScreening from "./components/BatchScreening";
import ModelInsights from "./components/ModelInsights";
import PatientForm from "./components/PatientForm";
import ResultPanel from "./components/ResultPanel";

const ICONS: Record<DiseaseId, typeof HeartPulse> = { heart: HeartPulse, diabetes: Droplet, liver: FlaskConical };
type Mode = "upload" | "single";

// Deep links, e.g. ?mode=single&disease=diabetes
const params = new URLSearchParams(window.location.search);
const initialDisease = (["heart", "diabetes", "liver"] as DiseaseId[]).find(
  (d) => d === (params.get("disease") ?? params.get("demo"))) ?? "heart";

export default function App() {
  const [diseases, setDiseases] = useState<DiseaseSummary[]>([]);
  const [active, setActive] = useState<DiseaseId>(initialDisease);
  const [mode, setMode] = useState<Mode>(params.get("mode") === "single" ? "single" : "upload");
  const [details, setDetails] = useState<Partial<Record<DiseaseId, DiseaseDetail>>>({});
  const [form, setForm] = useState<{ id: DiseaseId; values: Values } | null>(null);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [batchResult, setBatchResult] = useState<BatchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const workspace = useRef<HTMLDivElement>(null);
  const pendingValues = useRef<Values | null>(null);

  const detail = details[active];

  useEffect(() => {
    api.diseases().then(setDiseases).catch(() => setOffline(true));
  }, []);

  useEffect(() => {
    const preset = pendingValues.current ?? {};
    pendingValues.current = null;
    const cached = details[active];
    if (cached) {
      setForm({ id: active, values: { ...defaults(cached.features), ...preset } });
      return;
    }
    api.disease(active)
      .then((d) => {
        setDetails((prev) => ({ ...prev, [active]: d }));
        setForm({ id: active, values: { ...defaults(d.features), ...preset } });
      })
      .catch(() => setOffline(true));
  }, [active]);

  const invalid = useMemo(() => {
    if (!detail || !form || form.id !== detail.id) return [];
    return detail.features.filter((f) => fieldError(f, form.values[f.key] ?? null)).map((f) => f.label);
  }, [detail, form]);

  // Real-time inference: debounce edits, cancel stale requests.
  useEffect(() => {
    if (mode !== "single" || !detail || !form || form.id !== detail.id) return;
    if (invalid.length) {
      setError(`Fix ${invalid.join(", ")} to update the prediction.`);
      return;
    }
    const ctrl = new AbortController();
    const t = setTimeout(() => {
      setLoading(true);
      api.predict(form.id, form.values, ctrl.signal)
        .then((p) => { setPrediction(p); setError(null); })
        .catch((e) => { if (e.name !== "AbortError") setError(e.message); })
        .finally(() => setLoading(false));
    }, 180);
    return () => { clearTimeout(t); ctrl.abort(); };
  }, [form, detail, invalid, mode]);

  const scrollToWorkspace = () => workspace.current?.scrollIntoView({ behavior: "smooth", block: "start" });

  const switchDisease = (id: DiseaseId) => {
    if (id !== active) { setPrediction(null); setError(null); setActive(id); }
  };

  const openPatient = (id: DiseaseId, values: Values) => {
    setMode("single");
    if (id === active && details[id]) {
      setForm({ id, values: { ...defaults(details[id]!.features), ...values } });
    } else {
      pendingValues.current = values;
      switchDisease(id);
    }
    scrollToWorkspace();
  };

  const totalPatients = diseases.reduce((s, d) => s + d.n_patients, 0);
  const shownPrediction = prediction?.disease === active ? prediction : null;

  return (
    <div className="min-h-screen">
      {/* ---------- hero ---------- */}
      <header className="hero-grid no-print relative overflow-hidden bg-ink-900 text-white">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-4 py-5 sm:px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-sky-500 shadow-lg shadow-brand-500/30">
              <Activity className="h-5 w-5" strokeWidth={2.5} />
            </div>
            <span className="text-lg font-bold tracking-tight">HealthLens<span className="text-brand-200"> AI</span></span>
          </div>
          <div className="flex items-center gap-2 rounded-full bg-white/5 px-3 py-1.5 text-xs text-slate-300 ring-1 ring-white/10">
            <span className={`h-2 w-2 rounded-full ${offline ? "bg-red-400" : "bg-emerald-400"}`} />
            {offline ? "API offline" : "Models online"}
          </div>
        </nav>

        <div className="mx-auto max-w-7xl px-4 pt-10 pb-28 sm:px-6 lg:pt-16">
          <div className="max-w-3xl">
            <span className="inline-flex items-center gap-2 rounded-full bg-brand-500/10 px-3 py-1 text-xs font-medium text-brand-200 ring-1 ring-brand-500/30">
              <Brain className="h-3.5 w-3.5" /> Machine-learning clinical decision support
            </span>
            <h1 className="mt-5 text-4xl font-extrabold leading-[1.1] tracking-tight sm:text-5xl lg:text-6xl">
              AI Health Diagnostic{" "}
              <span className="bg-gradient-to-r from-brand-200 via-brand-500 to-sky-400 bg-clip-text text-transparent">Assistant</span>
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-relaxed text-slate-300">
              Upload a CSV or Excel file of patients and get an instant, explainable risk screening for heart disease,
              diabetes and liver disorders, or assess a single patient by hand.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <button onClick={() => { setMode("upload"); scrollToWorkspace(); }}
                      className="inline-flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-3 font-semibold text-white shadow-lg shadow-brand-500/30 transition hover:bg-brand-600">
                <FileSpreadsheet className="h-4 w-4" /> Upload patient file <ArrowRight className="h-4 w-4" />
              </button>
              <button onClick={() => { setMode("single"); scrollToWorkspace(); }}
                      className="inline-flex items-center gap-2 rounded-xl bg-white/10 px-5 py-3 font-semibold text-white ring-1 ring-white/15 transition hover:bg-white/15">
                <UserRound className="h-4 w-4" /> Assess one patient
              </button>
            </div>
            <p className="mt-4 flex items-center gap-1.5 text-sm text-slate-400">
              <ShieldCheck className="h-4 w-4 text-brand-200" /> Runs locally. Uploaded files are never stored.
            </p>
          </div>

          <dl className="mt-14 grid max-w-3xl grid-cols-2 gap-6 sm:grid-cols-4">
            {[["3", "Disease models"], [totalPatients ? totalPatients.toLocaleString() : "—", "Training patients"],
              ["8", "Algorithms compared"], ["5,000", "Patients per upload"]].map(([v, k]) => (
              <div key={k} className="border-l border-white/10 pl-4">
                <dt className="text-xs text-slate-400">{k}</dt>
                <dd className="mt-1 text-2xl font-bold tabular-nums">{v}</dd>
              </div>
            ))}
          </dl>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 sm:px-6">
        {/* ---------- disease picker ---------- */}
        <div className="no-print relative -mt-16 grid gap-4 md:grid-cols-3">
          {(diseases.length ? diseases : (["heart", "diabetes", "liver"] as DiseaseId[]).map((id) => ({ id } as DiseaseSummary)))
            .map((d) => {
              const Icon = ICONS[d.id];
              const on = d.id === active;
              return (
                <button key={d.id} onClick={() => switchDisease(d.id)}
                        className={`card group p-5 text-left transition hover:-translate-y-0.5 ${on ? "ring-2 ring-brand-500" : "hover:ring-1 hover:ring-slate-300"}`}>
                  <div className="flex items-start justify-between">
                    <div className={`flex h-11 w-11 items-center justify-center rounded-xl transition ${on ? "bg-brand-600 text-white" : "bg-brand-50 text-brand-600"}`}>
                      <Icon className="h-5 w-5" />
                    </div>
                    {d.roc_auc && (
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold tabular-nums text-slate-600">
                        AUC {d.roc_auc.toFixed(2)}
                      </span>
                    )}
                  </div>
                  <h3 className="mt-4 font-semibold text-slate-900">{d.name ?? "Loading…"}</h3>
                  <p className="mt-1 text-sm text-slate-500">{d.tagline}</p>
                  {d.dataset && (
                    <p className="mt-3 border-t border-slate-100 pt-3 text-[11px] text-slate-400">
                      {d.n_patients} patients · {d.dataset}
                    </p>
                  )}
                </button>
              );
            })}
        </div>

        {offline && (
          <div className="card mt-8 border-red-200 bg-red-50 p-5 text-sm text-red-700">
            Cannot reach the prediction API. Start the backend with{" "}
            <code className="rounded bg-white px-1.5 py-0.5">uvicorn app.main:app --port 8000</code> from the backend folder.
          </div>
        )}

        {/* ---------- workspace ---------- */}
        <div ref={workspace} className="scroll-mt-6 pt-10">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-slate-900">
                {mode === "upload" ? "Screen a patient file" : `${detail?.name ?? ""} risk assessment`}
              </h2>
              <p className="text-sm text-slate-500">
                {mode === "upload"
                  ? "Every row is checked, scored and explained. The disease type is detected from the columns."
                  : detail?.tagline}
              </p>
            </div>
            <div className="no-print flex rounded-xl bg-slate-200/70 p-1">
              {([["upload", "Upload file", FileSpreadsheet], ["single", "Single patient", UserRound]] as const).map(([m, label, Icon]) => (
                <button key={m} onClick={() => setMode(m)}
                        className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-sm font-medium transition ${
                          mode === m ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"}`}>
                  <Icon className="h-4 w-4" /> {label}
                </button>
              ))}
            </div>
          </div>

          {mode === "upload" && (
            <BatchScreening
              result={batchResult}
              onResult={(r) => { setBatchResult(r); if (r) switchDisease(r.disease); }}
              onOpenPatient={openPatient}
            />
          )}

          {mode === "single" && detail && form && form.id === detail.id && (
            <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_400px]">
              <PatientForm
                detail={detail}
                values={form.values}
                onChange={(k, v) => setForm((f) => f && { ...f, values: { ...f.values, [k]: v } })}
                onLoad={(vals) => setForm({ id: detail.id, values: { ...defaults(detail.features), ...vals } })}
                onReset={() => setForm({ id: detail.id, values: defaults(detail.features) })}
              />
              <div className="lg:sticky lg:top-6">
                <ResultPanel detail={detail} prediction={shownPrediction} loading={loading} error={error} />
              </div>
            </div>
          )}

          {detail && (
            <div className="mt-8">
              <ModelInsights detail={detail} />
            </div>
          )}
        </div>
      </main>

      <footer className="no-print mx-auto mt-16 max-w-7xl border-t border-slate-200 px-4 py-8 text-xs text-slate-400 sm:px-6">
        <div className="flex flex-wrap justify-between gap-4">
          <span>HealthLens AI · React + FastAPI + scikit-learn</span>
          <span>For educational and research use only. Not a substitute for professional medical advice.</span>
        </div>
      </footer>
    </div>
  );
}
