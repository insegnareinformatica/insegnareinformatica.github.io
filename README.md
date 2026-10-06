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
    node --test tests/*.test.cjs
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
Il registro può contenere anche collegamenti usati soltanto nel sito: la
Sitografia include solo gli alias richiamati nei sorgenti attivi della guida
o nella bibliografia, tramite `usera`, `\linkbreve` o `\hrefbreve`.
Gli alias aggiuntivi restano disponibili sul sito e vengono comunque verificati;
non modificano la Sitografia né richiedono di rigenerarla per superare `--check`,
purché il registro rimanga valido e coerente con la bibliografia.
Le modifiche restano nel checkout di lavoro, senza commit automatici.
Questo controllo non compila né pubblica la guida e non abilita la pubblicazione.

## Pubblicazione del libro

La compilazione e pubblicazione automatica di una versione in lavorazione parte
solo per i push su `main` che modificano `book/`. Modifiche al sito, ai redirect,
agli script o ai font esterni a `book/` non la avviano. Per verificare questi
ultimi cambiamenti, avviare manualmente **Libro - verifica o pubblica** in
modalità **verifica**; per una versione consigliata usare **consigliata**,
indicando numero di versione e conferma di pubblicazione.

La home nasconde una versione in lavorazione già superata dalla consigliata
oppure con lo stesso contenuto di `book/`, anche se il commit complessivo è
diverso. Le versioni nascoste restano nell'archivio e nei conteggi dei download.

La rimozione di una release pubblicata avvia **Refresh site after removing a
release**, che ripubblica il sito da `main` senza compilare il libro. Il link
scompare al termine della pubblicazione del sito, non immediatamente. Per una
release il cui tag non contiene questo workflow, oppure per aggiornare
manualmente elenco e conteggi, avviare **Deploy site** da `main`.

**Deploy site** aggiorna automaticamente il catalogo e ripubblica il sito
anche al minuto 17 di ogni ora, senza creare commit, compilare il libro o
pubblicare nuovi PDF. I conteggi mostrati sono quelli letti da GitHub durante
l'ultima pubblicazione completata, non sono in tempo reale.

La pianificazione può subire ritardi. Nei repository pubblici GitHub la
disattiva dopo 60 giorni senza attività nel repository: in quel caso
riabilitare **Deploy site** dalla scheda **Actions**. Per i limiti della
pianificazione consultare la
[documentazione di GitHub](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## Verifica della versione dal PDF

Il pulsante nella guida apre l'indirizzo permanente
`https://informaticainclasse.it/aggiornamenti/#v=v1.0.0`, con il numero della
copia al posto di `v1.0.0`. Sono accettati sia `v1.0.0` sia `1.0.0`.

La pagina usa lo stesso catalogo pubblico dei download della home, aggiornato
dal workflow del sito. Il confronto avviene nel browser e riguarda soltanto
le versioni consigliate presenti nel catalogo: corrente, precedente oppure
non riconosciuta. Una bozza o una versione assente non viene dichiarata
aggiornata. Senza JavaScript restano visibili numero, data e download della
versione consigliata, quando disponibile, per il confronto manuale.

La pagina non crea release, non abilita la pubblicazione e non include PDF o
sorgenti del libro. Finché non sono pubblicate versioni consigliate, segnala
che non è ancora possibile confrontare la copia. Non aggiunge richieste di
rete, cookie o contatori per il controllo della versione.
