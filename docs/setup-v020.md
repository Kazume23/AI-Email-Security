# AI-Email-Security — instrukcje i historyczne wyniki v0.2.0

## Nowy silnik TensorFlow/Keras

Uruchom `run_demo.py` w PyCharm i wybierz **TensorFlow / Keras** z listy silników.
Na komputerze użytym do wdrożenia model jest już wytrenowany w katalogu `models`.
Po zmianie modelu uruchom aplikację ponownie, aby wyczyścić pamięć podręczną.

Odtworzenie na innym komputerze wymaga instalacji `requirements-ml.txt`, następnie
uruchomienia w PyCharm kolejno `download_data.py`, `build_corpus.py`,
`prepare_data.py`, `train_model.py`, `evaluate_model.py`, `evaluate_scenarios.py`.
Każdy skrypt uruchamia się przez prawy przycisk → Run. Parametry są w `config.toml`.
Modele i dane są lokalne i ignorowane przez Git. Raporty trafiają do `reports`.
Pobranie danych wymaga Internetu. Trening odbywa się domyślnie na CPU.

### Wyniki bazowe z 13 listopada 2026

8000 wiadomości; trening 5657, walidacja 1179, test 1164. Progi z walidacji
wynoszą 0.24551 i 0.36028. Test: 549 poprawnie wykrytych zagrożeń, 3 przeoczenia,
606 poprawnych ocen legalnych maili, 6 fałszywych alarmów. Precision 98.92%,
recall 99.46%, F1 99.19%. W tym teście nie wystąpił wynik pośredni.

**Ograniczenie jakości:** na osobnym zestawie 8 syntetycznych scenariuszy model
ostrzegł przy wszystkich 4 atakach, ale też przy wszystkich 4 legalnych mailach.
Wysoki wynik wewnątrz korpusu nie przekłada się na potwierdzoną skuteczność
na nowych wiadomościach. Źródła klas, wiek danych i styl tekstu mogą wpływać na
wynik. Nie dostrajano modelu do tych ośmiu przykładów po pomiarze.

Architektura: TextVectorization → Embedding → GlobalAveragePooling1D → Dense.
Słownik jest dopasowany wyłącznie do treningu. Przetwarzane jest pierwsze 512
tokenów tekstu, zapisane w konfiguracji modelu. Wynik dotyczy tego fragmentu.
Keras zwraca ocenę i standardowe zalecenie, a reguły dostarczają osobnych sygnałów.
Pełny opis pochodzenia danych znajduje się w `DATA_SOURCES.md`, a plan dalszych
wersji w `ROADMAP.md`.

Lokalne demo analizy angielskich wiadomości `.eml`. Python + Streamlit + Ollama
(`qwen3:4b`). Wynik i wyjaśnienie po polsku. To prototyp do pracy inżynierskiej,
nie filtr produkcyjny ani dowód skuteczności wykrywania zagrożeń.

## Uruchomienie w PyCharm — bez PowerShella

1. Otwórz ten projekt. W **Settings → Project → Python Interpreter** wybierz
   istniejący interpreter `venv\Scripts\python.exe` (Python 3.11 lub nowszy).
2. Otwórz `requirements.txt`. Wybierz **Install requirements**, jeśli PyCharm
   pokazuje taką propozycję. Alternatywnie w oknie interpretera naciśnij **+**,
   wyszukaj `streamlit` i wybierz **Install Package**.
3. Zainstaluj Ollamę ze strony https://ollama.com/download/windows i uruchom ją.
   W aplikacji Ollama wybierz/pobierz model **qwen3:4b**. Jeżeli twoja wersja
   aplikacji nie pozwala go pobrać z listy, w **Wierszu polecenia Windows (cmd)**
   wykonaj `ollama pull qwen3:4b`. Pobranie wymaga Internetu i kilku GB miejsca.
