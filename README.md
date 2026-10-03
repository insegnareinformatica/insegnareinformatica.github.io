# Insegnare Informatica

Questo sito raccoglie materiali, attività e risorse per l'insegnamento dell'informatica a scuola, con particolare attenzione al primo ciclo.

Nasce dal lavoro sviluppato per il libro "libero" (CC BY-NC-SA) *Insegnare Informatica*, dedicato principalmente alla scuola primaria, ma è pensato come uno spazio più ampio, da estendere nel tempo con nuovi contenuti e materiali per docenti di diversi ordini scolastici.

Il sito è disponibile all'indirizzo:

<https://informaticainclasse.it/>

## Contenuti

Il sito raccoglie e raccoglierà progressivamente:

- attività didattiche;
- materiali per docenti;
- approfondimenti sui contenuti di informatica;
- risorse collegate alle Indicazioni nazionali;
- materiali collegati al libro *Insegnare Informatica*, oltre che il libro stesso liberamente scaricabile;
- collegamenti ad altre risorse utili.

## Anteprima locale

    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
    .venv/bin/mkdocs serve

Aprire http://127.0.0.1:8000/. Le anteprime locali non chiamano il contatore.

## Verifica

    .venv/bin/python scripts/book.py links
    .venv/bin/python -m unittest discover -s tests -v
    node --test tests/home-counter.test.cjs
    .venv/bin/mkdocs build --strict
    .venv/bin/python scripts/check_site.py

I test del PHP richiedono PHP CLI 8 a 64 bit; se non e' disponibile localmente,
vengono saltati. Il controllo su GitHub verifica anche PHP. Il libro non viene
compilato da questi test.

Il comando `book.py links` controlla sempre gli alias in `mkdocs.yml`. Quando
saranno presenti i sorgenti indicati in `config/book.json`, verifica anche i
collegamenti della guida e genera l'intero `book/sitografia.tex`. Il controllo
automatico viene eseguito sulle pull request e su ogni commit a `main`, prima
della build del sito; viene ripetuto prima delle future compilazioni del libro.
Le modifiche restano nel checkout di lavoro, senza commit automatici.
Questo controllo non compila né pubblica la guida e non abilita la pubblicazione.
