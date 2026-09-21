# =============================================================================
# pyscript: device_list_updater.py
# -----------------------------------------------------------------------------
# Fünf Aufgaben:
#   1. Befüllt input_select.device_csv_auswahl automatisch mit den Namen
#      aller in Home Assistant registrierten Geräte.
#   2. Filtert diese Liste live anhand von input_text.device_csv_filter
#      (Teilstring-Suche, ohne Groß-/Kleinschreibung) und zeigt die Treffer
#      zusätzlich als reine Markdown-Liste in sensor.device_csv_filter_
#      treffer (Attribut "liste") an – sichtbar ohne das Dropdown zu öffnen.
#   3. Schreibt bei Auswahl eines Geräts eine CSV mit dessen Entitäten nach
#      /config/www/device_entities.csv.
#   4. Berücksichtigt den Schalter input_boolean.device_csv_werte_
#      exportieren: an -> Zustände werden mit exportiert, aus -> nur
#      entity_id und Name.
#   5. Legt zusätzlich sensor.device_csv_vorschau an, dessen Attribut
#      "tabelle" eine fertige Markdown-Tabelle enthält – für eine Live-
#      Vorschau im Dashboard, ohne die CSV herunterladen zu müssen. Danach
#      werden Filter und Dropdown automatisch zurückgesetzt, damit das Tool
#      sofort wieder für die nächste Auswahl bereit ist.
#   6. input_button.device_csv_neu setzt Filter, Dropdown und CSV-Bereich
#      sofort per Klick zurück, unabhängig vom Tab/Enter-Verhalten des
#      Filterfelds.
#
# Die Filter-Trefferliste ist bewusst NICHT klickbar (kein Ersatz fürs
# Dropdown): ein früherer Versuch, Treffer über die HACS-Karte auto-entities
# als klickbare "button"-Kacheln darzustellen, scheiterte an unzuverlässiger
# Live-Aktualisierung, weil Home Assistants Template-Abhängigkeitserkennung
# Funktionsaufrufe in verschachtelten Dict-Literalen nicht zuverlässig
# erkennt. Eine reine Markdown-Karte mit state_attr() bindet dagegen direkt
# und zuverlässig – genau das nutzt diese einfachere Variante.
#
# Nutzt bewusst nur die Device-/Entity-Registry und das hass-Objekt direkt
# (kein device_id()/device_entities() – das sind reine Jinja-Template-
# Funktionen, die pyscript nicht als Python-Funktionen bereitstellt).
#
# Funktionen, die über task.executor laufen, brauchen @pyscript_compile,
# da task.executor keine pyscript-eigenen (AST-interpretierten) Funktionen
# akzeptiert, sondern nur regulär kompilierten Python-Code.
#
# Voraussetzung:
#   pyscript-Integration mit "Alle Importe erlauben" und "Home Assistant
#   als globale Variable verwenden" eingerichtet.
#
# Ablage: /config/pyscript/device_list_updater.py
# =============================================================================

import os

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er


# --- Hilfsfunktionen ----------------------------------------------------------

def _alle_geraetenamen():
    registry = dr.async_get(hass)
    namen = [
        geraet.name_by_user or geraet.name
        for geraet in registry.devices.values()
        if (geraet.name_by_user or geraet.name)
    ]
    return sorted(set(namen))


def _gefilterte_optionen(filtertext):
    alle = _alle_geraetenamen()
    if filtertext:
        filtertext = filtertext.strip().lower()
        alle = [n for n in alle if filtertext in n.lower()]
    return ["Bitte wählen"] + alle


def _geraet_anhand_name_finden(name):
    registry = dr.async_get(hass)
    for geraet in registry.devices.values():
        if (geraet.name_by_user or geraet.name) == name:
            return geraet
    return None


def _entities_fuer_geraet(device_id_wert):
    ent_reg = er.async_get(hass)
    return [
        eintrag.entity_id
        for eintrag in ent_reg.entities.values()
        if eintrag.device_id == device_id_wert
    ]


@pyscript_compile
def _csv_schreiben(pfad, inhalt):
    # Regulär kompilierte Funktion, damit sie über task.executor in einem
    # Thread laufen kann (blockierendes Datei-I/O gehört nicht in den
    # HA-Event-Loop).
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(inhalt)


# --- Teil 1: Geräteliste für den Dropdown-Helper -----------------------------

def _dropdown_optionen_setzen(optionen, filtertext=None):
    input_select.set_options(
        entity_id="input_select.device_csv_auswahl",
        options=optionen,
    )
    # Treffer (ohne "Bitte wählen") zusätzlich als reine Anzeige-Liste
    # bereitstellen – bewusst NICHT klickbar (siehe Design-Hinweis oben),
    # dafür zuverlässig live, weil eine gewöhnliche Markdown-Karte direkt
    # per state_attr() daran bindet statt über auto-entities' fragile
    # Template-Auswertung.
    # Nur bei aktivem Filtertext anzeigen – sonst würde nach einem Reset
    # (leeres Filterfeld) die komplette, ungefilterte Geräteliste angezeigt
    # und die Download-/Vorschau-Karte weit nach unten verdrängen.
    if filtertext:
        treffer = [n for n in optionen if n != "Bitte wählen"]
        liste_md = "\n".join([f"- {name}" for name in treffer]) if treffer else ""
    else:
        liste_md = ""
    state.set(
        "sensor.device_csv_filter_treffer",
        value=len(liste_md.splitlines()),
        new_attributes={
            "friendly_name": "Filter Treffer",
            "liste": liste_md,
        },
    )


