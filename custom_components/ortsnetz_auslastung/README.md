# Ortsnetz-Auslastung für Home-Assistant-Admins

Diese Anleitung richtet sich ausschließlich an Personen, die eine Home-Assistant-Instanz betreuen. Die HACS-Integration sendet die drei Phasenspannungen L1, L2 und L3 sowie den Standort deiner Instanz an die Ortsnetz-Auslastung-API. Nach dem ersten Senden werden die Werte alle fünf Minuten übertragen.

## Zuständigkeiten

| Rolle | Zuständig für |
| --- | --- |
| Home-Assistant-Admin | HACS-Installation, Neustart, Auswahl der Sensoren, Standortangaben und Eingabe der Zugangsdaten in Home Assistant |
| Server-Admin | Betrieb der Webanwendung und API, Sperren/Freigeben automatisch erkannter Standorte, Bereitstellen der öffentlichen API-Adresse und Untersuchung serverseitiger Fehler |

Der Home-Assistant-Admin benötigt keinen SSH- oder Docker-Zugang zum Server.

## Voraussetzungen

- Home Assistant mit installiertem [HACS](https://hacs.xyz/)
- Drei numerische `sensor`-Entitäten für L1, L2 und L3; die Zustände müssen Voltwerte enthalten, z. B. `229.8`
- Eine numerische Forecast-Sensor-Entität mit dem erwarteten PV-Tagesertrag in kWh
- Eine numerische Sensor-Entität für die Netzfrequenz in Hz, z. B. `50.01`
- Vom Server-Admin bereitgestellte öffentliche API-Adresse per HTTPS

Die Integration ist nicht für Werte wie `unknown`, `unavailable` oder Text geeignet. In diesem Fall wird die betreffende Übertragung übersprungen und in den Home-Assistant-Protokollen vermerkt.

> **Wichtig:** Wähle für L1, L2 und L3 immer die Spannungs-Sensoren des Smartmeters deiner PV-Anlage aus. Wähle auch die Netzfrequenz bevorzugt vom selben Smartmeter. Andere Spannungs- oder Frequenzwerte, etwa von Steckdosen, Wechselrichtern oder einzelnen Geräten, bilden die Netzqualität am Anschluss nicht zuverlässig ab und dürfen nicht verwendet werden.

## 1. Integration über HACS herunterladen

1. Öffne in Home Assistant **HACS**.
2. Wähle **Integrationen**.
3. Öffne oben rechts das Menü mit den drei Punkten und wähle **Benutzerdefinierte Repositories**.
4. Trage als Repository-URL ein:

   ```text
   https://github.com/thomaslehmann1234/Auslastung-Ortsnetz
   ```

5. Wähle als Kategorie **Integration** und bestätige mit **Hinzufügen**.
6. Suche nach **Ortsnetz-Auslastung** und wähle **Herunterladen**.

## 2. Home Assistant neu starten

Nach dem Download ist ein Neustart erforderlich:

1. Öffne **Einstellungen → System**.
2. Wähle oben rechts das Ein/Aus-Menü.
3. Wähle **Home Assistant neu starten** und bestätige.

Warte, bis Home Assistant wieder vollständig erreichbar ist.

## 3. Integration einrichten

1. Öffne **Einstellungen → Geräte & Dienste**.
2. Klicke auf **Integration hinzufügen**.
3. Suche nach **Ortsnetz-Auslastung**.
4. Fülle die Felder aus:

   | Feld | Wert |
   | --- | --- |
   | API-Adresse | `https://www.ortsnetz-auslastung.de` |
   | Sensor L1 | Sensor-Entität für Phase L1 |
   | Sensor L2 | Sensor-Entität für Phase L2 |
   | Sensor L3 | Sensor-Entität für Phase L3 |
   | Anlagengröße (kWp) | Installierte Nennleistung der PV-Anlage in Kilowatt-Peak, z. B. `9.8` |
   | PV-Forecast heute (kWh) | Optionaler Forecast-Sensor für den erwarteten PV-Ertrag des aktuellen Tages in Kilowattstunden |
   | Netzfrequenz (Hz) | Frequenz-Sensor des Smartmeters, dessen Wert in Hertz geliefert wird |
   | Breitengrad / Längengrad | Standardmäßig der Home-Assistant-Standort; bei Bedarf überschreiben |

5. Bestätige die Einrichtung.

Die Integration sendet sofort einen ersten Datensatz und danach alle fünf Minuten. Die Kartenansicht aktualisiert sich im Live-Modus alle 15 Minuten; ein manuelles Neuladen zeigt den neuen Standort sofort.

Der PV-Forecast wird pro Standort und Kalendertag gespeichert. Die Karte berechnet daraus den **Forecast-Ertrag**: `Forecast (kWh) ÷ Anlagengröße (kWp) = kWh/kWp/Tag`.

## Prüfung und Fehlerbehebung

Nach der Einrichtung sollten die Daten nach spätestens fünf Minuten auf der Karte erscheinen. Home-Assistant-Protokolle findest du unter **Einstellungen → System → Protokolle**.

| Meldung | Ursache und Lösung |
| --- | --- |
| `403 Forbidden` | Dieser Standort wurde durch den Server-Admin gesperrt. Standortangaben prüfen oder den Server-Admin kontaktieren. |
| `Spannungssensor … ist nicht verfügbar` | Eine ausgewählte Sensor-Entität hat keinen numerischen Wert. Entität und Einheit prüfen. |
| `Netzfrequenz-Sensor … ist nicht verfügbar` | Der Frequenz-Sensor liefert keinen numerischen Hz-Wert. Entität und Einheit prüfen. |
| Kein Standort auf der Karte | Mindestens fünf Minuten warten, Karte neu laden und die HA-Protokolle prüfen. Besteht das Problem weiter, Zeitpunkt und Fehlermeldung an den Server-Admin geben. |

API-Adresse, Sensoren, Koordinaten und PV-Angaben können nach der Einrichtung unter **Einstellungen → Geräte & Dienste → Ortsnetz-Auslastung → Konfigurieren** angezeigt und geändert werden. Der Standort wird beim ersten Messwert automatisch aus den Koordinaten erkannt.

## Datenschutz

Die Integration übermittelt Koordinaten, Zeitstempel, die drei Spannungswerte, Netzfrequenz sowie Angaben zu PV-Anlage und Forecast. Die öffentliche Karte zeigt Koordinaten nur gerastert mit etwa 100 Metern Genauigkeit. Verwende bei Bedarf die überschreibbaren Koordinaten, um einen alternativen Standort zu senden.
