# Dane v0.2.0

Źródło: Arifa Islam Champa, Phishing Email Curated Datasets, v1 (2023),
https://zenodo.org/records/8339691, DOI 10.5281/zenodo.8339691.
Metadane wydawcy deklarują CC BY 4.0.

Wykorzystujemy Nazario.csv i Nigerian_Fraud.csv (etykieta 1) oraz wyłącznie
wiadomości z etykietą 0 z SpamAssasin.csv. Spam oznaczony 1 w SpamAssassin
jest wykluczony. Lokalny source.json przechowuje SHA-256 każdego pobranego pliku.
Dane nie są ponownie publikowane w repozytorium.

Cytowania wskazane przez autorów:
- Champa, Rabbi, Zibran (2024), Why phishing emails escape detection: A closer look at the failure points, ISDFS.
- Champa, Rabbi, Zibran (2024), Curated datasets and feature analysis for phishing email detection with machine learning, ICMI.

Dobór obejmuje maksymalnie 4000 przykładów każdej klasy, po wykluczeniu pustych,
zbyt długich, sprzecznie oznaczonych i zduplikowanych tekstów. Temat i treść
są przygotowywane tak samo w treningu i aplikacji. Podobieństwo TF-IDF po
normalizacji tworzy grupy przy cosine >= 0.85. Grupowany podział jest zbliżony
do 70/15/15; rzeczywiste liczebności zapisuje manifest. Grupowanie jest heurystyczne.

Ograniczenia: klasy pochodzą z innych korpusów i okresów, więc model może uczyć
się stylu źródła. Etykiety przyjmujemy od autorów, bez ręcznego audytu każdego
maila. Wynik na odłożonej części tych samych źródeł nie mierzy jakości na
współczesnej skrzynce. Cztery scenariusze syntetyczne oceniamy osobno.
