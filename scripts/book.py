"""Prepare book publication and collect public download totals at build time."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "insegnareinformatica/insegnareinformatica.github.io"
VERSION = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
WORK_TAG = re.compile(r"lavorazione-[0-9]+-[0-9]+")
ASSET_NAME = "insegnare-informatica.pdf"


def configuration():
    data = json.loads((ROOT / "config/book.json").read_text())
    for key in ("source", "version_file"):
        path = Path(data[key])
        if any(char in data[key] for char in ("\n", "\r", "\0")):
            raise ValueError("Invalid character in " + key)
        if path.is_absolute() or ".." in path.parts or path.parts[0] != "book":
            raise ValueError(key + " must be a relative path inside book/")
    if not data["source"].endswith(".tex"):
        raise ValueError("The book source must be a .tex file")
    if data["engine"] not in ("lualatex", "pdflatex", "xelatex"):
        raise ValueError("Unsupported LaTeX engine")
    if data["asset_name"] != ASSET_NAME:
        raise ValueError("Keep the documented PDF asset name")
    return data


def publication_plan(env):
    event = env.get("GITHUB_EVENT_NAME")
    if event not in ("push", "workflow_dispatch"):
        raise ValueError("Only main pushes and manual runs are supported")
    if env.get("GITHUB_REF") != "refs/heads/main":
        raise ValueError("Run this workflow from main")
    mode = "in-lavorazione" if event == "push" else env.get("BOOK_MODE", "verifica")
    if mode not in ("verifica", "in-lavorazione", "consigliata"):
        raise ValueError("Unknown publication mode")
    if mode != "verifica":
        if env.get("BOOK_PUBLICATION_ENABLED") != "true":
            raise ValueError("Publication is disabled: BOOK_PUBLICATION_ENABLED must be true")
        if event == "workflow_dispatch" and env.get("CONFIRM_PUBLICATION") != "true":
            raise ValueError("Explicit publication confirmation is required")
    version = env.get("BOOK_VERSION", "").strip()
    if mode == "consigliata":
        version = version if version.startswith("v") else "v" + version
        if not VERSION.fullmatch(version):
            raise ValueError("Enter a version such as 1.0.0")
    else:
        version = ""
    return {"mode": mode, "version": version}


def api(path, *, method="GET", body=None, binary=None):
    token = os.environ.get("GH_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "insegnare-informatica-publication",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    host = "https://uploads.github.com" if binary is not None else "https://api.github.com"
    data = binary
    if binary is not None:
        headers["Content-Type"] = "application/pdf"
    elif body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    request = Request(host + "/repos/" + REPOSITORY + path,
                      headers=headers, method=method, data=data)
    with urlopen(request, timeout=120) as response:
        payload = response.read()
    return json.loads(payload) if payload else None


def all_releases():
    releases = []
    page = 1
    while True:
        batch = api("/releases?per_page=100&page=" + str(page))
        if not isinstance(batch, list):
            raise ValueError("Invalid releases response")
        releases.extend(batch)
        if len(batch) < 100:
            return releases
        page += 1


def book_tree_id(commit):
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid source commit")
    response = api("/git/trees/" + commit)
    if (not isinstance(response, dict) or response.get("truncated") is not False
            or not isinstance(response.get("tree"), list)):
        raise ValueError("Incomplete source tree")
    matches = [entry.get("sha") for entry in response["tree"]
               if isinstance(entry, dict) and entry.get("path") == "book"
               and entry.get("type") == "tree"]
    if (len(matches) != 1 or not isinstance(matches[0], str)
            or not re.fullmatch(r"[0-9a-f]{40}", matches[0])):
        raise ValueError("Missing or invalid book/ tree")
    return matches[0]


def catalog(releases, now=None, compare_commits=None, get_book_tree=None):
    stable, working = [], []
    for release in releases:
        if release.get("draft"):
            continue
        tag = release.get("tag_name", "")
        is_stable = bool(VERSION.fullmatch(tag)) and not release.get("prerelease")
        is_working = bool(WORK_TAG.fullmatch(tag)) and release.get("prerelease") is True
        if not (is_stable or is_working):
            continue
        matches = [asset for asset in release.get("assets", [])
                   if asset.get("name") == ASSET_NAME and asset.get("state") == "uploaded"]
        if not matches:
            continue
        if len(matches) != 1:
            raise ValueError("Ambiguous book asset")
        asset = matches[0]
        count = asset.get("download_count")
        if type(count) is not int or count < 0 or asset.get("size", 0) < 5:
            raise ValueError("Invalid PDF download metadata")
        date = release.get("published_at")
        datetime.fromisoformat(date.replace("Z", "+00:00"))
        entry = {
            "version": tag,
            "published_at": date,
            "downloads": count,
            "url": "https://github.com/" + REPOSITORY + "/releases/download/" +
                   quote(tag, safe="") + "/" + ASSET_NAME,
        }
        source = release.get("target_commitish", "")
        if isinstance(source, str) and re.fullmatch(r"[0-9a-f]{40}", source):
            entry["source_commit"] = source
        (stable if is_stable else working).append(entry)
    stable.sort(key=lambda item: tuple(map(int, VERSION.fullmatch(item["version"]).groups())),
                reverse=True)
    working.sort(key=lambda item: item["published_at"], reverse=True)
    superseded = False
    if stable and working:
        base = working[0].get("source_commit")
        head = stable[0].get("source_commit")
        if base and head:
            # Publication time can differ from source order, especially on reruns.
            superseded = base == head
            if not superseded and compare_commits is not None:
                try:
                    comparison = compare_commits("/compare/" + base + "..." + head)
                    superseded = (isinstance(comparison, dict) and
                                  comparison.get("status") in ("ahead", "identical"))
                except (OSError, ValueError) as error:
                    print("Cannot compare book sources; keeping the working version visible: " +
                          str(error), file=sys.stderr)
            if not superseded and get_book_tree is not None:
                try:
                    # Compare complete book/ trees, not the API's limited changed-file list.
                    working_tree = get_book_tree(base)
                    superseded = bool(working_tree) and working_tree == get_book_tree(head)
                except (OSError, ValueError) as error:
                    print("Cannot compare book content; keeping the working version visible: " +
                          str(error), file=sys.stderr)
    return {
        "updated_at": now or datetime.now(timezone.utc).isoformat(),
        "stable": stable,
        "working": working,
        "working_superseded": superseded,
        "total_downloads": sum(item["downloads"] for item in stable + working),
    }


def check_pdf(path):
    if not path.is_file() or not 5 < path.stat().st_size < 2 * 1024 ** 3:
        raise ValueError("Missing or invalid PDF")
    with path.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise ValueError("The compilation output is not a PDF")


def prepare():
    plan = publication_plan(os.environ)
    config = configuration()
    source = ROOT / config["source"]
    if not source.is_file():
        raise ValueError("Add the approved LaTeX sources at " + config["source"])
    flags = {"lualatex": "-lualatex", "pdflatex": "-pdf", "xelatex": "-xelatex"}
    values = dict(plan, directory=str(source.parent.relative_to(ROOT)), tex_file=source.name,
                  engine_flag=flags[config["engine"]])
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        for key, value in values.items():
            output.write(key + "=" + value + "\n")
    print("Book operation: " + plan["mode"])


def links():
    """Validate redirects and regenerate the sitography only in this checkout."""
    source = ROOT / configuration()["source"]
    subprocess.run([
        sys.executable, str(ROOT / "scripts/aggiorna-link.py"),
        "--root", str(source.parent),
        "--source", source.name,
        "--redirects", str(ROOT / "mkdocs.yml"),
        "--allow-missing-book",
    ], check=True)


def stamp():
    plan = publication_plan(os.environ)
    if plan["mode"] == "verifica":
        return
    path = ROOT / configuration()["version_file"]
    if not path.exists():
        print("No version.tex: the release number will appear on the site only.")
        return
    version = plan["version"] or "in lavorazione " + os.environ["GITHUB_SHA"][:12]
    today = datetime.now(timezone.utc).date()
    months = ("gennaio febbraio marzo aprile maggio giugno luglio agosto settembre "
              "ottobre novembre dicembre").split()
    date = str(today.day) + " " + months[today.month - 1] + " " + str(today.year)
    text = path.read_text()
    for name, value in (("guideversion", version), ("guideversiondate", date)):
        pattern = r"(\\newcommand\{\\" + name + r"\}\{)[^}]+(\})"
        text, count = re.subn(pattern, lambda match: match[1] + value + match[2], text)
        if count != 1:
            raise ValueError("Review the version macros in " + str(path))
    # Only the workflow checkout is changed; no automatic source commit is made.
    path.write_text(text)


def package():
    path = (ROOT / configuration()["source"]).with_suffix(".pdf")
    check_pdf(path)
    output = ROOT / "dist" / ASSET_NAME
    output.parent.mkdir(exist_ok=True)
    shutil.copyfile(path, output)


def publish():
    plan = publication_plan(os.environ)
    if plan["mode"] == "verifica":
        raise ValueError("Verification mode cannot publish a PDF")
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise ValueError("Unexpected repository")
    sha = os.environ.get("GITHUB_SHA", "")
    if not re.fullmatch("[0-9a-f]{40}", sha):
        raise ValueError("Invalid source commit")
    stable = plan["mode"] == "consigliata"
    if not stable:
        current = api("/git/ref/heads/main")["object"]["sha"]
        if current != sha and book_tree_id(current) != book_tree_id(sha):
            print("Newer book sources are on main; this working PDF will not be published.")
            return
    if stable:
        tag = plan["version"]
    else:
        run = os.environ.get("GITHUB_RUN_ID", "") + "-" + os.environ.get("GITHUB_RUN_ATTEMPT", "")
        tag = "lavorazione-" + run
        if not WORK_TAG.fullmatch(tag):
            raise ValueError("Invalid workflow run identifier")
    path = ROOT / "dist" / ASSET_NAME
    check_pdf(path)
    releases = all_releases()
    if any(release["tag_name"] == tag for release in releases):
        raise ValueError("This version already exists, possibly as a draft. Review it first.")
    if stable:
        previous = [tuple(map(int, VERSION.fullmatch(release["tag_name"]).groups()))
                    for release in releases if VERSION.fullmatch(release["tag_name"])
                    and not release.get("draft") and not release.get("prerelease")]
        if previous and tuple(map(int, VERSION.fullmatch(tag).groups())) <= max(previous):
            raise ValueError("The recommended version must be newer than published versions")
    try:
        api("/git/ref/tags/" + tag)
    except HTTPError as error:
        if error.code != 404:
            raise
    else:
        raise ValueError("This tag already exists; it will not be overwritten")
    notes = os.environ.get("BOOK_NOTES", "").strip()
    if not stable:
        notes = "Versione in lavorazione: contiene modifiche ancora da verificare."
    notes += "\n\nSorgenti: " + sha
    draft = api("/releases", method="POST", body={
        "tag_name": tag,
        "target_commitish": sha,
        "name": ("Versione " + tag[1:]) if stable else ("In lavorazione " + sha[:12]),
        "body": notes,
        "draft": True,
        "prerelease": not stable,
        "make_latest": "false",
    })
    pdf = path.read_bytes()
    asset = api("/releases/" + str(draft["id"]) + "/assets?name=" + ASSET_NAME,
                method="POST", binary=pdf)
    if asset.get("state") != "uploaded" or asset.get("size") != len(pdf):
        raise ValueError("Upload incomplete: the release has been left as a draft")
    digest = asset.get("digest")
    if digest and digest != "sha256:" + hashlib.sha256(pdf).hexdigest():
        raise ValueError("Upload checksum mismatch: the release is still a draft")
    api("/releases/" + str(draft["id"]), method="PATCH", body={
        "draft": False, "make_latest": "true" if stable else "false",
    })
    print("Published " + tag)
    # GITHUB_TOKEN events do not trigger other workflows; dispatch explicitly.
    try:
        api("/actions/workflows/deploy-site.yml/dispatches",
            method="POST", body={"ref": "main"})
    except Exception:
        print("PDF published. Run Deploy site manually to refresh the website.", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "links", "stamp", "package", "publish", "catalog"))
    args = parser.parse_args()
    if args.command == "catalog":
        enabled = os.environ.get("BOOK_PUBLICATION_ENABLED") == "true"
        data = catalog(all_releases() if enabled else [], compare_commits=api,
                       get_book_tree=book_tree_id)
        path = ROOT / ".cache/book-releases.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        print("Download catalog updated; publication enabled: " + str(enabled))
    else:
        globals()[args.command]()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        sys.exit(str(error))
