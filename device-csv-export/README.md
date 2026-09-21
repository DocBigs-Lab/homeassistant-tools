# Geräte-CSV-Export für Home Assistant

Kleines Dashboard-Tool für Home Assistant: Gerät aus einer gefilterten
Dropdown-Liste auswählen, alle zugehörigen Entitäten als CSV herunterladen –
wahlweise mit oder ohne aktuelle Zustände. Zusätzlich gibt es eine
Live-Vorschau als Tabelle direkt im Dashboard, und nach jedem Export setzt
sich das Tool automatisch zurück.

![Geräte-Export Dashboard-Karte](screenshot.png)

## Funktionen

- Dropdown mit **allen** in Home Assistant registrierten Geräten – wird
  automatisch befüllt, keine manuelle Pflege nötig
- **Filter**-Textfeld, das die Dropdown-Liste live filtert (Teilstring-Suche,
  ohne Groß-/Kleinschreibung) und die Treffer zusätzlich als einfache,
  live aktualisierte Liste im Dashboard anzeigt – sichtbar ohne das
  Dropdown zu öffnen (nicht klickbar, siehe „Design-Entscheidung“ unten)
- CSV-Export der Entitäten des gewählten Geräts nach `/config/www/device_entities.csv`
- Schalter, ob die aktuellen Zustände mit exportiert werden sollen
- Live-Vorschau als Markdown-Tabelle im Dashboard
- Filter und Dropdown setzen sich nach jedem Export automatisch zurück –
  sofort bereit für die nächste Auswahl
- Zusätzlicher **"Neue Auswahl"**-Button, der Filter, Dropdown und CSV-
  Bereich sofort per Klick zurücksetzt, ohne auf Tab/Enter zu warten
