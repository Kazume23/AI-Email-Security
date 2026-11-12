# AI-Email-Security v0.1.0

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
Nie ma historii na dysku: dane są przejściowo w pamięci aplikacji/Ollamy.
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

TensorFlow/Keras nie są jeszcze częścią v0.1.0. Kolejny etap: osobny klasyfikator
NLP, oznaczone i rozdzielone dane treningowe/walidacyjne/testowe, porównanie
z LLM, polskie wiadomości oraz kontrolowane przykłady generowane przez AI.
Adaptacja oznacza ponowne trenowanie na zweryfikowanych danych, nie automatyczne
uczenie z przesyłanych maili. Badane scenariusze: wyłudzenie danych logowania,
oszustwo płatnicze i nakłanianie do otwarcia załącznika.
