# Weryfikacja integracji — 23 listopada 2026

33 testy unittest zakończyły się powodzeniem, w tym atrapy błędów silników,
jedno parsowanie, zgodność starego API, diagnostyka, metryki, prywatność eksportu,
limit przypadków oraz widok Streamlit. Ruff check i format --check zakończone
bez błędów. Ostrzeżenia TensorFlow i Streamlit nie były błędami testów.

Przebieg demonstracyjny: reports/experiments/20261123T005306Z-31fe9241.
Aktywny model Keras: 20261117T125028Z-50b0fd0c. Qwen: qwen3:4b.

| Przypadek | Keras | Qwen |
| --- | --- | --- |
| safe.eml | dangerous, 0.7525970936 — fałszywy alarm | safe |
| attachment.eml | dangerous, 0.7047254443 | błąd: przekroczono 180 s |

Obie wiadomości miały po 28 tokenów Keras i nie były przycinane.
Timeout Qwen nie usunął wyniku Keras. Zgodność: 0 z 1 kompletnej pary;
drugi przypadek ma agreement=null. To kontrola integracji na dwóch sztucznych
przykładach, nie pomiar skuteczności ani podstawa strojenia modelu.

SHA-256 przed i po weryfikacji pozostały identyczne:

- current.json: 8144023c780fff16a8c5e4a24df2b07c72fc333df2fbac3e7fdfcbd8e9617f4e
- model.keras: 31cda680e9700693b8f88befef536e8d87195e9aa567f8847f5382160bf9dbbf
- metadata.json: 0fe6017ee9c38613bbf794fe2e9b5858d6de7c89052c59bc427ddf2e865ef35a

Nie uruchomiono treningu ani analizy dużego zbioru. Nie zmieniono progów,
architektury, danych treningowych ani aktywnego modelu. Nie tworzono tagu wydania.

Instrukcje przeniesiono z README do setup-v020.md; README pozostaje pusty.
Usunięte komentarze nie zmieniają zachowania: klient Ollamy nadal omija proxy,
podziały treningowe pozostają grupowe, progi zachowują pasmo pośrednie,
a test prompt injection sprawdza separację instrukcji, nie odporność modelu.
