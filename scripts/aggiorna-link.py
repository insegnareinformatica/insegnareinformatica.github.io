#!/usr/bin/env python3
"""Genera la sitografia e controlla la coerenza dei link brevi della guida."""

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

try:
    import yaml
except ImportError:
    sys.exit("Manca PyYAML. Installarlo nell'ambiente Python: python3 -m pip install PyYAML")

SITE_ROOT = Path(__file__).resolve().parents[1]
ROOT = SITE_ROOT / "book"
SLUG = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*\Z")
DIRECT_URL = re.compile(r"\\(?:urloriginale|hreforiginale)\s*\{")
ALIAS = re.compile(r"\\(?:linkbreve|hrefbreve)\s*\{([^{}]*)\}")
LITERAL_URL = re.compile(r"https?://[^\s{}<>]+|www\.[^\s{}<>]+", re.IGNORECASE)
INFRA_DEFINITION = re.compile(
    r"\\(?:newcommand|renewcommand|providecommand|DeclareRobustCommand)\*?"
    r"\s*\{\\(?:linkbreve|hrefbreve)\}\s*(?:\[[^\]]*\]\s*)*\{"
)


class Invalid(ValueError):
    pass


def yaml_mapping(node, location):
    """Legge i nodi senza costruire oggetti o eseguire tag di MkDocs."""
    if not isinstance(node, yaml.MappingNode) or node.tag != "tag:yaml.org,2002:map":
        raise Invalid(f"{location}: attesa una mappa YAML")
    result = {}
    for key_node, value_node in node.value:
        if not isinstance(key_node, yaml.ScalarNode) or key_node.tag != "tag:yaml.org,2002:str":
            raise Invalid(f"{location}: chiave YAML non testuale, riga {key_node.start_mark.line + 1}")
        key = key_node.value
        if key in result:
            raise Invalid(f"{location}: chiave YAML duplicata {key!r}, riga {key_node.start_mark.line + 1}")
        result[key] = value_node
    return result


def load_redirects(path):
    # compose restituisce soltanto nodi YAML: !ENV e !!python/name presenti
    # altrove nel mkdocs.yml non vengono interpretati o eseguiti.
    config = yaml_mapping(yaml.compose(path.read_text(encoding="utf-8"), Loader=yaml.SafeLoader), str(path))
    plugin_nodes = config.get("plugins")
    if isinstance(plugin_nodes, yaml.SequenceNode):
        plugins = []
        for node in plugin_nodes.value:
            if isinstance(node, yaml.MappingNode):
                plugin = yaml_mapping(node, f"{path}, plugins")
                if "redirects" in plugin:
                    plugins.append(plugin["redirects"])
    elif isinstance(plugin_nodes, yaml.MappingNode):
        plugin = yaml_mapping(plugin_nodes, f"{path}, plugins")
        plugins = [plugin["redirects"]] if "redirects" in plugin else []
    else:
        raise Invalid(f"{path}: atteso plugins come elenco o mappa")
    if len(plugins) != 1:
        raise Invalid(f"{path}: atteso un solo plugin redirects")
    redirects = yaml_mapping(plugins[0], f"{path}, redirects")
    maps = yaml_mapping(redirects.get("redirect_maps"), f"{path}, redirect_maps")
    if not maps:
        raise Invalid(f"{path}: redirect_maps deve essere una mappa non vuota")
    result, cases, destinations = {}, {}, {}
    for key, node in maps.items():
        if not key.endswith(".md") or not SLUG.fullmatch(key[:-3]):
            raise Invalid(f"{path}: chiave non valida {key!r}; usare un alias semplice seguito da .md")
        slug = key[:-3]
        if slug.casefold() in cases:
            raise Invalid(f"{path}: alias distinti solo per maiuscole: {cases[slug.casefold()]} / {slug}")
        cases[slug.casefold()] = slug
        if not isinstance(node, yaml.ScalarNode) or node.tag != "tag:yaml.org,2002:str":
            raise Invalid(f"{path}: la destinazione di {slug} deve essere un URL letterale, senza tag YAML")
        target = node.value
        if not target or re.search(r"[\s\\{}]", target):
            raise Invalid(f"{path}: URL non valido per {slug}: {target!r}")
        try:
            parts = urlsplit(target)
        except ValueError as exc:
            raise Invalid(f"{path}: URL non valido per {slug}: {exc}") from exc
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise Invalid(f"{path}: destinazione di {slug} non è un URL HTTP(S) assoluto")
        if target in destinations:
            raise Invalid(f"{path}: destinazione duplicata per {destinations[target]} e {slug}")
        destinations[target] = slug
        result[slug] = target
    return result


