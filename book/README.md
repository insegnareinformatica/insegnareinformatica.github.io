# Sorgenti del libro

Questa cartella contiene i sorgenti LaTeX, le immagini e i font della guida
*Insegnare Informatica — Una guida per docenti del primo ciclo, Volume 1*.

Il file principale e' main.tex, compilato con LuaLaTeX.
Il percorso e il motore sono modificabili in ../config/book.json.
La cartella `font/` include i font Source Sans Pro e la relativa licenza;
deve restare accanto a `main.tex`, insieme alla cartella `img/`.
La configurazione locale `latexmkrc` non fa parte dei sorgenti pubblicati:
il workflow del sito imposta esplicitamente LuaLaTeX.

Prima della compilazione, `python scripts/book.py links` (dalla radice del sito)
controlla i collegamenti e genera `sitografia.tex` dal registro in `mkdocs.yml`.
Nella Sitografia entrano soltanto gli alias richiamati nei sorgenti attivi o
nella bibliografia, tramite `usera`, `\linkbreve` o `\hrefbreve`. Il registro
può contenere altri collegamenti destinati solo al sito: restano validati ma
non compaiono nella Sitografia. Commenti, copie LaTeX estranee ai sorgenti
attivi e vecchie Sitografie generate non aggiungono alias all'elenco.
Il generatore resta in `scripts/`, fuori da questa cartella. Finché i sorgenti
non sono presenti, il comando controlla soltanto il registro. Se trova file
`.tex` o `.bib` ma manca il sorgente principale, segnala l'incompletezza come
errore. Non occorre copiare i materiali privati di `ALTRO`.

Nei `.tex` usare `\linkbreve{alias}` o `\hrefbreve{alias}{testo}` per gli
alias definiti in `mkdocs.yml`; per gli altri indirizzi restano
`\urloriginale{URL}` e `\hreforiginale{URL}{testo}`. Nei `.bib`, `url`
conserva sempre la destinazione originale e `usera` contiene il solo alias
quando quella destinazione compare nel registro. Il controllo segnala alias
mancanti, duplicati, URL non validi e incoerenze fra questi campi.

Per verificare anche che il file generato sia aggiornato, senza modificarlo,
con la struttura predefinita `book/main.tex`:

    python scripts/aggiorna-link.py --check

L'inserimento dei sorgenti non abilita automaticamente la pubblicazione dei PDF.

Attenzione: questo repository e' pubblico. I sorgenti inviati a GitHub diventano
visibili anche quando la pubblicazione dei PDF e' disabilitata.
