"""HealthLens AI web app, written entirely in Python with Streamlit.

Run (from backend/):  streamlit run healthlens.py
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import service
from app.batch import norm
from ml import samples
from ml.specs import DISEASES, RISK_BANDS

st.set_page_config(page_title="HealthLens AI", page_icon=":material/stethoscope:", layout="wide")

RISK_STYLE = {
    "low": {"label": "Low risk", "color": "#10b981", "icon": ":material/check_circle:"},
    "moderate": {"label": "Moderate risk", "color": "#f59e0b", "icon": ":material/error:"},
    "high": {"label": "High risk", "color": "#ef4444", "icon": ":material/warning:"},
}
ICONS = {"heart": ":material/cardiology:", "diabetes": ":material/water_drop:", "liver": ":material/science:"}
BRAND = "#0d9488"
MODES = {"upload": ":material/upload_file: Upload file", "single": ":material/person: Single patient"}


def pct(v: float, digits: int = 1) -> str:
    return f"{v * 100:.{digits}f}%"


# ------------------------------------------------------------------ state

def field_key(disease: str, key: str) -> str:
    return f"{disease}.{key}"


def na_key(disease: str, key: str) -> str:
    return f"{disease}.{key}.na"


def to_input(f: dict, v):
    """Coerce a stored number to the type its widget expects (int slider, float slider or option value)."""
    if f["input"] == "select":
        return next((o["value"] for o in f["options"] if o["value"] == v), f["default"])
    v = min(max(v, f["min"]), f["max"])
    return float(v) if f["step"] < 1 else int(round(v))


def load_values(disease: str, values: dict | None = None):
    """Put a patient's values (or the defaults) into the form widgets."""
    values = values or {}
    for f in DISEASES[disease]["features"]:
        v = values.get(f["key"], f["default"])
        missing = v is None or pd.isna(v)
        st.session_state[field_key(disease, f["key"])] = to_input(f, f["default"] if missing else v)
        st.session_state[na_key(disease, f["key"])] = missing and bool(f.get("optional"))


def form_values(disease: str) -> dict:
    return {f["key"]: None if st.session_state.get(na_key(disease, f["key"]))
            else st.session_state[field_key(disease, f["key"])]
            for f in DISEASES[disease]["features"]}


def open_patient(disease: str, values: dict):
    st.session_state.disease = disease
    st.session_state.mode = "single"
    load_values(disease, values)


def run_upload(filename: str, content: bytes):
    try:
        result = service.predict_file(filename, content)
    except service.InputError as e:
        st.session_state.upload_error = str(e)
        return
    st.session_state.upload_error = None
    st.session_state.batch = result
    st.session_state.disease = result["disease"]


def on_file_chosen():
    file = st.session_state.get("uploader")
    if file is not None:
        run_upload(file.name, file.getvalue())


def run_demo(disease: str):
    run_upload(f"{disease}_patients.csv", sample_bytes(disease, "csv"))


@st.cache_data(show_spinner=False)
def sample_bytes(disease: str, fmt: str) -> bytes:
    return samples.to_bytes(samples.sample(disease), fmt)


@st.cache_data(show_spinner=False)
def template_bytes(disease: str, fmt: str) -> bytes:
    return samples.to_bytes(samples.template(disease), fmt)


def init_state():
    if "mode" in st.session_state:
        return
    # Deep links, e.g. ?mode=single&disease=diabetes  or  ?demo=heart
    q = st.query_params
    demo = q.get("demo") if q.get("demo") in DISEASES else None
    st.session_state.mode = "single" if q.get("mode") == "single" else "upload"
    st.session_state.disease = q.get("disease") if q.get("disease") in DISEASES else demo or "heart"
    st.session_state.batch = None
    st.session_state.upload_error = None
    for d in DISEASES:
        load_values(d)
    if demo:
        run_demo(demo)


# ------------------------------------------------------------------ header

