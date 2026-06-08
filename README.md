# Insegnare Informatica

Sito pubblico del libro *Insegnare Informatica*, una guida per docenti del primo ciclo dedicata all'informatica nella scuola primaria.

Il sito è pubblicato con MkDocs Material all'indirizzo:

<https://insegnareinformatica.github.io/>

## Contenuti del sito

- presentazione del libro;
- origine del progetto editoriale;
- sintesi dei principali contenuti didattici;
- risorse e collegamenti utili;
- contatti degli autori.

## Sviluppo locale

Installare le dipendenze:

```bash
python -m pip install -r requirements.txt
```

Avviare l'anteprima locale:

```bash
mkdocs serve
```

Verificare la build:

```bash
mkdocs build --strict
```

## Pubblicazione

La pubblicazione del sito avviene tramite GitHub Pages a ogni push sul branch `main`.

Il repository contiene solo il sito statico. Il libro completo e i materiali non ancora pubblici non sono inclusi.
