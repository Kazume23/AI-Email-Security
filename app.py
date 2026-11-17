import hashlib
import json
import streamlit as st
from ai_email_security.analyzer import analyze
from ai_email_security.eml_reader import InputError
from ai_email_security.ollama_client import AnalysisError
from ai_email_security.config import SETTINGS

st.set_page_config(page_title="AI Email Security", page_icon="✉️")
st.title("AI Email Security")
st.caption("Angielskie wiadomości • lokalna analiza Qwen / TensorFlow Keras")
engine = st.selectbox(
    "Silnik analizy",
    ["qwen", "keras"],
    format_func=lambda value: {"qwen": "Qwen (Ollama)", "keras": "TensorFlow / Keras"}[
        value
    ],
)
if engine == "keras":
    st.info(
        "Model bazowy v0.2.0. Testy nowych legalnych wiadomości wykazały nadmierną liczbę alarmów. Wynik wymaga weryfikacji użytkownika."
    )
st.write("Wybierz wiadomość .eml. Otrzymasz ocenę zagrożeń i wskazówki po polsku.")
uploaded = st.file_uploader("Wiadomość e-mail (maks. 5 MB)", type=["eml"])
raw = uploaded.getvalue() if uploaded else None
fingerprint = hashlib.sha256(raw).hexdigest() if raw else None
if st.session_state.get("fingerprint") != fingerprint:
    st.session_state.pop("report", None)
    st.session_state["fingerprint"] = fingerprint
if st.session_state.get("engine", engine) != engine:
    st.session_state.pop("report", None)
st.session_state["engine"] = engine
if st.button("Analizuj", disabled=not raw, type="primary"):
    st.session_state.pop("report", None)
    try:
        with st.spinner("Analiza lokalna może potrwać do 3 minut…"):
            st.session_state["report"] = analyze(raw, engine=engine)
    except (InputError, AnalysisError) as exc:
        st.error("Analiza nie została ukończona. " + str(exc))
report = st.session_state.get("report")
if report:
    result = report["analysis"]
    labels = {
        "safe": "Bezpieczny",
        "suspicious": "Podejrzany",
        "dangerous": "Niebezpieczny",
        "low": "Niskie",
        "medium": "Średnie",
        "high": "Wysokie",
    }
    st.subheader(labels[result["verdict"]])
    st.write("Ryzyko: " + labels[result["risk"]])
    if "score" in report:
        st.caption(
            f"Wynik klasyfikatora {report['score']:.3f} • progi {report['thresholds']['low']:.3f} / {report['thresholds']['high']:.3f}"
        )
    st.text(result["explanation"])
    st.subheader("Sygnały znalezione w wiadomości")
    for item in result["evidence"]:
        st.text("• " + item)
    if report["rule_signals"]:
        st.caption("Dodatkowe wskazania reguł — nie przesądzają o ataku:")
        for item in report["rule_signals"]:
            st.text("• " + item)
    st.subheader("Zalecenie")
    st.text(result["recommendation"])
    st.info(report["limitations"])
    st.download_button(
        "Pobierz raport JSON",
        json.dumps(report, ensure_ascii=False, indent=2),
        file_name="email-report.json",
        mime="application/json",
    )
    if engine == 'keras' and 'diagnostics' in report:
        with st.expander('Diagnostyka modelu Keras'):
            diagnostics = report['diagnostics']
            st.write('Model:', diagnostics.get('model_id', report.get('model')))
            st.write('Architektura:', diagnostics.get('architecture', 'niedostępna'))
            st.caption('Wynik sieci nie jest skalibrowanym prawdopodobieństwem phishingu.')
            st.json(diagnostics)
            st.write('Sygnały reguł (nie zmieniają wyniku sieci):')
            for signal in report['rule_signals']:
                st.text(signal)
            if diagnostics.get('tokens_omitted', 0):
                st.warning('Model nie przetworzył całego tekstu: część tokenów została przycięta.')
            if st.button('Zbadaj wpływ fragmentów', disabled=not raw or not SETTINGS.get('diagnostics', {}).get('text_influence_enabled', True)):
                from ai_email_security.keras_diagnostics import influence
                from ai_email_security.eml_reader import read_eml

                try:
                    with st.spinner('Sprawdzanie wariantów wiadomości…'):
                        report['text_influence'] = influence(read_eml(raw), report['model'], report['score'])
                except (AnalysisError, InputError, ValueError, RuntimeError) as exc:
                    st.error('Diagnostyka fragmentów nie została ukończona. ' + str(exc))
            if 'text_influence' in report:
                sensitivity = report['text_influence']
                st.caption(sensitivity['limitations'])
                st.dataframe(sensitivity['fragments'], hide_index=True)
                st.write('Liczba zbadanych wariantów:', sensitivity['variants_evaluated'])
                st.write('Pominięte fragmenty:', sensitivity['fragments_skipped'])
            st.caption('Raport może zawierać fragmenty wiadomości. Pobierasz go świadomie na swój komputer.')
            st.download_button('Pobierz diagnostykę JSON', json.dumps({'diagnostics': diagnostics, 'rule_signals': report['rule_signals'], 'text_influence': report.get('text_influence')}, ensure_ascii=False, indent=2), file_name='keras-diagnostics.json', mime='application/json')
st.caption(
    "Analiza odbywa się lokalnie na komputerze. Diagnostyka Keras może zapisywać lokalne logi techniczne bez treści wiadomości. "
    "Linki i załączniki nie są otwierane. Instrukcje zawarte w mailu mogą próbować manipulować modelem; odporność nie jest gwarantowana."
)
