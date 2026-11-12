import hashlib
import json
import streamlit as st
from ai_email_security.analyzer import analyze
from ai_email_security.eml_reader import InputError
from ai_email_security.ollama_client import AnalysisError

st.set_page_config(page_title='AI Email Security', page_icon='✉️')
st.title('AI Email Security')
st.caption('Demo v0.1.0 • angielskie wiadomości • lokalna analiza Qwen3 4B')
st.write('Wybierz wiadomość .eml. Otrzymasz ocenę zagrożeń i wskazówki po polsku.')
uploaded = st.file_uploader('Wiadomość e-mail (maks. 5 MB)', type=['eml'])
raw = uploaded.getvalue() if uploaded else None
fingerprint = hashlib.sha256(raw).hexdigest() if raw else None
if st.session_state.get('fingerprint') != fingerprint:
    st.session_state.pop('report', None)
    st.session_state['fingerprint'] = fingerprint
if st.button('Analizuj', disabled=not raw, type='primary'):
    st.session_state.pop('report', None)
    try:
        with st.spinner('Analiza lokalna może potrwać do 3 minut…'):
            st.session_state['report'] = analyze(raw)
    except (InputError, AnalysisError) as exc:
        st.error('Analiza nie została ukończona. ' + str(exc))
report = st.session_state.get('report')
if report:
    result = report['analysis']
    labels = {'safe': 'Bezpieczny', 'suspicious': 'Podejrzany', 'dangerous': 'Niebezpieczny',
              'low': 'Niskie', 'medium': 'Średnie', 'high': 'Wysokie'}
    st.subheader(labels[result['verdict']])
    st.write('Ryzyko: ' + labels[result['risk']])
    st.text(result['explanation'])
    st.subheader('Sygnały znalezione w wiadomości')
    for item in result['evidence']:
        st.text('• ' + item)
    if report['rule_signals']:
        st.caption('Dodatkowe wskazania reguł — nie przesądzają o ataku:')
        for item in report['rule_signals']:
            st.text('• ' + item)
    st.subheader('Zalecenie')
    st.text(result['recommendation'])
    st.info(report['limitations'])
    st.download_button('Pobierz raport JSON', json.dumps(report, ensure_ascii=False, indent=2),
                       file_name='email-report.json', mime='application/json')
st.caption('Treść trafia wyłącznie do lokalnej Ollamy. Brak historii na dysku. '
           'Linki i załączniki nie są otwierane. Instrukcje zawarte w mailu mogą próbować manipulować modelem; odporność nie jest gwarantowana.')
