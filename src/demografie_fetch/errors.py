"""Fehlerklassen mit Bezug zum Exit-Code."""

from __future__ import annotations


class FetchError(Exception):
    """Fehler einer Quelle; der Lauf ueber die Konfiguration geht weiter."""

    exit_code = 1


class InputError(FetchError):
    """Eingabe unklar (z. B. mehrere Tabellen, unbekannter Auswahlwert)."""

    exit_code = 2


class UnsupportedSourceError(FetchError):
    """Quelle erkannt oder unbekannt, aber (noch) nicht abrufbar."""

    exit_code = 2


class BlockedError(FetchError):
    """Server verweigert den Zugriff (401/403); wird nicht umgangen."""

    exit_code = 2


class FormatError(FetchError):
    """Antwort hat nicht den erwarteten Aufbau."""

    exit_code = 1
