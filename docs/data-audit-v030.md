# Audyt danych v0.3.0 — 2026-11-17

Status: dobór danych niezakończony. Nie uruchomiono treningu B/C ani nie zmieniono aktywnego modelu A.
Użytkownik wybrał poszukiwanie większych, wiarygodnych danych zamiast treningu pilotażowego.

## Odrzucony główny zbiór

[Zenodo 13474746](https://zenodo.org/records/13474746): po usunięciu powtórzeń
pozostało 100 tekstów (77 legalnych i 23 phishingowe), mimo 2000 wierszy.
Po kontroli podobieństwa ze starym korpusem podział grupowy dał tylko 22 przykłady
walidacyjne i 9 testowych. Nie jest to odpowiednia podstawa wyboru nowego modelu.
Dotychczasowe pliki data/v030 są roboczymi kandydatami, nie zatwierdzonym eksperymentem.
prepare_experiment.py domyślnie wykonuje teraz wyłącznie audyt.

[SunnyThakur25](https://github.com/SunnyThakur25/Phishing-Benign-Email-Dataset-Short-Version-):
200 przykładów, po 100 na klasę. Nie ustalono pochodzenia z rzeczywistych skrzynek.
Może być diagnostyką, ale nie dowodem skuteczności na prawdziwych nowych mailach.

## Większy kandydat: MeAJOR 2.0

[Oficjalny rekord](https://zenodo.org/records/18471483), autorzy: Francisco Cardoso,
João Vitorino, Paulo Mendes, Eva Maia, Isabel Praça. Licencja z API: CC-BY-4.0.
Pobrano Parquet i zweryfikowano opublikowany MD5 78e397ad8447bcdba5a98097921ba8bd.
Odtworzenie lokalnego audytu: uruchom audit_candidate.py w interpreterze projektu.
Pobieranie nie powoduje treningu. Pliki danych pozostają poza Git.

| Źródło w pliku | Etykieta 0 | Etykieta 1 |
| --- | ---: | ---: |
| trec5 | 29929 | 19654 |
| trec6 | 11208 | 3797 |
| trec7 | 19513 | 24583 |

Łącznie 108685 wierszy, w tym jeden bez etykiety i źródła.
Nie występują wartości nazario ani nigerian_fraud, choć opis wymienia te korpusy.
Nie wiadomo, czy zostały pominięte, czy zmieniono ich oznaczenia.

[Artykuł autorów](https://pmc.ncbi.nlm.nih.gov/articles/PMC13080633/) wskazuje,
że TREC pochodzi z zadania wykrywania spamu. Nie potwierdzono procedury
ponownego oznaczenia każdego pozytywnego przykładu jako phishingu.
Dlatego nie zatwierdzamy automatycznie label=1 jako phishing: groziłoby to
badaniem spamu zamiast zagrożeń z tematu pracy. Rozmiar zbioru nie usuwa tej wątpliwości.

## Dalszy dobór

[Oryginalny korpus Jose Nazario](https://monkey.org/~jose/phishing/) udostępnia
roczne archiwa rzeczywistych wiadomości, także 2024 i 2025. To kandydat na
nowe ataki po deduplikacji ze starym korpusem, nie kompletny zbiór obu klas.
Potrzebne są legalne wiadomości z wielu źródeł oraz kontrola wpływu źródła
i podział według kampanii. Nie wolno deklarować rozwiązania problemu źródło–etykieta
wyłącznie przez połączenie nowego archiwum ataków z inną kolekcją legalnych maili.

Warunki wznowienia treningu: potwierdzone znaczenie etykiet, pochodzenie i licencja,
obie klasy w walidacji i teście, brak przecieku względem całego starego korpusu,
raport liczebności niezależnych grup i zatwierdzony protokół doboru danych.
