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

## Manutenzione del sito e del libro

Il sito rimane in Markdown con MkDocs Material. I sorgenti del libro, quando
pronti, andranno in book/. I vecchi sorgenti e PDF riservati non sono stati importati.

- [Pubblicazione, versioni e conteggi dei download](maintenance/PUBBLICAZIONE.md)
- [Installazione del contatore della sola home](maintenance/CONTATORE.md)
- [Decisioni concordate e verifiche ancora necessarie](maintenance/DECISIONI.md)
- [Elenco delle modifiche e verifiche locali](maintenance/STATO.md)

La pubblicazione del libro resta disabilitata fino al via libera esplicito.
Il contatore della home si attiva tramite la variabile HOME_COUNTER_URL su GitHub;
in locale rimane disattivato. La home raccoglie anche risorse e contatti,
mentre Contenuti resta l'unica pagina aggiuntiva.
Le istruzioni operative sono fuori da docs/ e non vengono pubblicate sul sito.

## Anteprima locale

    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
    .venv/bin/mkdocs serve

Aprire http://127.0.0.1:8000/. Le anteprime locali non chiamano il contatore.

## Verifica

    .venv/bin/python -m unittest discover -s tests -v
    node --test tests/home-counter.test.cjs
    .venv/bin/mkdocs build --strict
    .venv/bin/python scripts/check_site.py

I test del PHP richiedono PHP CLI 8 a 64 bit; se non e' disponibile localmente,
vengono saltati. Il controllo su GitHub verifica anche PHP. Il libro non viene
compilato da questi test.