def escaped(text, offset):
    start = offset
    while start > 0 and text[start - 1] == "\\":
        start -= 1
    return (offset - start) % 2 == 1


def group(text, start, opening="{", closing="}"):
    """Legge un gruppo bilanciato preservandone contenuto e escape TeX."""
    if start >= len(text) or text[start] != opening:
        raise Invalid("Gruppo non valido nel sorgente")
    depth, pos = 1, start + 1
    while pos < len(text):
        if not escaped(text, pos):
            if text[pos] == opening:
                depth += 1
            elif text[pos] == closing:
                depth -= 1
                if depth == 0:
                    return text[start + 1:pos], pos + 1
        pos += 1
    raise Invalid("Gruppo non chiuso nel sorgente")


def strip_comments(text):
    """Rimuove i commenti TeX, mantenendo righe e offset per la diagnostica."""
    chars = list(text)
    pos = 0
    while pos < len(text):
        if text[pos] == "%" and not escaped(text, pos):
            end = text.find("\n", pos)
            if end < 0:
                end = len(text)
            chars[pos:end] = " " * (end - pos)
            pos = end
        pos += 1
    return "".join(chars)


def mask_infrastructure(text):
    chars = list(text)
    for definition in INFRA_DEFINITION.finditer(text):
        start = definition.end() - 1
        _, end = group(text, start)
        for url in re.finditer(r"https://informaticainclasse\.it/#1", text[start:end]):
            left, right = start + url.start(), start + url.end()
            chars[left:right] = " " * (right - left)
    return "".join(chars)


def check_aliases(text, name, redirects, errors):
    for match in ALIAS.finditer(text):
        slug = match.group(1).strip()
        if re.fullmatch(r"#[1-9]", slug):
            continue  # Argomento parametrico nel corpo di una macro.
        if slug not in redirects:
            line = text.count("\n", 0, match.start()) + 1
            errors.append(f"{name}:{line}: alias non definito {slug!r}")


def read_bibliography(text):
    """Legge le voci e i campi letterali usati in references.bib.

    Le graffe possono essere annidate; percentuali nei campi URL non sono
    commenti. Le concatenazioni BibTeX sono rifiutate, evitando verifiche parziali.
    """
    entries = []
    pos = 0
    while match := re.search(r"(?m)^\s*@([A-Za-z]+)\s*\{", text[pos:]):
        kind = match.group(1).casefold()
        start = pos + match.end() - 1
        body, pos = group(text, start)
        if kind in ("comment", "preamble", "string"):
            continue
        key, comma, body = body.partition(",")
        if not comma:
            raise Invalid("references.bib: voce senza campi")
        key = key.strip()
        fields, cursor = {}, 0
        while cursor < len(body):
            spacer = re.match(r"(?:\s|,|%[^\n]*(?:\n|$))*", body[cursor:])
            cursor += spacer.end()
            if cursor == len(body):
                break
            field = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", body[cursor:])
            if not field:
                raise Invalid(f"references.bib, {key}: sintassi non supportata vicino a {body[cursor:cursor + 40]!r}")
            name = field.group(1).casefold()
            cursor += field.end()
            if cursor >= len(body):
                raise Invalid(f"references.bib, {key}: campo {name} senza valore")
            if body[cursor] == "{":
                value, cursor = group(body, cursor)
            elif body[cursor] == '"':
                start = cursor + 1
                cursor = start
                while cursor < len(body) and (body[cursor] != '"' or escaped(body, cursor)):
                    cursor += 1
                if cursor == len(body):
                    raise Invalid(f"references.bib, {key}: virgolette non chiuse")
                value = body[start:cursor]
                cursor += 1
            else:
                value_match = re.match(r"[^,\s]+", body[cursor:])
                if not value_match:
                    raise Invalid(f"references.bib, {key}: campo {name} senza valore")
                value = value_match.group()
                cursor += value_match.end()
            if name in fields:
                raise Invalid(f"references.bib, {key}: campo duplicato {name}")
            fields[name] = value
        entries.append((key, fields))
    if not entries:
        raise Invalid("references.bib: nessuna voce riconosciuta")
    return entries


