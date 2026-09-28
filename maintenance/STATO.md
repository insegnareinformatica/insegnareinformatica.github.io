# Preparazione e verifiche

Riepilogo delle verifiche locali del 27 settembre 2026, prima del primo invio.
Michael ha autorizzato commit e push dell'integrazione, lasciando disattivati
libro e contatore sul sito. Nessun libro e' stato compilato o pubblicato.
Il progetto precedente non e' stato modificato.
Michael ha caricato il PHP sul proprio hosting; il collaudo remoto e' riuscito.

## File modificati

- `.github/workflows/deploy-site.yml`: metadati dei download e controlli prima della pubblicazione.
- `.gitignore`: esclusione di PDF, credenziali, contatore e risultati delle compilazioni.
- `README.md`: rimandi alle istruzioni e verifiche locali.
- `docs/index.md`: spazio per le due versioni del libro, senza PDF attivi inizialmente.
- `docs/assets/stylesheets/site.css`: aspetto dei download e del conteggio delle aperture.
- `mkdocs.yml`: integrazione delle versioni e contatore facoltativo, font locali, dominio configurato.
- `requirements.txt`: dipendenze compatibili con MkDocs 1.x e Material 9.x.

## File creati

- `.github/workflows/check-site.yml`
- `.github/workflows/publish-book.yml`
- `book/README.md`
- `config/book.json`
- `docs/assets/javascripts/home-counter.js`
- `hooks/book_downloads.py`
- `maintenance/CONTATORE.md`
- `maintenance/DECISIONI.md`
- `maintenance/PUBBLICAZIONE.md`
- `maintenance/STATO.md`
- `overrides/main.html`
- `scripts/book.py`
- `scripts/check_site.py`
- `server/home-counter/counter.php`
- `tests/home-counter.test.cjs`
- `tests/test_book.py`
- `tests/test_counter.py`
- `tests/test_site_build.py`

## Controlli prima del primo invio

- `mkdocs build --strict`: riuscito.
- Controllo del sito generato: nessun PDF, sorgente del libro, PHP o script esterno.
- 18 test Python superati; 4 test PHP saltati per assenza di PHP CLI sul Mac.
- 4 test JavaScript superati.
- `actionlint`: nessun errore nei tre workflow.
- Browser a 1440x900 e 375x812: nessuna immagine mancante o eccedenza orizzontale;
  ricerca interna funzionante, navigazione e quattro pagine controllate.
- Prova con versioni fittizie: download, date, totale e storico correttamente generati.
- Contatore simulato nel browser: una richiesta a ogni apertura della home,
  nessuna nelle altre pagine o da localhost, nessun cookie o referrer inviato.
- Nessuna richiesta al contatore reale durante le prove locali nel browser.
- Dopo il caricamento del PHP su lodi.ml: quattro richieste autorizzate hanno
  restituito in sequenza i totali 1, 2, 3 e 4. Entrambi i domini HTTPS ammessi
  ricevono il corretto permesso CORS; nessuna risposta imposta cookie.
- Le richieste senza origine o da origine non ammessa restituiscono 403;
  OPTIONS restituisce 204. Queste richieste non incrementano il totale.

Il collaudo remoto e' distinto dai test automatici PHP locali, ancora saltati.
Il primo push avvia anche i test PHP su GitHub; gli esiti aggiornati sono
consultabili nella [pagina dei controlli](https://github.com/insegnareinformatica/insegnareinformatica.github.io/actions/workflows/check-site.yml).
La compatibilita' dei sorgenti finali LaTeX non e' ancora verificabile.

## Aggiornamento del 28 settembre 2026

- La prima pubblicazione e tutti i 26 test su GitHub sono riusciti, inclusi i test PHP.
- Il dominio e' operativo, il certificato e' approvato e HTTPS e' obbligatorio.
- Su richiesta di Michael, restano soltanto Home e Contenuti. Risorse e contatti
  sono incorporati nella home, con il nuovo testo fornito dall'autore.
- Il collegamento a YouTube usa un'immagine gia' locale e l'icona di riproduzione.
  Non ci sono player incorporati ne' richieste automatiche a YouTube.
- HOME_COUNTER_URL e' impostata e il contatore e' pubblicato nella home.
  La pubblicazione del libro rimane disabilitata.
- Nuova pubblicazione e controlli su GitHub riusciti (23 test Python, 4 JavaScript).
- Prova reale a 1440x900 e 375x812 riuscita: tre aperture della home (5, 6, 7),
  nessun incremento passando a Contenuti, nessun cookie impostato, nessuna
  richiesta automatica a YouTube, nessuna immagine mancante o eccedenza orizzontale.

## Prossimi passi

Aggiungere esclusivamente i sorgenti approvati, verificare il PDF e dare
il via libera esplicito alla pubblicazione del libro.

La conservazione delle versioni precedenti in lavorazione, mostrando soltanto
l'ultima sulla home, e' confermata.

Le istruzioni complete sono in [PUBBLICAZIONE.md](PUBBLICAZIONE.md) e
[CONTATORE.md](CONTATORE.md).
