# Historia zmian

## 0.1.0 — 2026-11-12

- Lokalny interfejs Streamlit, wybór EML i pobieranie raportu JSON.
- Odczyt MIME, HTML, nagłówków, linków i metadanych załączników.
- Reguły pomocnicze oraz analiza przez lokalną Ollamę / qwen3:4b.
- Walidacja wyniku, limity wejścia i obsługa błędów bez fałszywego werdyktu.
- Pięć sztucznych przykładów oraz testy automatyczne parsera, klienta i interfejsu.
- Test na rzeczywistym LLM oczekuje na uruchomienie Ollamy i pobranie modelu
  na komputerze użytkownika. Testy klienta używają odpowiedzi zastępczych.
- TensorFlow/Keras i pomiar jakości pozostają kolejnym etapem pracy.