def unescape_url(value):
    # Gli escape tipografici non fanno parte dell'URL; nessuna normalizzazione
    # di maiuscole, schema, slash finale, query, frammento o percent-encoding.
    return re.sub(r"\\([%#&_{}])", r"\1", value)


def http_url_error(value):
    if not value or re.search(r"[\s\\{}]", value):
        return "URL non valido"
    try:
        parts = urlsplit(value)
    except ValueError:
        return "URL non valido"
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return "atteso un URL HTTP(S) assoluto"
    return None


def mask_direct_urls(text, name, errors):
    """Ammette solo il primo argomento delle macro per URL originali."""
    chars = list(text)
    for match in DIRECT_URL.finditer(text):
        start = match.end() - 1
        value, end = group(text, start)
        if not re.fullmatch(r"#[1-9]", value):
            error = http_url_error(unescape_url(value))
            if error:
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"{name}:{line}: {error} in {match.group().rstrip('{')}: {value!r}")
        # Le etichette di hreforiginale e il testo successivo restano soggetti
        # al controllo. Un primo argomento invalido è già un errore bloccante.
        for pos in range(start + 1, end - 1):
            if chars[pos] != "\n":
                chars[pos] = " "
    return "".join(chars)


def check_urls(text, name, errors, infrastructure=False):
    masked = mask_direct_urls(text, name, errors)
    if infrastructure:
        masked = mask_infrastructure(masked)
    for match in LITERAL_URL.finditer(masked):
        line = text.count("\n", 0, match.start()) + 1
        errors.append(f"{name}:{line}: URL letterale da sostituire: {match.group()}")


def source_paths(root, source="main.tex"):
    """Sorgenti attivi e moduli della guida; mai copie locali o prodotti di build."""
    root = root.resolve()
    pending = [root / source]
    pending.extend(sorted(root.glob("cap[1-9].tex")))
    if (root / "utils.tex").exists():
        pending.append(root / "utils.tex")
    if (root / "utils").is_dir():
        pending.extend(sorted((root / "utils").rglob("*.tex")))
    excluded = {root / "sitografia.tex", root / "sitografia-elenco.tex"}
    seen = set()
    while pending:
        path = pending.pop().resolve()
        if path in seen or path in excluded:
            continue
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise Invalid(f"Inclusione TeX esterna alla guida: {path}") from exc
        seen.add(path)
        text = strip_comments(path.read_text(encoding="utf-8"))
        for match in re.finditer(r"\\(?:input|include)\s*\{([^{}]+)\}", text):
            name = match.group(1).strip()
            if "\\" in name or "#" in name:
                continue  # Nome parametrico nel corpo di una macro.
            included = root / name
            if not included.suffix:
                included = included.with_suffix(".tex")
            pending.append(included)
    return sorted(seen)


def validate_sources(root, redirects, source="main.tex"):
    errors = []
    by_destination = {target: slug for slug, target in redirects.items()}
    for path in source_paths(root, source):
        name = path.relative_to(root.resolve()).as_posix()
        text = strip_comments(path.read_text(encoding="utf-8"))
        check_aliases(text, name, redirects, errors)
        check_urls(text, name, errors, infrastructure=True)
    bib = (root / "references.bib").read_text(encoding="utf-8")
    for key, fields in read_bibliography(bib):
        for name, value in fields.items():
            if name != "url":
                active = strip_comments(value)
                location = f"references.bib, {key}, {name}"
                check_aliases(active, location, redirects, errors)
                check_urls(active, location, errors)
        if "url" not in fields:
            if "usera" in fields:
                errors.append(f"references.bib, {key}: usera presente senza url")
            continue
        target = unescape_url(fields["url"])
        error = http_url_error(target)
        if error:
            errors.append(f"references.bib, {key}: {error} nel campo url")
        expected = by_destination.get(target)
        slug = fields.get("usera", "").strip()
        if expected is None:
            if "usera" in fields:
                errors.append(f"references.bib, {key}: rimuovere usera, la destinazione non è nel registro YAML")
        elif not slug:
            errors.append(f"references.bib, {key}: manca usera={{{expected}}} per la destinazione nel registro YAML")
        elif slug not in redirects:
            errors.append(f"references.bib, {key}: usera non definito {slug!r}")
        elif slug != expected:
            errors.append(f"references.bib, {key}: url diverso dalla destinazione di {slug}; usare usera={{{expected}}}")
    return errors