- Läuft komplett über [pyscript](https://github.com/custom-components/pyscript) –
  keine zusätzliche Automation, kein `notify:`- oder `shell_command:`-Setup,
  keine weiteren HACS-Karten nötig

## Voraussetzungen

- Home Assistant (getestet ab 2024.12, da ältere `notify: file`-Konfigurationen
  seither entfernt sind und dieses Tool ohnehin nicht darauf aufbaut)
- [HACS](https://hacs.xyz/)
- Die HACS-Integration **pyscript**

## Installation

1. **pyscript installieren**
   HACS → Integrationen → „pyscript“ suchen und installieren, danach unter
   *Einstellungen → Geräte & Dienste → Integration hinzufügen* → „Pyscript“
   einrichten mit:
   - ✅ Alle Importe erlauben
   - ✅ Home Assistant als globale Variable verwenden
   - ⬜ Legacy-Decorators verwenden (nicht nötig)

2. **Dateien kopieren**

   | Datei | Ziel |
   |---|---|
   | `device_csv_export.yaml` | `/config/packages/device_csv_export.yaml` |
   | `device_list_updater.py` | `/config/pyscript/device_list_updater.py` |

3. **Packages aktivieren**, falls noch nicht geschehen, in der `configuration.yaml`:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

4. **Home Assistant komplett neu starten** (kein reines „YAML neu laden“ –
   pyscript-Dateien und Packages werden nur beim vollständigen Start geladen).

5. **Dashboard-Karte einfügen** (Lovelace, YAML-Modus):

   ```yaml
   type: vertical-stack
   cards:
     - type: entities
       title: Geräte-Export
       entities:
         - input_text.device_csv_filter
         - input_select.device_csv_auswahl
         - input_boolean.device_csv_werte_exportieren
         - input_button.device_csv_neu
     - type: markdown
       content: >
         {% if states('sensor.device_csv_vorschau') not in ['unknown', 'kein_geraet'] %}
         <a href="/local/device_entities.csv?t={{ as_timestamp(states.sensor.device_csv_vorschau.last_changed) | int }}" target="_blank"><ha-icon icon="mdi:file-download"></ha-icon> CSV herunterladen</a>

         {{ state_attr('sensor.device_csv_vorschau', 'tabelle') }}
         {% endif %}
     - type: markdown
       content: >
         {{ state_attr('sensor.device_csv_filter_treffer', 'liste') }}
   ```

   Die Filter-Treffer-Liste steht bewusst **unter** Download/Vorschau: Sie
   ist leer, solange kein Filtertext eingegeben ist, und würde nach dem
   automatischen Reset sonst als lange, ungefilterte Liste Download und
   Vorschau weit nach unten verdrängen. Die Download-/Vorschau-Karte
   blendet sich zudem selbst aus, sobald wieder in das Filterfeld getippt
   wird (die zuletzt exportierte CSV ist dann nicht mehr die aktuelle
   Auswahl) – sie erscheint erst wieder nach dem nächsten Export.
   `target="_blank"` öffnet die CSV in einem neuen Tab, damit der
   Dashboard-Tab nicht navigiert wird. Der Zeitstempel-Parameter `?t=...`
   ist wichtig: Ohne ihn cached der Browser die Datei unter der immer
   gleichen URL und liefert bei wiederholten Downloads eine veraltete
   Version aus.

## Verwendung

1. Im Filterfeld tippen und mit Tab oder Enter bestätigen – die Liste ganz
   unten zeigt dann die Treffer (Home Assistant sendet den Feldinhalt erst
   beim Verlassen des Felds, nicht bei jedem Tastendruck).
2. Im Dropdown das gewünschte Gerät auswählen.
3. Optional: Schalter „Aktuelle Werte mit exportieren“ umlegen.
4. Die Vorschau-Tabelle darunter aktualisiert sich sofort.
5. Über den Link „CSV herunterladen“ die Datei im Browser öffnen/speichern.
6. Filter und Dropdown setzen sich danach automatisch zurück – die
   Vorschau-Tabelle und der Download-Link bleiben unverändert bestehen, bis
   der nächste Export läuft. Sobald wieder in das Filterfeld getippt wird
   (nach Verlassen/Enter), blendet sich der CSV-Bereich aus.
7. Alternativ: Jederzeit auf **"Neue Auswahl"** klicken, um Filter,
   Dropdown und CSV-Bereich sofort zurückzusetzen, ohne erst tippen zu
   müssen.

## CSV-Format

Semikolon-getrennt, UTF-8:

```
entity_id;name;state
sensor.beispiel_temperatur;Beispiel Temperatur;21.4
```

Ohne aktivierten Schalter entfällt die Spalte `state`.

## Wie es technisch funktioniert

- `device_list_updater.py` liest beim Start von Home Assistant die
  Device-Registry aus und befüllt darüber den `input_select`-Helper.
- Bei jeder Bestätigung im Filterfeld (Tab/Enter – `input_text` sendet
  seinen Wert erst beim Verlassen des Felds an Home Assistant, nicht bei
  jedem Tastendruck) wird die Optionsliste des `input_select` neu gesetzt
  (Teilstring-Suche über alle Gerätenamen) und parallel ein
  `sensor.device_csv_filter_treffer` mit den Treffern als Markdown-Liste
  (Attribut `liste`) aktualisiert – eine gewöhnliche Markdown-Karte bindet
  direkt per `state_attr()` daran und aktualisiert sich live. Bei leerem
  Filter bleibt die Liste bewusst leer, statt alle Geräte aufzulisten.
  Ist der Filtertext dabei nicht leer (also aktiv getippt, nicht unser
  eigener Reset), wird zusätzlich `sensor.device_csv_vorschau` auf den
  Wert `kein_geraet` mit leerer Tabelle zurückgesetzt – die Download-/
  Vorschau-Karte blendet sich dadurch per `{% if %}`-Bedingung im Template
  komplett aus, bis das nächste Gerät exportiert wurde.
- Bei jeder Auswahl im Dropdown (oder Umschalten des Werte-Schalters)
  ermittelt ein `@state_trigger` alle Entitäten des gewählten Geräts über
  die Entity-Registry, schreibt sie als CSV und aktualisiert parallel einen
  `sensor.device_csv_vorschau` mit einer fertigen Markdown-Tabelle als
  Attribut.
- Das Schreiben der Datei läuft über `task.executor`, damit blockierendes
  Datei-I/O den Home-Assistant-Event-Loop nicht ausbremst.
- Direkt danach werden Filter und Dropdown programmatisch zurückgesetzt
  (`input_select.select_option` auf „Bitte wählen“, `input_text.set_value`
  auf leer), damit das Tool sofort wieder für die nächste Auswahl bereit
  ist. Das löst harmlos erneut denselben Trigger aus – die Abbruchbedingung
  am Anfang der Funktion verhindert einen zweiten Export.
- `input_button.device_csv_neu` löst denselben Reset zusätzlich sofort per
  Klick aus (Filter leeren, Dropdown auf „Bitte wählen“, Vorschau-Sensor
  auf `kein_geraet` mit leerer Tabelle) – unabhängig vom Tab/Enter-
  Verhalten des Filterfelds.

## Design-Entscheidung: Filter-Treffer sind sichtbar, aber nicht klickbar

Ein früherer Ansatz zeigte Filter-Treffer als klickbare `button`-Kacheln
über die HACS-Karte `auto-entities` an, um das Dropdown ganz zu ersetzen.
Das scheiterte an unzuverlässiger Live-Aktualisierung: Home Assistants
Abhängigkeitserkennung für Templates erkennt Funktionsaufrufe wie
`state_attr(...)` innerhalb eines verschachtelten Dict-Literals nicht
zuverlässig, wodurch die Kacheln nach der ersten Anzeige nicht mehr
aktualisiert wurden – auch mehrere Workarounds lösten das nicht robust.

Die aktuelle Lösung zeigt die Treffer stattdessen über eine gewöhnliche
Markdown-Karte an, die ganz normal per `state_attr()` an den Sensor bindet
– genau derselbe, bewährt zuverlässige Bindungsmechanismus, den auch die
Vorschau-Tabelle nutzt. Zum Auswählen selbst dient weiterhin das native
`input_select`-Dropdown. Das kostet einen zusätzlichen Klick zum Öffnen,
ist dafür aber ohne zusätzliche HACS-Abhängigkeit voll zuverlässig.

## Bekannte Stolpersteine

- **`notify: - platform: file` funktioniert nicht mehr** – diese YAML-Methode
  wurde in Home Assistant 2024.12.0 entfernt. Dieses Tool nutzt daher direktes
  Datei-I/O über pyscript statt `notify`.
- **`device_id()` / `device_entities()` sind reine Jinja-Template-Funktionen**
  und in pyscript-Python-Code nicht verfügbar. Das Skript greift stattdessen
  direkt auf `device_registry` und `entity_registry` zu.
- Funktionen, die über `task.executor` laufen, brauchen den Decorator
  `@pyscript_compile`, da `task.executor` keine pyscript-eigenen
  AST-interpretierten Funktionen akzeptiert.
- Ein direkter Markdown-/HTML-Link ohne `target="_blank"` kann in manchen
  Browsern/Kiosk-Umgebungen den Tab beim Herunterladen schließen.
- **Browser-Caching der CSV-Datei**: Da die URL `/local/device_entities.csv`
  bei jedem Export gleich bleibt, kann der Browser eine ältere, gecachte
  Version ausliefern, statt die gerade neu geschriebene Datei zu laden – man
  bekommt dann Entitäten eines vorher gewählten Geräts statt des aktuellen.
  Fix: Zeitstempel als Query-Parameter an die URL anhängen (siehe
  Installationsschritt 5), damit jede Auswahl eine neue URL erzeugt.
- **pyscript unterstützt keine reinen Generator-Ausdrücke** (`(x for x in y)`
  ohne eckige Klammern) – führt zu `NotImplementedError: ... ast_generatorexp`.
  Betroffene Stellen müssen als Listen-Comprehension (`[x for x in y]`)
  geschrieben werden.

## Lizenz

MIT
