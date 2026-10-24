#!/usr/bin/env python3
"""Zugangspruefung (Schritt 0) fuer demografie-fetch.

Prueft je Quelle aus config/sources_demografie.yaml, ob die Daten per URL
abrufbar sind (Tests T1-T8), und leitet eine vorlaeufige Zugangsklasse ab.

Regeln: lesend und hoeflich (je Test hoechstens eine Anfrage, 2 s Pause),
keine Umgehung von Logins, CAPTCHAs, Zustimmungsdialogen oder Sperren.
Tokens nur aus GENESIS_TOKEN / REGIO_TOKEN, nie im Bericht.

Aufruf:
    python probe/access_probe.py                 # lokal -> probe/report_local.json
    python probe/access_probe.py --env ci        # CI    -> probe/report_ci.json
    python probe/access_probe.py --dry-run       # nur Testplan, kein Netzwerk
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "sources_demografie.yaml"

PAUSE_S = 2.0
TIMEOUT_S = 30
EXCERPT_CHARS = 300
BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)
BBSR_REFERER = "https://www.bbsr.bund.de/"

GENESIS_BASES = {
    "genesis": "https://genesis.destatis.de/genesisWS/rest/2020/",
    "regio": "https://www.regionalstatistik.de/genesisws/rest/2020/",
}
TOKEN_ENV = {"genesis": "GENESIS_TOKEN", "regio": "REGIO_TOKEN"}

ALL_TESTS = ("T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8")
TESTS_BY_KIND = {
    "genesis": ("T1", "T2", "T6", "T7"),
    "tableau": ("T1", "T2", "T3", "T4", "T5"),
    "file": ("T1", "T2", "T8"),
}

LOGIN_HINTS = ("login", "signin", "sign-in", "anmeld", "auth/", "consent", "zustimmung")
DATA_CONTENT_TYPES = (
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats",
    "application/zip",
    "application/x-zip",
    "application/octet-stream",
)

TABLE_RE = re.compile(r"(?<![\d])(\d{5}(?:-[0-9A-Za-z]+)+)")
STAT_RE = re.compile(r"(?<![\d-])(\d{5})(?![\d-])")

# Statuswerte je Test
OK = "ok"  # Daten bzw. positiver Nachweis
ERREICHBAR = "erreichbar"  # Server antwortet, aber keine Daten
GESCHEITERT = "gescheitert"
KEIN_TOKEN = "kein_token"
NICHT_ANWENDBAR = "nicht_anwendbar"
NICHT_PRUEFBAR = "nicht_pruefbar"


@dataclass
class TestResult:
    test: str
    status: str
    http: int | None = None
    dauer_ms: int | None = None
    content_type: str | None = None
    weiterleitung: list[str] = field(default_factory=list)
    grund: str | None = None
    auszug: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceReport:
    id: str
    url: str
    art: str
    rolle: str | None
    tests: dict[str, TestResult]
    klasse: str
    grund: str | None = None


# --------------------------------------------------------------------------- Hilfen


def source_kind(src: dict[str, Any]) -> str:
    """genesis | tableau | file | unbekannt (aus Adapter bzw. Host)."""
    adapter = (src.get("adapter") or "").lower()
    if adapter in ("genesis", "tableau", "file"):
        return adapter
    host = urlsplit(src.get("url") or "").hostname or ""
    if host.endswith("genesis.destatis.de") or host.endswith("regionalstatistik.de"):
        return "genesis"
    if host.startswith("tableau."):
        return "tableau"
    path = urlsplit(src.get("url") or "").path.lower()
    if path.endswith((".csv", ".xlsx", ".xls", ".zip")):
        return "file"
    return "unbekannt"


def genesis_db(url: str) -> str:
    host = urlsplit(url).hostname or ""
    return "regio" if host.endswith("regionalstatistik.de") else "genesis"


def extract_code(url: str) -> tuple[str | None, str | None]:
    """Liefert (tabellencode, statistikcode) aus einer GENESIS-URL."""
    m = TABLE_RE.search(url)
    if m:
        return m.group(1), m.group(1)[:5]
    m = STAT_RE.search(url)
    if m:
        return None, m.group(1)
    return None, None


def plan_tests(src: dict[str, Any]) -> list[str]:
    return list(TESTS_BY_KIND.get(source_kind(src), ("T1", "T2")))


def mask(text: str, secrets: list[str]) -> str:
    for s in secrets:
        if s:
            text = text.replace(s, "***")
    return text


def excerpt(text: str, secrets: list[str], lines: int | None = None) -> str:
    if lines is not None:
        text = "\n".join(text.splitlines()[:lines])
    return mask(text[:EXCERPT_CHARS], secrets)


def looks_like_login(url: str) -> bool:
    low = url.lower()
    return any(h in low for h in LOGIN_HINTS)


def is_data_content_type(ct: str | None) -> bool:
    low = (ct or "").lower()
    return any(low.startswith(d) for d in DATA_CONTENT_TYPES)


def looks_like_csv(text: str) -> bool:
    head = text.lstrip()[:500].lower()
    if head.startswith("<") or "<html" in head:
        return False
    first = text.splitlines()[0] if text.splitlines() else ""
    return first.count(",") + first.count(";") + first.count("\t") >= 1


def classify(tests: dict[str, TestResult], env: str) -> tuple[str, str | None]:
    """Vorlaeufige Zugangsklasse fuer eine Umgebung."""
    st = {k: v.status for k, v in tests.items()}
    simple = ("T2", "T4", "T7", "T8")
    if any(st.get(t) == OK for t in simple) or (st.get("T6") == OK and st.get("T7") == OK):
        return ("A-cloud" if env == "ci" else "A-lokal"), None
    if st.get("T3") == OK:
        return "A-lokal", "nur mit Browser-Kennung/Referer"
    if st.get("T5") == OK:
        return "A-browser", None
    if KEIN_TOKEN in st.values():
        return NICHT_PRUEFBAR, "kein_token: GENESIS-/Regio-Token fehlt, Datenzugang offen"
    return "B-manuell", None


# --------------------------------------------------------------------------- Prober


class Prober:
    def __init__(self, env: str, pause: float = PAUSE_S,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.env = env
        self.pause = pause
        self._sleep = sleep
        self._last: float | None = None
        self.tokens = {db: os.environ.get(var, "") for db, var in TOKEN_ENV.items()}
        self.secrets = [t for t in self.tokens.values() if t]
        self._robots_done: dict[str, TestResult] = {}

    # Hoeflichkeit: mindestens `pause` Sekunden zwischen zwei Anfragen
    def wait(self) -> None:
        if self._last is not None:
            delta = time.monotonic() - self._last
            if delta < self.pause:
                self._sleep(self.pause - delta)
        self._last = time.monotonic()

    def _request(self, test: str, method: str, url: str,
                 headers: dict[str, str] | None = None, data: dict[str, str] | None = None,
                 lines: int | None = None) -> tuple[TestResult, requests.Response | None]:
        self.wait()
        t0 = time.monotonic()
        try:
            r = requests.request(method, url, headers=headers or {}, data=data,
                                 timeout=TIMEOUT_S, allow_redirects=True)
        except requests.RequestException as e:
            return TestResult(test, GESCHEITERT, grund=f"netzwerk: {type(e).__name__}",
                              auszug=mask(str(e)[:EXCERPT_CHARS], self.secrets)), None
        finally:
            self._last = time.monotonic()
        res = TestResult(
            test=test,
            status=ERREICHBAR if r.ok else GESCHEITERT,
            http=r.status_code,
            dauer_ms=int((time.monotonic() - t0) * 1000),
            content_type=r.headers.get("Content-Type"),
            weiterleitung=[h.headers.get("Location", "") for h in r.history][:5],
        )
        if r.history and looks_like_login(r.url):
            res.status, res.grund = GESCHEITERT, "login_oder_zustimmung"
        if method != "HEAD":
            try:
                res.auszug = excerpt(r.text, self.secrets, lines)
            except Exception:  # binaere Antwort
                res.auszug = f"<{len(r.content)} Bytes binaer>"
        if not r.ok and not res.grund:
            res.grund = f"HTTP {r.status_code}"
        return res, r

    # ---- T1
    def t1_robots(self, url: str) -> TestResult:
        parts = urlsplit(url)
        key = parts.netloc
        if key in self._robots_done:
            cached = self._robots_done[key]
            return TestResult("T1", cached.status, cached.http, cached.dauer_ms,
                              cached.content_type, grund="wie oben (gleicher Host)")
        res, _ = self._request("T1", "GET", f"{parts.scheme}://{parts.netloc}/robots.txt")
        self._robots_done[key] = res
        return res

    # ---- T2
    def t2_default(self, url: str, kind: str) -> TestResult:
        res, r = self._request("T2", "GET", url)
        if r is not None and r.ok and res.status != GESCHEITERT:
            if kind in ("file", "tableau") and (
                is_data_content_type(res.content_type)
                or (kind == "tableau" and looks_like_csv(r.text))
            ):
                res.status = OK
        return res

    def browser_headers(self) -> dict[str, str]:
        return {"User-Agent": BROWSER_UA, "Referer": BBSR_REFERER,
                "Accept-Language": "de-DE,de;q=0.9"}

    # ---- T3
    def t3_browser_headers(self, url: str) -> TestResult:
        res, r = self._request("T3", "GET", url, headers=self.browser_headers())
        if r is not None and r.ok and res.status != GESCHEITERT and (
            is_data_content_type(res.content_type)
        ):
            res.status = OK
        return res

    # ---- T4
    def t4_csv_export(self, url: str) -> TestResult:
        view = url.split("?")[0].split("#")[0].rstrip("/")
        res, r = self._request("T4", "GET", view + ".csv", headers=self.browser_headers(),
                               lines=3)
        res.details["export_url"] = view + ".csv"
        if r is not None and r.ok and res.status != GESCHEITERT:
            if looks_like_csv(r.text):
                res.status = OK
            else:
                res.grund = "Antwort ist kein CSV"
        return res

    # ---- T5
    def t5_playwright(self, url: str) -> TestResult:
        self.wait()
        res = TestResult("T5", GESCHEITERT)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            res.grund = "playwright nicht installiert"
            return res
        t0 = time.monotonic()
        boot: dict[str, Any] = {"antworten": 0, "mit_datenwoerterbuch": 0}
        try:
            with sync_playwright() as p:
                launch: dict[str, Any] = {"headless": True}
                if self.env != "ci" and os.environ.get("PROBE_CHROME_CHANNEL", "chrome"):
                    launch["channel"] = os.environ.get("PROBE_CHROME_CHANNEL", "chrome")
                try:
                    browser = p.chromium.launch(**launch)
                except Exception:
                    launch.pop("channel", None)
                    browser = p.chromium.launch(**launch)
                ctx = browser.new_context(user_agent=BROWSER_UA, locale="de-DE",
                                          extra_http_headers={"Referer": BBSR_REFERER})
                page = ctx.new_page()

                def on_response(resp: Any) -> None:
                    if "bootstrapSession" in resp.url:
                        boot["antworten"] += 1
                        try:
                            if "dataDictionary" in resp.text():
                                boot["mit_datenwoerterbuch"] += 1
                        except Exception:
                            pass

                page.on("response", on_response)
                nav = page.goto(url, wait_until="networkidle", timeout=60_000)
                res.http = nav.status if nav else None
                res.weiterleitung = [page.url] if nav and page.url != url else []
                if looks_like_login(page.url):
                    res.grund = "login_oder_zustimmung"
                else:
                    dl = page.locator(
                        "[data-tb-test-id='viz-viewer-toolbar-button-download'], "
                        "[data-tb-test-id='download-ToolbarButton']"
                    )
                    vorhanden = dl.count() > 0
                    aktiv = vorhanden and dl.first.is_enabled()
                    menue: list[str] = []
                    if aktiv:
                        dl.first.click()  # oeffnet nur das Menue, kein Download
                        page.wait_for_timeout(1500)
                        for name in ("Daten", "Kreuztabelle", "Data", "Crosstab"):
                            b = page.get_by_role("button", name=name, exact=True)
                            if b.count() > 0 and b.first.is_enabled():
                                menue.append(name)
                    res.details.update(download_schaltflaeche=vorhanden,
                                       download_aktiv=aktiv, menue_aktiv=menue)
                    if boot["mit_datenwoerterbuch"] > 0 or menue:
                        res.status = OK
                    elif res.http and res.http < 400:
                        res.status, res.grund = ERREICHBAR, "kein Datenwoerterbuch, kein Export"
                    else:
                        res.grund = f"HTTP {res.http}"
                res.auszug = mask(page.title()[:EXCERPT_CHARS], self.secrets)
                browser.close()
        except Exception as e:
            res.grund = f"browser: {type(e).__name__}: {str(e)[:150]}"
        finally:
            self._last = time.monotonic()
        res.dauer_ms = int((time.monotonic() - t0) * 1000)
        res.details["bootstrapSession"] = boot
        return res

    # ---- T6 / T7
    def _genesis_post(self, test: str, db: str, method: str,
                      params: dict[str, str]) -> tuple[TestResult, Any]:
        token = self.tokens.get(db, "")
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if token:
            headers.update(username=token, password="")
        res, r = self._request(test, "POST", GENESIS_BASES[db] + method, headers=headers,
                               data=params)
        res.details["basis_url"] = GENESIS_BASES[db]
        body: Any = None
        if r is not None:
            try:
                body = r.json()
            except ValueError:
                body = None
        if isinstance(body, dict):
            st = body.get("Status") or {}
            if isinstance(st, dict):
                res.details["genesis_status"] = {
                    "Code": st.get("Code"), "Type": st.get("Type"),
                    "Content": mask(str(st.get("Content", ""))[:200], self.secrets),
                }
        return res, body

    def t6_logincheck(self, db: str) -> TestResult:
        res, body = self._genesis_post("T6", db, "helloworld/logincheck", {})
        if not self.tokens.get(db):
            res.status, res.grund = KEIN_TOKEN, f"{TOKEN_ENV[db]} nicht gesetzt"
            return res
        if isinstance(body, dict):
            text = json.dumps(body, ensure_ascii=False).lower()
            if res.http == 200 and ("erfolgreich" in text or "success" in text):
                res.status = OK
            else:
                res.status, res.grund = GESCHEITERT, "Anmeldung nicht bestaetigt"
        return res

    def t7_catalogue(self, db: str, table: str | None, stat: str | None) -> TestResult:
        if not table and not stat:
            return TestResult("T7", GESCHEITERT, grund="kein Tabellen-/Statistikcode in URL")
        sel = table if table else f"{stat}*"
        res, body = self._genesis_post(
            "T7", db, "catalogue/tables", {"selection": sel, "area": "all", "pagelength": "50"}
        )
        res.details["selection"] = sel
        codes: list[str] = []
        if isinstance(body, dict):
            lst = body.get("List") or []
            if isinstance(lst, list):
                codes = [str(x.get("Code")) for x in lst if isinstance(x, dict)]
        res.details["treffer"] = codes[:20]
        res.details["anzahl_treffer"] = len(codes)
        if not self.tokens.get(db):
            res.status, res.grund = KEIN_TOKEN, f"{TOKEN_ENV[db]} nicht gesetzt"
        elif (table and table in codes) or (not table and codes):
            res.status = OK
        elif res.status != GESCHEITERT:
            res.status, res.grund = GESCHEITERT, "Code nicht im Katalog"
        return res

    # ---- T8
    def t8_conditional(self, url: str) -> TestResult:
        res, r = self._request("T8", "HEAD", url)
        if r is not None:
            et, lm = r.headers.get("ETag"), r.headers.get("Last-Modified")
            res.details.update(etag=bool(et), last_modified=lm)
            if r.ok and res.status != GESCHEITERT and is_data_content_type(res.content_type):
                res.status = OK
            if r.ok and not (et or lm):
                res.grund = "kein ETag/Last-Modified: Pruefsumme entscheidet"
        return res

    # ---- je Quelle
    def probe_source(self, src: dict[str, Any]) -> SourceReport:
        url = (src.get("url") or "").strip()
        kind = source_kind(src)
        planned = plan_tests(src)
        tests: dict[str, TestResult] = {
            t: TestResult(t, NICHT_ANWENDBAR) for t in ALL_TESTS if t not in planned
        }
        rep = SourceReport(id=src["id"], url=url, art=kind, rolle=src.get("rolle"),
                           tests=tests, klasse=NICHT_PRUEFBAR)
        if not url:
            for t in planned:
                tests[t] = TestResult(t, NICHT_PRUEFBAR, grund="URL fehlt")
            if kind == "tableau":  # Host-Test zeigt einen moeglichen Herkunftsfilter
                tests["T1"] = self.t1_robots("https://tableau.bbsr.bund.de/")
                tests["T1"].details["hinweis"] = "Host-Test ohne Quell-URL"
            rep.grund = "URL fehlt in der Konfiguration, bitte nachtragen"
            return rep
        host = urlsplit(url).hostname or ""
        if kind == "tableau" and (host == "bbsr.bund.de" or host.endswith(".bbsr.bund.de")) \
                and not host.startswith("tableau."):
            for t in planned:
                tests[t] = TestResult(t, NICHT_PRUEFBAR, grund="Einbettungsseite")
            rep.grund = ("Einbettungsseite auf bbsr.bund.de (Zustimmungsdialog), wird nicht "
                         "bedient; bitte die Tableau-URL (tableau.bbsr.bund.de/views/...) "
                         "eintragen")
            return rep
        if kind == "unbekannt":
            rep.grund = "Quelle nicht erkannt"
        tests["T1"] = self.t1_robots(url)
        tests["T2"] = self.t2_default(url, kind)
        if kind == "tableau":
            tests["T3"] = self.t3_browser_headers(url)
            tests["T4"] = self.t4_csv_export(url)
            tests["T5"] = self.t5_playwright(url)
        elif kind == "genesis":
            db = genesis_db(url)
            table, stat = extract_code(url)
            tests["T6"] = self.t6_logincheck(db)
            tests["T7"] = self.t7_catalogue(db, table, stat)
            tests["T7"].details.update(datenbank=db, tabelle=table, statistik=stat)
        elif kind == "file":
            tests["T8"] = self.t8_conditional(url)
        rep.klasse, grund = classify(tests, self.env)
        rep.grund = rep.grund or grund
        return rep


# --------------------------------------------------------------------------- Lauf


def load_sources(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(data.get("sources") or [])


def public_ip_info(env: str) -> dict[str, Any]:
    """Netz der Laufumgebung ohne IP; Region und Anbieter nur fuer CI (kein Privatanschluss)."""
    try:
        r = requests.get("https://ipinfo.io/json", timeout=10)
        d = r.json()
        keys = ("country", "region", "org") if env == "ci" else ("country",)
        return {k: d.get(k) for k in keys}
    except Exception:
        return {}


def run(env: str, config: Path, out: Path, only: list[str] | None = None) -> dict[str, Any]:
    prober = Prober(env)
    sources = [s for s in load_sources(config) if not only or s["id"] in only]
    reports = []
    for src in sources:
        print(f"[probe] {src['id']} ...", file=sys.stderr, flush=True)
        rep = prober.probe_source(src)
        reports.append(rep)
        summary = " ".join(f"{k}={v.status}({v.http or '-'})" for k, v in rep.tests.items()
                           if v.status != NICHT_ANWENDBAR)
        print(f"[probe]   -> {rep.klasse}: {summary}", file=sys.stderr, flush=True)
    report = {
        "umgebung": env,
        "zeit_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "plattform": platform.platform(),
        "python": platform.python_version(),
        "runner": os.environ.get("RUNNER_NAME") or None,
        "netz": public_ip_info(env),
        "tokens": {db: bool(t) for db, t in prober.tokens.items()},
        "quellen": [
            {**{k: v for k, v in asdict(r).items() if k != "tests"},
             "tests": {k: asdict(v) for k, v in r.tests.items()}}
            for r in reports
        ],
    }
    text = mask(json.dumps(report, ensure_ascii=False, indent=2), prober.secrets)
    out.write_text(text + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--env", choices=("local", "ci"),
                    default="ci" if os.environ.get("GITHUB_ACTIONS") == "true" else "local")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--only", nargs="*", help="nur diese Quell-IDs")
    ap.add_argument("--dry-run", action="store_true", help="Testplan zeigen, kein Netzwerk")
    a = ap.parse_args(argv)
    if a.dry_run:
        for s in load_sources(a.config):
            url = s.get("url") or ""
            tests = plan_tests(s) if url else ["(nicht pruefbar: URL fehlt)"]
            print(f"{s['id']:<28} {source_kind(s):<9} {' '.join(tests)}")
        return 0
    out = a.out or ROOT / "probe" / f"report_{a.env}.json"
    run(a.env, a.config, out, a.only)
    print(f"[probe] Bericht: {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
