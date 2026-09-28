# Decisioni concordate

- Conservare il sito Markdown. Dal 28 settembre 2026 la navigazione richiesta
  comprende soltanto Home e Contenuti; risorse e contatti sono nella home.
- I sorgenti finali saranno LaTeX, nello stesso repository del sito.
- Non importare i vecchi manoscritti, PDF o versioni sperimentali riservate.
- Versione in lavorazione pubblica e automatica dopo il primo via libera.
- Versione consigliata approvata dal browser, con numero e descrizione.
- Primo via libera esplicito; nessun PDF pubblico soltanto perche' sono arrivati
  i sorgenti.
- PDF distribuiti attraverso GitHub Releases e conteggi GitHub visibili sul sito.
- Conservare i PDF in lavorazione precedenti e mostrare sulla home solo l'ultimo.
- Nessun GoatCounter o altro servizio di analisi delle visite.
- Collegamento esterno alla playlist YouTube con immagine locale e icona di
  riproduzione; nessun player, miniatura o script caricato dai server YouTube.
- Solo aperture della home, incluse le ripetute; nessun riconoscimento di sessione.
- PHP sul proprio hosting, al percorso lodi.ml/insegnareinformatica/counter.php.
- CORS impostato nel PHP, senza modifiche ai DNS.
- Nessuna pubblicazione remota, release o compilazione del vecchio libro
  effettuata durante questa preparazione.

## Verifiche ancora da fare con i sorgenti finali

- Confermare percorso principale, motore, pacchetti e font effettivi del libro.
- Verificare l'eventuale integrazione delle macro guideversion e guideversiondate.
- Compilare e controllare visivamente il PDF prima del via libera.
- Controllare che i soli materiali autorizzati entrino nel repository pubblico.

## Sito e contatore

- DNS e HTTPS operativi dal 28 settembre 2026, con HTTPS obbligatorio su Pages.
- Contatore autorizzato e HOME_COUNTER_URL impostata il 28 settembre 2026.
  Il PHP era stato caricato e collaudato su lodi.ml il giorno precedente.
- Verificare il conteggio nella home pubblicata dopo il nuovo Deploy site.

## Scelte tecniche esplicite

Il contatore dei download del sito e' una fotografia dei numeri GitHub,
aggiornata a ogni generazione del sito, con data visibile.
Ogni PDF pubblico in lavorazione ha un allegato distinto: niente sovrascritture
che azzererebbero il relativo numero di download. La home ne mostra solo l'ultimo.
Le vecchie compilazioni pubbliche non vengono cancellate automaticamente.
La conservazione di tutti i PDF in lavorazione e' stata confermata da Michael.

Le istruzioni operative sono in maintenance/, fuori dalla documentazione pubblica.
La copia locale del vecchio progetto resta inalterata.
