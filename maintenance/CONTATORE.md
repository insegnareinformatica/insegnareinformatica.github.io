# Contatore della home

Percorso concordato: https://lodi.ml/insegnareinformatica/counter.php.
Il file da caricare e' ../server/home-counter/counter.php.
GitHub Pages non esegue PHP: questo file va sullo stesso hosting PHP gia'
usato per lodi.ml/infonin, in una cartella separata.

Stato al 27 settembre 2026: file caricato da Michael e collaudo remoto riuscito.
Entrambi i domini autorizzati funzionano; quattro aperture di prova hanno
portato il totale a 4. Le richieste respinte e OPTIONS non lo incrementano.
Il 28 settembre 2026 Michael ne ha autorizzato l'attivazione sul sito.
HOME_COUNTER_URL e' stata impostata; il successivo Deploy site pubblica il contatore.

## Cosa conta

Ogni apertura della home, incluse riaperture e ricaricamenti, aggiunge uno.
Passare a Contenuti o a una sezione della stessa home non aggiunge nulla.
Non si tratta di sessioni o visitatori unici. I browser che bloccano la richiesta
non vengono contati; anche richieste automatiche possono aumentare il totale.

Il PHP conserva solo un numero in counter.txt. Non scrive IP, identificatori,
sessioni, referrer o cronologie e non imposta cookie. I log dell'hosting sono
separati e dipendono dalla configurazione del server.
Il browser usa credentials: omit e referrerPolicy: no-referrer.
Il server vede comunque i dati necessari alla connessione, incluso l'IP.

## Installazione

1. Creare la cartella insegnareinformatica sul proprio hosting lodi.ml.
2. Caricare soltanto counter.php nella cartella.
3. Verificare PHP 8 su un sistema a 64 bit e consentire al processo PHP
   di scrivere counter.txt. Non usare permessi 777.
4. Non copiare il vecchio counter.txt di infonin. Alla prima chiamata valida
   il nuovo contatore parte da uno. Conservarlo nei caricamenti successivi:
   il file contiene il totale e non va sostituito.
5. Verificare la chiamata con il comando sotto.
6. Su GitHub, Settings > Secrets and variables > Actions > Variables, creare:

       HOME_COUNTER_URL = https://lodi.ml/insegnareinformatica/counter.php

7. Avviare manualmente Deploy site.

Verifica del PHP, che incrementa il nuovo contatore di una unita':

    curl --fail --header 'Origin: https://informaticainclasse.it' https://lodi.ml/insegnareinformatica/counter.php

Aprire direttamente counter.php nel browser restituisce 403 perche' manca
l'origine ammessa. Non e' un errore della connessione dal sito.

## CORS e domini

Il permesso CORS e' configurato nel PHP su lodi.ml. Non richiede modifiche ai
DNS o interventi dei tecnici UniTN. Sono ammesse queste origini HTTPS:

- https://informaticainclasse.it
- https://insegnareinformatica.github.io

HTTP, sottodomini www, siti locali e origini diverse non sono abilitati.
Se servira' un'altra origine, va concordata e aggiunta sia al PHP sia al
controllo JavaScript. I DNS e HTTPS devono gia' funzionare per il dominio scelto.

CORS limita la lettura della risposta da altre pagine web, ma non e'
un'autenticazione: un client non-browser puo' simulare l'intestazione Origin.
Il contatore e' orientativo e non una misura certificata di persone reali.

## Sviluppo e guasti

La variabile HOME_COUNTER_URL e' vuota per impostazione predefinita:
nessun contatore viene inserito nella pagina prima dell'attivazione.
Anche se la variabile e' impostata, localhost e gli altri indirizzi di anteprima
non chiamano il server. Solo la home carica lo script del contatore.

Se il PHP non risponde, il numero viene nascosto e il sito continua a funzionare.
Non viene mostrato uno zero inventato. Un counter.txt corrotto causa un errore
anziche' un azzeramento silenzioso. Il file viene creato e aggiornato sotto lock.

Per disattivare il contatore, rimuovere la variabile e ripubblicare il sito.
Non vengono usati GoatCounter, servizi di analytics o contatori ospitati da terzi.