def header(summaries: list[dict]):
    st.markdown("### :material/stethoscope: HealthLens **AI**")
    st.title("AI Health Diagnostic Assistant")
    st.markdown(
        "Upload a CSV or Excel file of patients and get an instant, explainable risk screening for heart disease, "
        "diabetes and liver disorders, or assess a single patient by hand.  \n"
        ":material/verified_user: *Runs locally. Uploaded files are never stored.*")
    cols = st.columns(4)
    for col, (label, value) in zip(cols, [
        ("Disease models", "3"),
        ("Training patients", f"{sum(d['n_patients'] for d in summaries):,}"),
        ("Algorithms compared", "8"),
        ("Patients per upload", "5,000"),
    ]):
        col.metric(label, value)

    st.radio("Disease", list(DISEASES), key="disease", horizontal=True,
             format_func=lambda d: f"{ICONS[d]} {DISEASES[d]['name']}", label_visibility="collapsed")
    cols = st.columns(3)
    for col, d in zip(cols, summaries):
        with col.container(border=True):
            active = " :material/check_circle:" if d["id"] == st.session_state.disease else ""
            st.markdown(f"**{ICONS[d['id']]} {d['name']}**{active} &nbsp; `AUC {d['roc_auc']:.2f}`")
            st.caption(d["tagline"])
            st.caption(f"{d['n_patients']} patients · {d['dataset']}")


# ------------------------------------------------------------------ upload mode

def upload_view():
    result = st.session_state.batch
    if result is None:
        upload_panel()
    else:
        with st.expander("Upload another file", icon=":material/upload_file:"):
            upload_panel()
        batch_results(result)


def upload_panel():
    left, right = st.columns([2, 1], gap="large")
    with left, st.container(border=True):
        st.file_uploader(
            "Drop a patient file here or browse", type=["csv", "xlsx", "xls", "xlsm"], key="uploader",
            on_change=on_file_chosen,
            help="CSV or Excel (.xlsx) · one patient per row · up to 5,000 rows")
        st.caption(":material/check: Disease detected automatically &nbsp; :material/check: Kaggle column names accepted &nbsp; "
                   ":material/check: Blank cells are estimated")
        st.markdown("**No file handy?** Try it with 40 real patients:")
        cols = st.columns(3)
        for col, d in zip(cols, DISEASES):
            col.button(f"{ICONS[d]} {DISEASES[d]['name']}", key=f"demo_{d}", on_click=run_demo, args=(d,),
                       width="stretch")
        if st.session_state.upload_error:
            st.error(st.session_state.upload_error, icon=":material/warning:")
    with right, st.container(border=True):
        file_library()


def file_library():
    st.markdown("#### :material/description: Need a file?")
    st.caption("**Sample patients** are 40 real records with their recorded diagnosis. "
               "A **template** has the right columns for your own data.")
    for d in DISEASES:
        st.markdown(f"**{ICONS[d]} {DISEASES[d]['name']}**")
        c1, c2, c3 = st.columns(3)
        c1.download_button("Sample CSV", sample_bytes(d, "csv"), f"{d}_patients.csv", "text/csv",
                           key=f"dl_s_csv_{d}", width="stretch")
        c2.download_button("Sample Excel", sample_bytes(d, "xlsx"), f"{d}_patients.xlsx",
                           key=f"dl_s_xlsx_{d}", width="stretch")
        c3.download_button("Template", template_bytes(d, "csv"), f"{d}_template.csv", "text/csv",
                           key=f"dl_t_{d}", width="stretch")