def render(redirects):
    # Il layout appartiene al generatore: sitografia.tex è un file completo,
    # pronto per LuaLaTeX/Overleaf, senza importazioni o dipendenze da Python.
    lines = [r"""% Generato da aggiorna-link.py a partire dal registro YAML dei redirect.
% Non modificare a mano: rigenerare e conservare questo file nel repository.
% Capitolo finale non numerato; compare nell'indice e nei segnalibri PDF.
\chapterimage{chapter-sitografia.png}
\chapter*{Sitografia}
\addcontentsline{toc}{chapter}{Sitografia}
\markboth{\sffamily\normalsize\bfseries Sitografia}{}
\label{sitografia}

Gli indirizzi brevi usati nel testo, nelle note, nei crediti e nelle bibliografie
sono raccolti qui in ordine alfabetico, accanto alle rispettive destinazioni
complete. Puoi digitare gli indirizzi brevi così come sono stampati, rispettando
le maiuscole presenti nei nomi, per esempio \texttt{codeA}.

\begingroup
\footnotesize
\urlstyle{guida}
% Mantiene unito ://, lasciando spezzabile il resto degli URL.
\appto\UrlNoBreaks{\do\:}
\setlength{\tabcolsep}{5pt}
\renewcommand{\arraystretch}{1.15}
\begin{longtable}{@{}>{\raggedright\arraybackslash}p{.46\textwidth}>{\raggedright\arraybackslash}p{\dimexpr.54\textwidth-10pt\relax}@{}}
\textbf{Indirizzo breve} & \textbf{Destinazione completa}\\
\hline
\endfirsthead
\textbf{Indirizzo breve} & \textbf{Destinazione completa}\\
\hline
\endhead
\hline
\multicolumn{2}{r}{\emph{Continua nella pagina seguente}}\\
\endfoot
\hline
\endlastfoot"""]
    for slug in sorted(redirects, key=str.casefold):
        # La chiamata diretta a \\url non è racchiusa in una macro esterna:
        # xurl/hyperref possono trattare &, _, ~ e gli altri caratteri dell'URL.
        target = redirects[slug].replace("%", r"\%").replace("#", r"\#")
        lines.append(r"\linkbreve{" + slug + r"} & \url{" + target + r"} \\[4pt]")
    lines.extend([
        r"\\",
        r"\end{longtable}",
        r"\endgroup",
    ])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="cartella dei sorgenti (predefinita: book/ del sito)")
    parser.add_argument("--redirects", type=Path, default=SITE_ROOT / "mkdocs.yml", help="registro YAML (predefinito: mkdocs.yml del sito)")
    parser.add_argument("--source", type=Path, default=Path("main.tex"), help="sorgente principale relativo a --root (predefinito: main.tex)")
    parser.add_argument("--allow-missing-book", action="store_true", help="verifica solo il registro se i sorgenti del libro non sono ancora presenti")
    parser.add_argument("--check", action="store_true", help="controlla anche che sitografia.tex sia aggiornato, senza scrivere file")
    args = parser.parse_args()
    try:
        root = args.root.expanduser().resolve()
        registry = args.redirects.expanduser().resolve()
        redirects = load_redirects(registry)
        if args.source.is_absolute() or ".." in args.source.parts or args.source.suffix != ".tex":
            raise Invalid("--source deve essere un percorso .tex relativo alla cartella dei sorgenti")
        source = (root / args.source).resolve()
        if not source.is_relative_to(root):
            raise Invalid("Il sorgente principale è esterno alla guida")
        if args.allow_missing_book and not source.is_file():
            partial = any(root.rglob("*.tex")) or any(root.rglob("*.bib"))
            if partial:
                raise Invalid(f"Sorgenti incompleti: manca {source}")
            print(f"Registro verificato: {len(redirects)} link brevi. Sorgenti del libro assenti: generazione saltata.")
            return 0
        errors = validate_sources(root, redirects, args.source)
        generated = render(redirects)
        output = root / "sitografia.tex"
        encoded = generated.encode("utf-8")
        if args.check and (not output.exists() or output.read_bytes() != encoded):
            errors.append("sitografia.tex assente o non aggiornato: rieseguire il generatore senza --check, con gli stessi percorsi")
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        if not args.check:
            output.write_bytes(encoded)
        print(f"{'Verifica riuscita' if args.check else 'Sitografia aggiornata'}: {len(redirects)} link brevi.")
        return 0
    except (Invalid, OSError, yaml.YAMLError) as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