4. W PyCharm kliknij prawym przyciskiem **run_demo.py → Run 'run_demo'**.
5. Otwórz http://127.0.0.1:8501. Wybierz `samples/credentials.eml`, kliknij
   **Analizuj**, poczekaj na wynik i pobierz JSON.
6. Zatrzymanie: czerwony przycisk Stop w oknie Run. Ollama działa osobno.

Jeżeli pojawi się komunikat o braku Ollamy/modelu, uruchom Ollamę lub pobierz model
i ponów analizę. Pierwsza analiza może być wolniejsza z powodu ładowania modelu.
Limit oczekiwania wynosi 180 sekund; wydajność zależy od pamięci i procesora/GPU.

`main.py` to zachowany oryginalny plik startowy użytkownika. Demo uruchamia **run_demo.py**.

## Jak działa

`eml_reader` odczytuje MIME, tekst/HTML, nagłówki, adresy URL i metadane załączników.
`rules` wskazuje różnice From/Reply-To i wybrane ryzykowne rozszerzenia.
`ollama_client` wysyła dane wyłącznie na lokalny adres 127.0.0.1:11434,
z oddzielną instrukcją systemową i schematem odpowiedzi JSON.
`analyzer` składa raport, a `app.py` prezentuje go i udostępnia pobranie.

Klasyfikacje: `safe/low`, `suspicious/medium`, `dangerous/high`. Ocena nie jest
skalibrowanym prawdopodobieństwem. Brak wykrytych sygnałów nie gwarantuje bezpieczeństwa.
Reguły nie stanowią samodzielnego dowodu ataku. Nagłówki uwierzytelnienia mogą być
sfałszowane; nie wykonujemy własnej weryfikacji SPF/DKIM.

Limit pliku: 5 MiB; limit danych przekazywanych modelowi: 16000 znaków JSON.
Tekst i wersja HTML mogą być uwzględnione łącznie. Załączniki nie są wykonywane,
zapisywane ani skanowane, a linki nie są odwiedzane. Rozmiar załączonego maila
message/rfc822 jest rozmiarem jego serializacji MIME.
Treść maila pozostaje przejściowo w pamięci aplikacji/Ollamy. Diagnostyka Keras
może zapisywać techniczne logi, a jawnie uruchomione eksperymenty zapisują wyniki.
Raport nie zawiera pełnego maila, ale uzasadnienie może cytować jego fragmenty.
Prompt injection pozostaje ograniczeniem LLM; oddzielenie danych od instrukcji
nie daje gwarancji odporności. Nie udostępniaj tego demo w publicznej sieci.

## Przykłady i testy

W `samples` są wyłącznie sztuczne wiadomości z domenami example.com/net/org:
zwykły mail, wyłudzenie hasła, oszustwo płatnicze, przynęta z załącznikiem
i próba manipulacji modelem. `invoice.exe` zawiera wyłącznie nieszkodliwy tekst.
Przykłady nie stanowią zbioru do pomiaru jakości.

W PyCharm można uruchomić testy unittest z katalogu `tests`. Odpowiednik w cmd:
`venv\Scripts\python.exe -m unittest discover -s tests -v`.
Testy automatyczne komunikacji używają atrap odpowiedzi i nie wymagają Ollamy.
Rzeczywisty test demo: przeanalizuj wszystkie pięć przykładów, porównaj wynik
z treścią, pobierz JSON i sprawdź zgodność. Zatrzymaj Ollamę i sprawdź komunikat
błędu — nie powinien pojawić się werdykt bezpieczeństwa.

## Dalsza praca badawcza

TensorFlow/Keras są częścią v0.2.0. Kolejny etap obejmuje porównanie
z LLM, poprawę uogólniania, polskie wiadomości oraz kontrolowane przykłady generowane przez AI.
Adaptacja oznacza ponowne trenowanie na zweryfikowanych danych, nie automatyczne
uczenie z przesyłanych maili. Badane scenariusze: wyłudzenie danych logowania,
oszustwo płatnicze i nakłanianie do otwarcia załącznika.
