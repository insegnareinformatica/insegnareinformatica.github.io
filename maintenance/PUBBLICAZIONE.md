# Pubblicazione del sito e del libro

## Prima di iniziare

Il repository pubblico e' insegnareinformatica/insegnareinformatica.github.io.
Il sito conserva le pagine Home, Contenuti, Risorse e Contatti.
Il dominio principale configurato e' https://informaticainclasse.it/.
I DNS e il certificato HTTPS devono essere operativi prima dell'attivazione
del contatore. Nessuna modifica ai DNS e' richiesta dal PHP.

Il workflow Deploy site continua a pubblicare soltanto docs/ tramite MkDocs.
Nei file pubblicati non possono entrare PDF, sorgenti del libro, script PHP
o documenti di lavoro: il controllo scripts/check_site.py blocca questi casi.
Le dipendenze restano su MkDocs 1.x e Material 9.x, le versioni compatibili con
il progetto. Il tema usa font di sistema, senza richieste a Google Fonts.

## Sorgenti futuri

Inserire in book/ soltanto i sorgenti e le immagini approvati per la diffusione.
Un push rende i sorgenti visibili nel repository pubblico, anche se i PDF
sono ancora disabilitati. Non inserire materiale editoriale riservato.

config/book.json riprende il vecchio progetto:

- sorgente principale: book/main.tex;
- motore: LuaLaTeX;
- metadati facoltativi: book/version.tex;
- nome dell'allegato pubblico: insegnare-informatica.pdf.

Se il sorgente finale usa un'altra struttura o un altro motore, aggiornare
questa configurazione prima di eseguire il workflow. Gli engine ammessi sono
lualatex, pdflatex e xelatex. Il compilatore remoto usa TeX Live 2026.

Se book/version.tex esiste, la pubblicazione aggiorna guideversion e
guideversiondate nella sola copia temporanea usata per compilare. Il file deve
usare le macro newcommand del vecchio progetto; una struttura diversa ferma
la pubblicazione, per evitare metadati errati. Se il file manca, la versione
compare sul sito e nella release, senza modificare il contenuto del libro.

I PDF generati restano esclusi da Git e vengono distribuiti solo come allegati
alle release. L'esclusione globale dei PDF va valutata quando arriveranno i
sorgenti: eventuali figure PDF autorizzate richiederanno eccezioni mirate.

## Verificare prima di pubblicare

Aprire Actions, scegliere "Libro - verifica o pubblica", poi Run workflow:

1. Branch: main.
2. Operazione: verifica.
3. Lasciare disattivata la conferma di pubblicazione.

La verifica compila il libro e controlla il PDF, ma non crea tag, release
o allegati scaricabili e non aggiorna i collegamenti del sito. I log di un
repository pubblico non sono uno spazio riservato per manoscritti segreti.
La verifica visiva del PDF va fatta localmente prima del via libera.

Nessuno di questi comandi e' stato eseguito sul vecchio libro durante
la preparazione dell'integrazione.

## Dare il primo via libera

In Settings > Secrets and variables > Actions > Variables creare:

    BOOK_PUBLICATION_ENABLED = true

Questa e' un'autorizzazione persistente: abilita anche la pubblicazione
automatica delle successive modifiche ai sorgenti su main.
Finche' la variabile manca o e' diversa da true, l'aggiunta dei sorgenti non
compila ne' pubblica automaticamente PDF.

Dopo il via libera, eseguire manualmente il workflow con l'operazione
in-lavorazione e selezionare la conferma. Oppure pubblicare direttamente
la prima versione consigliata seguendo la procedura sotto.

Per sospendere le pubblicazioni, impostare la variabile a false.
Questo non ritira PDF, release o sorgenti gia' pubblicati.

## Versione in lavorazione

Con il via libera attivo, ogni push su main che modifica book/ o la relativa
configurazione avvia la compilazione. Le modifiche solo al sito non ricompilano
il libro. Rimane disponibile anche l'avvio manuale.

Ogni compilazione pubblicata ha una propria prerelease con identificativo
lavorazione-<numero esecuzione>-<tentativo>. In questo modo gli allegati
precedenti e i relativi conteggi non vengono cancellati o azzerati.
La home mostra soltanto la versione in lavorazione piu' recente.
Gli allegati precedenti restano accessibili su GitHub: non sono copie private.
Non e' configurata alcuna cancellazione automatica.
La conservazione dello storico e' stata confermata da Michael.

Una compilazione automatica superata da un nuovo commit non pubblica un PDF
piu' vecchio sopra quello recente. Se la compilazione fallisce, la versione
pubblica precedente rimane disponibile.

## Versione consigliata dal browser

In Actions > "Libro - verifica o pubblica" > Run workflow:

1. Scegliere main e l'operazione consigliata.
2. Inserire il numero, ad esempio 1.0.0, e le novita'.
3. Selezionare "Confermo che questo PDF puo essere reso pubblico".
4. Avviare il workflow.

Il PDF viene compilato dal commit selezionato all'avvio. Il caricamento avviene
in una release in bozza, resa pubblica soltanto dopo la verifica dell'allegato.
Il numero deve essere nuovo e superiore a quelli consigliati gia' pubblicati.
Non vengono sovrascritti tag o PDF precedenti.

La home mostra la nuova versione consigliata, data e conteggio dei download.
Un elenco espandibile conserva i collegamenti alle consigliate precedenti.
Il pubblico vede etichette semplici, senza terminologia tecnica.

Una release lasciata in bozza da un caricamento fallito resta da controllare:
il sistema non la cancella o sovrascrive automaticamente. Dopo una pubblicazione
riuscita, se l'aggiornamento del sito fallisce, basta rieseguire Deploy site;
non occorre ripubblicare il libro.

## Aggiornamento del sito e dei conteggi

Dopo ogni pubblicazione del libro, il workflow richiede esplicitamente un
nuovo Deploy site. Non si affida all'evento release generato da GITHUB_TOKEN,
che non attiverebbe automaticamente un altro workflow.

Il sito recupera soltanto i metadati delle release pubbliche e il conteggio
GitHub degli allegati chiamati insegnare-informatica.pdf. Non scarica i PDF
per generare il sito e non incrementa quindi questi conteggi.
Le bozze e le release senza un PDF pronto sono escluse.

Vengono mostrati:

- conteggio del PDF consigliato corrente;
- conteggio del PDF in lavorazione corrente;
- totale dei download di tutte le versioni pubblicate;
- conteggi delle consigliate archiviate;
- data dell'ultimo aggiornamento dei numeri.

Sono download registrati da GitHub, non lettori distinti o conferme di lettura.
I numeri vengono incorporati nell'HTML: nessuna richiesta statistica parte dal
browser per leggerli. Si aggiornano a ogni pubblicazione del sito o avviando
manualmente Deploy site. Non sono in tempo reale e non ci sono aggiornamenti
programmati.

Se il recupero dei metadati fallisce, la pubblicazione del sito si ferma e resta
online la versione precedente, evitando di mostrare zeri o collegamenti falsi.

## Pubblicare questa integrazione

Dalla cartella di questo clone, dopo la revisione:

    git status --short
    git add .
    git diff --cached --stat
    git commit -m "Prepara pubblicazione libro e contatori"
    git push origin HEAD:main

Non occorre attivare BOOK_PUBLICATION_ENABLED per pubblicare solo il sito.
Nessuna automazione carica file sul server lodi.ml: il PHP va caricato a parte.
