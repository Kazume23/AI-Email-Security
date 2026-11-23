# Porównanie Qwen i Keras

Uruchom run_demo.py w PyCharm, wybierz „Porównaj modele”, dodaj EML i kliknij
„Analizuj”. Wyniki są obok siebie, a pod nimi dostępna jest diagnostyka Keras.
„Zbadaj wpływ fragmentów” wykonuje dodatkową analizę wyłącznie na żądanie.
Pobierany raport porównania może zawierać cytaty z wiadomości; zwykły eksport
eksperymentu nie zawiera uzasadnień, sygnałów ani fragmentów tekstu.

## Architektura

analyze(raw, engine=...) zachowuje dotychczasowy raport i wyjątki.
compare(raw) z modułu comparison zwraca schema_version=comparison-v1.
Parser i reguły wykonują się raz. Rejestr ENGINES w analyzer wskazuje adapter,
deklarowany model i profil wejścia. Adapter otrzymuje (mail, signals) i zwraca
(analysis, details) zgodne z istniejącym raportem. Dodanie adaptera nie wymaga
zmiany pętli porównującej ani kolumn widoku. Dodatkowa diagnostyka Keras pozostaje
funkcją specyficzną dla tego silnika.

Wykonanie jest sekwencyjne: Keras, potem Qwen. Błąd jednego nie usuwa drugiego.
EngineUnavailable dziedziczy po AnalysisError. Niedostępność oznacza brak
usługi/modelu albo niemożność załadowania modelu; timeout i błędna odpowiedź
mają status error. Błąd parsowania poprzedza uruchomienie obu silników.
Wyniki bez sukcesu nie otrzymują werdyktu. Nie powstaje wspólny werdykt.

To porównanie systemów z różnymi wejściami: Keras analizuje temat i treść,
Qwen dodatkowo metadane i reguły. Nie jest to izolowany eksperyment architektur
na jednakowym wejściu. Score Keras nie jest skalibrowanym prawdopodobieństwem;
Qwen ma score=null. Brak danych o przycięciu oznacza null, nie brak przycięcia.
Identyfikator Keras pochodzi z załadowanego cache. Zmiana current.json nie
przełącza modelu w działającym procesie. Qwen identyfikujemy nazwą z konfiguracji;
podmiana artefaktu Ollamy pod tą samą nazwą ogranicza odtwarzalność badania.

## Eksperyment w PyCharm

Utwórz konfigurację Python dla compare_models.py, wybierz interpreter projektu,
a w „Parameters” wpisz:

```text
--manifest samples/comparison.jsonl --dataset-kind demonstration --limit 2
```

Przycisk Run uruchamia rzeczywiste modele. Nie wykonuje treningu. Domyślny limit
to 10 przypadków; większy limit trzeba podać jawnie. Nie należy podawać końcowego
testu do dobierania progów ani wyboru modeli. Rodzaj independent jest deklaracją
operatora, a nie automatycznym potwierdzeniem niezależności danych.

Manifest zawiera po jednym obiekcie JSON na linię: id (unikalny tekst), path
(ścieżka EML względem manifestu lub absolutna), label (0 legalny, 1 atak), opcjonalnie
source i category. Te identyfikatory są zapisywane, więc nie umieszczaj w nich
adresów ani prywatnej treści. Walidacja manifestu następuje przed analizami.

reports/experiments/<czas-id>/ zawiera run.json, cases.jsonl, cases.csv i summary.json.
Każdy przypadek jest zapisywany od razu. Przerwany przebieg pozostaje ze statusem
running; częściowe rekordy można odczytać. Kolejny przebieg tworzy nowy katalog.
JSONL jest pełnym eksportem technicznym, CSV skróconą tabelą wyników.
run.json zapisuje konfigurację, wersję kodu, stan zmian, sumę różnic, hash manifestu,
zakres i kolejność silników. Rekordy zawierają hashe wejść, dostępne identyfikatory
modeli i progi, bez tekstu, ścieżek EML i pełnych komunikatów wyjątków.

## Metryki

Ostrzeżenie to suspicious lub dangerous. Metryki każdego modelu obejmują tylko
udane analizy, zawsze z pokryciem i licznikami błędów/niedostępności. Błąd pliku
jest odnotowany jako input_error i nie oznacza poprawnej ani błędnej predykcji.
Brak mianownika daje null. Zgodność dotyczy dokładnego werdyktu, wyłącznie gdy
oba modele zakończyły analizę. Nie jest miarą poprawności.

Czasy silników obejmują pierwsze ładowanie i diagnostykę. Raport podaje pierwszy
czas, średnią i medianę; parsowanie i czas całego żądania są zapisane osobno
dla każdego przypadku. Nie są to porównania wydajności samej sieci neuronowej.
