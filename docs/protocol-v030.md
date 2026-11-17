# Protokół v0.3.0

Gałąź `keras`. Protokół ustalony przed treningiem B/C.

A to zapisany model 0.2.0. B to Embedding/średnia/Dense na nowych danych.
C to Embedding/Conv1D/maskowane maksimum/Dense na tych samych danych co B.
Ziarna 42, 43, 44, wspólny słownik i długość, limit 20 epok i patience 3.
Długość to najmniejsze 512/1024/2048 obejmujące 95% treningu, inaczej 2048.

Główna metryka FPR ostrzegania. Minimalny recall ustala A na nowej walidacji
ze swoimi zapisanymi progami. Progi B/C dobieramy wyłącznie na walidacji.
Średni FPR musi być niższy niż A, a każdy przebieg spełnia wymagany recall.
Remis preferuje B. Artefakt wybieramy według FPR, następnie recall.
Niepowodzenie kandydatów oznacza pozostawienie A.

Nowa walidacja i wspólny test muszą być wolne od dokładnych i bliskich
duplikatów całego starego korpusu. Grupy szablonów nie mogą przecinać podziałów.
Niezależny test wymaga obu klas z niewidzianych źródeł lub kampanii.
Brak takich danych zatrzymuje eksperyment do ustalenia doboru danych.

Raporty: precision, recall, FPR, F1, liczby pomyłek, pokrycie, odrzucenia,
przycięcia i czas. FPR/recall z przedziałami Wilsona 95%. Podział według źródła
i kategorii. Końcowy test dopiero po zamrożeniu wyboru, bez ponownego strojenia.
Znane osiem scenariuszy to diagnostyka rozwojowa.

Maskowanie Conv1D wyklucza wszystkie okna dotykające paddingu. Brak poprawnego
okna daje wektor zerowy. Testy obejmują zmianę długości paddingu i zapis modelu.
Limit pliku, limit danych JSON 16000 znaków i limit tokenów są odrębne.

Wnioski o wpływie źródła wymagają tabeli źródło/klasa i wyników na źródłach
niewidzianych. Sama wysoka korelacja nie stanowi dowodu mechanizmu błędu.
