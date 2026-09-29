# API: Messwerte übertragen

Diese Dokumentation beschreibt den öffentlichen Endpunkt für www.ortsnetz-auslastung.de darüber kommunizieren Clients wie Home Assistant, Shelly Scripts und eigene Anwendungen. 

## Endpunkt

```text
POST https://www.ortsnetz-auslastung.de/v1/measurements
Content-Type: application/json
```

Für die Messwertübertragung ist keine Anmeldung. Ein Messpunkt wird anhand seiner Koordinaten zugeordnet. Sende je Messpunkt höchstens einmal alle fünf Minuten.

## Request

| Feld | Typ | Pflicht | Regeln |
| --- | --- | --- | --- |
| `observed_at` | String | Ja | ISO 8601 mit Zeitzone, z. B. `2026-09-14T10:15:00Z`; höchstens 15 Minuten in der Zukunft |
| `latitude` | Zahl | Ja | −90 bis 90 |
| `longitude` | Zahl | Ja | −180 bis 180 |
| `l1_v` | Zahl | Ja | größer 0, höchstens 500; empfohlen: 150–300 V |
| `l2_v` | Zahl | Ja | größer 0, höchstens 500; empfohlen: 150–300 V |
| `l3_v` | Zahl | Ja | größer 0, höchstens 500; empfohlen: 150–300 V |
| `grid_frequency_hz` | Zahl | Nein | 45–55 Hz |
| `plant_capacity_kwp` | Zahl | Nein | größer 0, höchstens 1000 |
| `pv_forecast_kwh` | Zahl | Nein | 0–100000 |
| `smartmeter_model` | String | Nein | maximal 120 Zeichen |
| `integration_version` | String | Nein | maximal 32 Zeichen |

Beispiel:

```json
{
  "observed_at": "2026-09-14T10:15:00Z",
  "latitude": 52.520008,
  "longitude": 13.404954,
  "l1_v": 229.8,
  "l2_v": 230.1,
  "l3_v": 230.0,
  "grid_frequency_hz": 50.01,
  "smartmeter_model": "Shelly Pro 3EM",
  "integration_version": "shelly-0.1.0"
}
```

## Response

Bei Erfolg antwortet der Server mit `202 Accepted`:

```json
{
  "accepted": true,
  "created": true,
  "status": {
    "l1": "green",
    "l2": "green",
    "l3": "green",
    "overall": "green"
  },
  "storage_recommendation": "none"
}
```

`created` ist `false`, wenn derselbe Messwert bereits verarbeitet wurde. Die Statuswerte sind `green`, `yellow` oder `red`; `overall` ist die schlechteste Bewertung einer Phase.

`storage_recommendation` ist `charge` bei Überspannung, `discharge` bei Unterspannung und `none` bei normaler Spannung. Liegen Über- und Unterspannung gleichzeitig vor, hat `discharge` Vorrang.

| HTTP-Status | Bedeutung |
| --- | --- |
| `202` | Messung angenommen |
| `403` | Der Messpunkt für diese Koordinaten wurde gesperrt |
| `422` | Request ist unvollständig oder ein Feld verletzt die Validierungsregeln |
| `5xx` | Temporärer Serverfehler; beim nächsten regulären Intervall erneut senden |

## Datenschutz

Die Koordinaten identifizieren den Messpunkt. Die öffentliche Karte zeigt sie gerastert mit etwa 100 Metern Genauigkeit. Sende bei Bedarf leicht versetzte Koordinaten.