def batch_results(result: dict):
    s = result["summary"]
    has_actual = s["labelled"] > 0

    with st.container(border=True):
        top, actions = st.columns([3, 1])
        top.markdown(f"#### :material/description: {result['filename']}")
        top.caption(f"{'Detected' if result['auto_detected'] else 'Screened as'} **{result['disease_name']}** data · "
                    f"{s['scored']} patients scored in {result['elapsed_ms'] / 1000:.2f} s · {result['model']}")
        name = result["filename"].rsplit(".", 1)[0]
        actions.download_button("Download results", samples.to_bytes(service.results_table(result), "csv"),
                                f"{name}_results.csv", "text/csv", icon=":material/download:", type="primary",
                                width="stretch")
        actions.button("Back to upload", icon=":material/restart_alt:",
                       on_click=lambda: st.session_state.update(batch=None), width="stretch")

        tiles = [("Patients screened", str(s["scored"]), f"of {s['total']} rows")]
        for level in ("high", "moderate", "low"):
            tiles.append((RISK_STYLE[level]["icon"] + " " + RISK_STYLE[level]["label"], str(s[level]),
                          pct(s[level] / s["scored"], 0) if s["scored"] else ""))
        if has_actual:
            tiles.append(("Matches recorded diagnosis", pct(s["agreement"] or 0, 0), f"{s['labelled']} labelled"))
        if s["errors"]:
            tiles.append(("Rows needing fixes", str(s["errors"]), ""))
        for col, (label, value, sub) in zip(st.columns(len(tiles)), tiles):
            col.metric(label, value, sub or None, delta_color="off")

        if s["scored"]:
            st.plotly_chart(risk_bar(s), width="stretch", config={"displayModeBar": False})

        cols = result["columns"]
        ignored = f", {len(cols['ignored'])} ignored" if cols["ignored"] else ""
        with st.expander(f"How your columns were read ({len(cols['recognised'])} recognised{ignored})"):
            lines = [f"- :green[:material/check_circle:] `{c['column']}`" + ("" if norm(c["column"]) == norm(c["feature"])
                                               else f" → {c['feature']}") for c in cols["recognised"]]
            if cols["id_column"]:
                lines.append(f"- :blue[:material/badge:] `{cols['id_column']}` → patient ID")
            if cols["target_column"]:
                lines.append(f"- :blue[:material/label:] `{cols['target_column']}` → recorded diagnosis")
            lines += [f"- ~~`{c}`~~ ignored" for c in cols["ignored"]]
            lines += [f"- :orange[:material/warning:] {c}: not in file, estimated" for c in cols["not_provided"]]
            st.markdown("\n".join(lines))

    patient_table(result, has_actual)