@time_trigger("startup")
def geraeteliste_bei_start_aktualisieren():
    optionen = _gefilterte_optionen(None)
    _dropdown_optionen_setzen(optionen, filtertext=None)
    log.info(f"Geräteliste aktualisiert: {len(optionen) - 1} Geräte gefunden")


@service
def device_liste_aktualisieren():
    """Manuell aufrufbarer Service: pyscript.device_liste_aktualisieren"""
    filtertext = state.get("input_text.device_csv_filter")
    optionen = _gefilterte_optionen(filtertext)
    _dropdown_optionen_setzen(optionen, filtertext=filtertext)


# --- Teil 1b: Geräteliste anhand des Filters filtern -------------------------

@state_trigger("input_text.device_csv_filter")
def geraeteliste_bei_filter_aktualisieren():
    filtertext = state.get("input_text.device_csv_filter")
    optionen = _gefilterte_optionen(filtertext)
    _dropdown_optionen_setzen(optionen, filtertext=filtertext)
    log.info(f"Geräteliste gefiltert nach '{filtertext}': {len(optionen) - 1} Treffer")

    # Sobald aktiv wieder getippt wird (nicht bei unserem eigenen Reset auf
    # leeren Filtertext direkt nach einem Export), ist die zuletzt
    # exportierte CSV nicht mehr die aktuelle Auswahl – Download-Link und
    # Vorschau-Tabelle blenden wir daher aus, bis das nächste Gerät
    # exportiert wurde.
    if filtertext:
        state.set(
            "sensor.device_csv_vorschau",
            value="kein_geraet",
            new_attributes={
                "friendly_name": "CSV Vorschau",
                "anzahl_entitaeten": 0,
                "tabelle": "",
            },
        )


# --- Teil 2: CSV-Export + Dashboard-Vorschau bei Auswahl ---------------------

@state_trigger(
    "input_select.device_csv_auswahl",
    "input_boolean.device_csv_werte_exportieren",
)
def csv_export_bei_auswahl():
    geraet_name = state.get("input_select.device_csv_auswahl")
    if not geraet_name or geraet_name in ("unknown", "Bitte wählen"):
        return

    geraet = _geraet_anhand_name_finden(geraet_name)
    if not geraet:
        log.warning(f"Kein Gerät gefunden für Auswahl '{geraet_name}'")
        return

    werte_mit = state.get("input_boolean.device_csv_werte_exportieren") == "on"

    # CSV-Inhalt aufbauen
    if werte_mit:
        csv_zeilen = ["entity_id;name;state"]
    else:
        csv_zeilen = ["entity_id;name"]

    # Markdown-Tabelle für die Dashboard-Vorschau (ohne entity_id, da lange
    # nicht umbrechende IDs die Name-Spalte sonst zusammenquetschen)
    if werte_mit:
        md_zeilen = ["| name | state |", "|---|---|"]
    else:
        md_zeilen = ["| name |", "|---|"]

    entity_ids = _entities_fuer_geraet(geraet.id)

    for eid in entity_ids:
        zustand_objekt = hass.states.get(eid)
        name = zustand_objekt.attributes.get("friendly_name", "") if zustand_objekt else ""
        if werte_mit:
            zustand = zustand_objekt.state if zustand_objekt else "unknown"
            csv_zeilen.append(f"{eid};{name};{zustand}")
            md_zeilen.append(f"| {name} | {zustand} |")
        else:
            csv_zeilen.append(f"{eid};{name}")
            md_zeilen.append(f"| {name} |")

    csv_inhalt = "\n".join(csv_zeilen)
    md_tabelle = "\n".join(md_zeilen)

    pfad = "/config/www/device_entities.csv"

    try:
        task.executor(_csv_schreiben, pfad, csv_inhalt)
        log.info(
            f"CSV-Export für '{geraet_name}' geschrieben "
            f"({len(entity_ids)} Entitäten, Werte {'mit' if werte_mit else 'ohne'})"
        )
    except Exception as e:
        log.error(f"CSV-Export fehlgeschlagen: {e}")

    # Vorschau-Sensor aktualisieren, unabhängig vom Datei-Export
    state.set(
        "sensor.device_csv_vorschau",
        value=geraet_name,
        new_attributes={
            "friendly_name": "CSV Vorschau",
            "anzahl_entitaeten": len(entity_ids),
            "tabelle": md_tabelle,
        },
    )

    # Filter und Dropdown zurücksetzen, damit das Tool sofort wieder für die
    # nächste Auswahl bereit ist. Löst harmlos erneut diesen Trigger sowie
    # den Filter-Trigger aus (input_select landet dabei wieder bei "Bitte
    # wählen" -> obiger Abbruch greift, kein zweiter Export).
    input_select.select_option(
        entity_id="input_select.device_csv_auswahl",
        option="Bitte wählen",
    )
    input_text.set_value(
        entity_id="input_text.device_csv_filter",
        value="",
    )


# --- Teil 3: Manueller Reset über den Button ---------------------------------

@state_trigger("input_button.device_csv_neu")
def neue_auswahl_button_gedrueckt():
    # Setzt Filter, Dropdown und den CSV-Bereich sofort per Klick zurück,
    # ohne auf Tab/Enter im Filterfeld warten zu müssen.
    input_text.set_value(
        entity_id="input_text.device_csv_filter",
        value="",
    )
    input_select.select_option(
        entity_id="input_select.device_csv_auswahl",
        option="Bitte wählen",
    )
    state.set(
        "sensor.device_csv_vorschau",
        value="kein_geraet",
        new_attributes={
            "friendly_name": "CSV Vorschau",
            "anzahl_entitaeten": 0,
            "tabelle": "",
        },
    )
    )