def risk_bar(s: dict) -> go.Figure:
    fig = go.Figure()
    for level in ("low", "moderate", "high"):
        if s[level]:
            st_ = RISK_STYLE[level]
            fig.add_bar(y=[""], x=[s[level]], orientation="h", name=f"{st_['label']} · {s[level]}",
                        marker_color=st_["color"],
                        hovertemplate=f"{st_['label']}: {s[level]} patients ({pct(s[level] / s['scored'], 0)})"
                                      "<extra></extra>")
    fig.update_layout(barmode="stack", height=90, margin=dict(l=0, r=0, t=0, b=0), showlegend=True,
                      legend=dict(orientation="h", y=-0.4), xaxis=dict(visible=False), yaxis=dict(visible=False),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def patient_table(result: dict, has_actual: bool):
    s = result["summary"]
    filters = {"all": ("All", s["total"]), "high": ("High", s["high"]), "moderate": ("Moderate", s["moderate"]),
               "low": ("Low", s["low"]), "errors": ("Errors", s["errors"])}
    filters = {k: v for k, v in filters.items() if k == "all" or v[1] > 0}

    c1, c2, c3 = st.columns([3, 1.3, 1])
    flt = c1.radio("Show", list(filters), horizontal=True, key="batch_filter",
                   format_func=lambda k: f"{filters[k][0]} ({filters[k][1]})")
    query = c2.text_input("Find patient ID", placeholder="Find patient ID", icon=":material/search:",
                          label_visibility="collapsed")
    by_risk = c3.toggle("Highest risk first", value=True)

    rows = [r for r in result["rows"]
            if flt == "all" or (r["errors"] if flt == "errors" else r.get("risk_level") == flt)]
    if query.strip():
        rows = [r for r in rows if query.strip().lower() in r["patient_id"].lower()]
    if by_risk:
        rows = sorted(rows, key=lambda r: r.get("probability", -1), reverse=True)

    if not rows:
        st.info("No patients match this filter.")
        return

    table = []
    for r in rows:
        if r["errors"]:
            table.append({"Patient": r["patient_id"], "Row": r["row"], "Risk": None, "Level": "Not scored",
                          "Result": "", "Main reasons": "Not scored: " + " · ".join(r["errors"]), "Recorded": ""})
            continue
        st_ = RISK_STYLE[r["risk_level"]]
        reasons = ", ".join(f"{f['label']}: {f['display']}" for f in r["top_factors"]) or "No strong risk factors"
        recorded = "" if r["actual"] is None else \
            ("Disease" if r["actual"] else "Healthy") + (" (agrees)" if r["actual"] == r["predicted"] else " (differs)")
        table.append({"Patient": r["patient_id"] + (f" · {len(r['imputed'])} estimated" if r["imputed"] else ""),
                      "Row": r["row"], "Risk": r["probability"] * 100, "Level": st_["label"],
                      "Result": r["prediction"], "Main reasons": reasons, "Recorded": recorded})
    df = pd.DataFrame(table)
    if not has_actual:
        df = df.drop(columns="Recorded")

    level_colors = {s["label"]: s["color"] for s in RISK_STYLE.values()} | {"Not scored": "#ef4444"}
    styled = df.style.map(lambda v: f"color: {level_colors.get(v, 'inherit')}; font-weight: 600", subset=["Level"])

    st.caption("Select a row to open that patient in the single-patient view.")
    event = st.dataframe(
        styled, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
        key=f"table_{result['filename']}_{flt}",
        column_config={
            "Risk": st.column_config.ProgressColumn("Risk", min_value=0, max_value=100, format="%.0f%%"),
            "Row": st.column_config.NumberColumn("Row", width="small"),
            "Main reasons": st.column_config.TextColumn("Main reasons", width="large"),
        })
    picked = event.selection.rows
    if picked:
        row = rows[picked[0]]
        if row["errors"]:
            st.warning(f"{row['patient_id']} could not be scored: " + " · ".join(row["errors"]))
        else:
            st.button(f"Open {row['patient_id']} in single-patient view", type="primary",
                      icon=":material/arrow_forward:", on_click=open_patient,
                      args=(result["disease"], row["values"]))


# ------------------------------------------------------------------ single-patient mode

def single_view(disease: str):
    spec = DISEASES[disease]
    left, right = st.columns([3, 2], gap="large")
    with left, st.container(border=True):
        patient_form(disease)
    with right:
        try:
            prediction = service.predict(disease, form_values(disease))
        except service.InputError as e:
            st.warning(f"Fix these values to update the prediction: {e}", icon=":material/warning:")
            return
        result_panel(spec, prediction)


def patient_form(disease: str):
    spec, m = DISEASES[disease], service.meta(disease)
    head, reset = st.columns([4, 1])
    head.markdown("#### Patient parameters")
    head.caption("Results update live as you edit.")
    reset.button("Reset", icon=":material/restart_alt:", on_click=load_values, args=(disease,), key=f"reset_{disease}")

    st.caption("**TRY A REAL PATIENT:**")
    cols = st.columns(len(m["samples"]))
    for col, smp in zip(cols, m["samples"]):
        col.button(smp["label"], icon=":material/person:", on_click=load_values, args=(disease, smp["values"]),
                   key=f"smp_{disease}_{smp['label']}", width="stretch")

    groups: dict[str, list[dict]] = {}
    for f in spec["features"]:
        groups.setdefault(f["group"], []).append(f)
    for group, feats in groups.items():
        st.markdown(f"**:green[{group.upper()}]**")
        cols = st.columns(2, gap="medium")
        for i, f in enumerate(feats):
            with cols[i % 2]:
                field(disease, f)


def field(disease: str, f: dict):
    unknown = st.session_state.get(na_key(disease, f["key"]), False)
    label = f["label"] + (f" ({f['unit']})" if f.get("unit") and f["input"] == "number" else "")
    if f["input"] == "select":
        opts = [o["value"] for o in f["options"]]
        names = {o["value"]: o["label"] for o in f["options"]}
        compact = len(opts) <= 4 and all(len(o["label"]) <= 12 for o in f["options"])
        widget = st.radio if compact else st.selectbox
        kwargs = {"horizontal": True} if compact else {}
        widget(label, opts, key=field_key(disease, f["key"]), format_func=names.get, disabled=unknown,
               help=f.get("help"), **kwargs)
    else:
        st.slider(label, min_value=to_input(f, f["min"]), max_value=to_input(f, f["max"]),
                  step=float(f["step"]) if f["step"] < 1 else int(f["step"]),
                  key=field_key(disease, f["key"]), disabled=unknown, help=f.get("help"))
    if f.get("optional"):
        st.checkbox("Not measured", key=na_key(disease, f["key"]))

    notes = []
    if unknown:
        notes.append("Will be estimated by the model")
    elif f.get("normal"):
        v = st.session_state[field_key(disease, f["key"])]
        lo, hi = f["normal"]
        if lo is not None and v < lo:
            notes.append(":orange[:material/arrow_downward: Below normal range]")
        elif hi is not None and v > hi:
            notes.append(":red[:material/arrow_upward: Above normal range]")
    if f.get("normal"):
        notes.append(f"Normal {service.range_text(f)}")
    if notes:
        st.caption(" · ".join(notes))


def result_panel(spec: dict, p: dict):
    style = RISK_STYLE[p["risk_level"]]
    with st.container(border=True):
        st.markdown("#### :material/monitor_heart: Diagnostic result")
        st.caption(f":material/bolt: {p['latency_ms']} ms")
        st.plotly_chart(gauge(p["probability"], style["color"]), width="stretch",
                        config={"displayModeBar": False})
        st.markdown(
            f"<div style='text-align:center;margin-top:-1.5rem'>"
            f"<div style='font-size:3rem;font-weight:800'>{pct(p['probability'], 0)}</div>"
            f"<div style='opacity:.7'>probability of {spec['positive_label'].lower()}</div>"
            f"<div style='margin-top:.5rem;font-weight:600;color:{style['color']}'>{style['label']}</div>"
            f"</div>", unsafe_allow_html=True)
        {"low": st.success, "moderate": st.warning, "high": st.error}[p["risk_level"]](
            p["advice"], icon=":material/stethoscope:")

        st.markdown("##### What's driving this result")
        st.caption("Change in risk vs. a typical healthy patient's value. :red[Red raises], :green[green lowers] risk.")
        contributions(p["contributions"])

        if p["flags"]:
            st.markdown("##### Outside clinical reference range")
            for fl in p["flags"]:
                tag = ":red[**HIGH**]" if fl["status"] == "high" else ":orange[**LOW**]"
                st.markdown(f"{tag} {fl['label']}: **{fl['value']}** / {fl['range']}")

        imputed = f" · Estimated (not measured): {', '.join(p['imputed'])}" if p["imputed"] else ""
        st.caption(f":material/info: Model: {p['model']}{imputed}. Educational decision-support only — not a medical diagnosis.")


def gauge(probability: float, color: str) -> go.Figure:
    cuts = [0, *[b[0] for b in RISK_BANDS[:-1]], 1]
    band_colors = ["rgba(16,185,129,.18)", "rgba(245,158,11,.18)", "rgba(239,68,68,.18)"]
    fig = go.Figure(go.Indicator(
        mode="gauge", value=probability * 100,
        gauge={"axis": {"range": [0, 100], "ticksuffix": "%", "tickvals": [0, 30, 60, 100]},
               "bar": {"color": color, "thickness": 0.35},
               "steps": [{"range": [cuts[i] * 100, cuts[i + 1] * 100], "color": band_colors[i]} for i in range(3)],
               "borderwidth": 0}))
    fig.update_layout(height=200, margin=dict(l=30, r=30, t=20, b=0), paper_bgcolor="rgba(0,0,0,0)")
    return fig


def contributions(items: list[dict]):
    top = [c for c in items if abs(c["impact"]) >= 0.002][:7]
    if not top:
        st.caption("All values match the typical healthy patient profile.")
        return
    top = top[::-1]  # plotly draws the first bar at the bottom
    fig = go.Figure(go.Bar(
        x=[c["impact"] * 100 for c in top],
        y=[f"{c['label']} · {c['display']}" for c in top],
        orientation="h",
        marker_color=["#f87171" if c["impact"] > 0 else "#34d399" for c in top],
        text=[f"{'+' if c['impact'] > 0 else '−'}{abs(c['impact'] * 100):.1f} pts" for c in top],
        textposition="outside", cliponaxis=False,
        customdata=[c["baseline_display"] for c in top],
        hovertemplate="%{y}<br>%{x:+.1f} pts<br>Typical healthy value: %{customdata}<extra></extra>"))
    lim = max(max(abs(c["impact"] * 100) for c in top), 5) * 1.35
    fig.update_layout(height=60 + 34 * len(top), margin=dict(l=0, r=10, t=0, b=0),
                      xaxis=dict(range=[-lim, lim], zeroline=True, zerolinecolor="#94a3b8", title="pts"),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ------------------------------------------------------------------ model insights

def model_insights(disease: str):
    spec, m = DISEASES[disease], service.meta(disease)
    with st.container(border=True):
        st.markdown(f"### Under the hood: {spec['name']} model")
        st.caption(f"{len(m['leaderboard'])} algorithms compared with {m['cv_folds']}-fold stratified "
                   f"cross-validation · trained {m['trained_at']}")
        h = m["holdout"]
        for col, (k, v) in zip(st.columns(5), [("Accuracy", h["accuracy"]), ("ROC-AUC", h["roc_auc"]),
                                               ("F1", h["f1"]), ("Precision", h["precision"]),
                                               ("Recall", h["recall"])]):
            col.metric(k, f"{v:.3f}")

        tabs = st.tabs([":material/trophy: Model comparison", ":material/show_chart: ROC curve",
                        ":material/grid_view: Confusion matrix", ":material/bar_chart: Feature importance",
                        ":material/database: Data pipeline"])
        with tabs[0]:
            leaderboard(m)
        with tabs[1]:
            roc(m)
        with tabs[2]:
            confusion(spec, m)
        with tabs[3]:
            importance(m)
        with tabs[4]:
            pipeline(m)
        st.caption(f"Headline metrics are measured on a stratified 20% hold-out set ({h['n_test']} patients) never "
                   "seen during model selection. The deployed model is then refit on all data.")


def leaderboard(m: dict):
    rows = m["leaderboard"]
    df = pd.DataFrame([{
        "#": i + 1,
        "Algorithm": r["model"] + (" — DEPLOYED" if i == 0 else "")
                     + (f" (blend of {' + '.join(r['members'])})" if r.get("members") else ""),
        "CV ROC-AUC": r["roc_auc"], "± std": r["roc_auc_std"], "Accuracy": r["accuracy"], "F1": r["f1"],
        "Precision": r["precision"], "Recall": r["recall"], "Time (s)": r["train_time_s"],
    } for i, r in enumerate(rows)])
    lo = min(r["roc_auc"] for r in rows) - 0.03
    hi = max(r["roc_auc"] for r in rows)
    st.dataframe(df, hide_index=True, width="stretch", column_config={
        "CV ROC-AUC": st.column_config.ProgressColumn("CV ROC-AUC", min_value=lo, max_value=hi, format="%.3f"),
        **{c: st.column_config.NumberColumn(c, format="%.3f") for c in ("± std", "Accuracy", "F1", "Precision",
                                                                         "Recall")},
        "Time (s)": st.column_config.NumberColumn("Time (s)", format="%.1f"),
    })
    st.caption("Bars are scaled to the range of scores, so small differences are visible.")


def roc(m: dict):
    pts = m["holdout"]["roc_curve"]
    chart, side = st.columns([3, 1])
    fig = go.Figure()
    fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color="#cbd5e1", dash="dash"), name="Chance",
                    hoverinfo="skip")
    fig.add_scatter(x=[p["fpr"] for p in pts], y=[p["tpr"] for p in pts], mode="lines", line_shape="hv",
                    line=dict(color=BRAND, width=2), fill="tozeroy", fillcolor="rgba(20,184,166,.15)",
                    name="Model", hovertemplate="FPR %{x:.3f}<br>TPR %{y:.3f}<extra></extra>")
    fig.update_layout(height=320, margin=dict(l=0, r=10, t=10, b=0), showlegend=False,
                      xaxis=dict(title="False positive rate", range=[0, 1]),
                      yaxis=dict(title="True positive rate", range=[0, 1.02]),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    chart.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with side:
        st.metric("Area under curve", f"{m['holdout']['roc_auc']:.3f}")
        st.caption("The probability the model ranks a random sick patient above a random healthy one. "
                   "0.5 is a coin flip (dashed line), 1.0 is perfect.")


def confusion(spec: dict, m: dict):
    (tn, fp), (fn, tp) = m["holdout"]["confusion_matrix"]
    chart, side = st.columns([3, 2])
    labels = [["True negative", "False positive"], ["False negative", "True positive"]]
    z = [[tn, fp], [fn, tp]]
    fig = go.Figure(go.Heatmap(
        z=z, x=[f"Predicted: {spec['negative_label']}", f"Predicted: {spec['positive_label']}"],
        y=["Actual: healthy", "Actual: disease"], colorscale=[[0, "#f0fdfa"], [1, BRAND]], showscale=False,
        text=[[f"<b>{z[i][j]}</b><br>{labels[i][j]}" for j in range(2)] for i in range(2)],
        texttemplate="%{text}", textfont=dict(size=15), hovertemplate="%{text}<extra></extra>"))
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), yaxis=dict(autorange="reversed"))
    chart.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    total = tn + fp + fn + tp
    with side:
        for k, v in [("Sensitivity (recall)", tp / (tp + fn)), ("Specificity", tn / (tn + fp)),
                     ("Positive predictive value", tp / (tp + fp)), ("Overall accuracy", (tp + tn) / total)]:
            st.metric(k, pct(v))


def importance(m: dict):
    rows = m["feature_importance"][::-1]
    st.caption("Permutation importance: how much ROC-AUC drops when a feature is shuffled.")
    fig = go.Figure(go.Bar(x=[r["importance"] for r in rows], y=[r["label"] for r in rows], orientation="h",
                           marker_color=BRAND, hovertemplate="%{y}: AUC drop %{x:.4f}<extra></extra>"))
    fig.update_layout(height=40 + 28 * len(rows), margin=dict(l=0, r=10, t=0, b=0),
                      xaxis=dict(title="ROC-AUC drop"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def pipeline(m: dict):
    c = m["cleaning"]
    steps, side = st.columns([3, 2], gap="large")
    steps.markdown("\n".join(f"{i}. **{s['action']}**  \n   {s['detail']}" for i, s in enumerate(c["steps"], 1)))
    with side:
        a, b = st.columns(2)
        a.metric("Raw records", c["rows_raw"])
        b.metric("After cleaning", c["rows_clean"])
        a.metric("With disease", c["class_counts"]["positive"])
        b.metric("Healthy", c["class_counts"]["negative"])
        if c["missing_after_cleaning"]:
            st.caption("**MISSING VALUES IMPUTED**")
            for k, v in c["missing_after_cleaning"].items():
                st.progress(min(v / c["rows_clean"], 1.0), text=f"{k}: {v} ({pct(v / c['rows_clean'], 0)})")


# ------------------------------------------------------------------ page

def main():
    if not service.models_ready():
        st.error("The AI models are not trained yet. Run **setup.bat** (Windows) or `bash setup.sh` first.")
        st.stop()
    init_state()
    header(service.disease_summaries())
    st.divider()

    disease = st.session_state.disease
    mode = st.radio("Mode", list(MODES), key="mode", horizontal=True, format_func=MODES.get,
                    label_visibility="collapsed")
    if mode == "upload":
        st.header("Screen a patient file")
        st.caption("Every row is checked, scored and explained. The disease type is detected from the columns.")
        upload_view()
    else:
        st.header(f"{DISEASES[disease]['name']} risk assessment")
        st.caption(DISEASES[disease]["tagline"])
        single_view(disease)

    st.write("")
    model_insights(disease)
    st.divider()
    st.caption("HealthLens AI · Python · Streamlit + scikit-learn · For educational and research use only. "
               "Not a substitute for professional medical advice.")


main()
