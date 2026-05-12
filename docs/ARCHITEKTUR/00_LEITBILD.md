# 00 — Leitbild

## Was wir bauen

Eine **kognitive Werkbank für eine Domäne**. Nicht ein Werkzeug, das eine Aufgabe löst, sondern eine Sammlung halbselbstständiger Werkzeuge, die zusammen die Arbeit substanziell besser machen — Daten aus mehreren Quellen erfassen, prüfen, strukturieren, verschiedene Effektoren parallel arbeiten lassen, und das Ergebnis in einem zentralen Wahrheits-Speicher konsolidieren.

Drei parallele Demo-Domänen ([`docs/DEMOS.de.md`](../DEMOS.de.md)) zeigen das Pattern in konkreten Szenarien:

- **Architekturbüro** (`examples/architect_lite/`) — Floor-Plan-Extraktion, Entity-Verwaltung
- **Steuerberatung** (`examples/tax_lite/`) — Steuererklärungs-Validierung pro Mandant
- **CFO-Office** (`examples/cfo_lite/`) — Quartals-Closes mit Budget-Variance-Checks

Was nicht in allen drei Domänen funktioniert, gehört nicht ins Skelett.

## Drei Grundprinzipien

### 1. Menschenlesbare Dateien sind die Wahrheit

Jeder Effektor schreibt seine Ergebnisse in `.md`/`.yaml` in das Entity-Verzeichnis (`memory/entities/<entity_id>/`). Datenbanken sind nur Suchindizes, nie Wahrheitsquelle. Wer eine Entity verstehen will, liest die Dateien — nicht eine SQL-Tabelle.

Das ist anstrengend (Tools müssen YAML schreiben können statt SQL), aber es ist der einzige Weg, der Folgendes garantiert:

- Die Domäne bleibt unabhängig vom KI-System — wenn das System weg ist, bleiben die Daten lesbar.
- Manuelle Korrektur ist immer möglich (Texteditor reicht).
- Versionierung über git ist trivial.

### 2. Mensch ist Kurator, KI ist Vorschlag

Kein Effektor darf eigenmächtig in Entity-Daten schreiben, ohne dass der Mensch entweder explizit zugestimmt oder eine Aktion bestätigt hat (Plan-Gate, save-edits, confirm-Buttons). Die KI darf:

- Vorschlagen
- Hervorheben
- Aggregieren
- Übersetzen

Aber die Wahrheit setzt der Mensch.

Realisiert über das Plan-Gate-Pattern (siehe [`02_NERVENSYSTEM.md`](02_NERVENSYSTEM.md) und [`docs/LIFECYCLE.de.md`](../LIFECYCLE.de.md)).

### 3. Effektoren sind semi-autonom, nicht autark

Ein Effektor darf eine Aufgabe selbständig erledigen, **muss aber zuerst den Kontext lesen**. Die häufigste Bug-Klasse in solchen Systemen ist: Effektor löst seine Aufgabe gut, ignoriert aber den vorhandenen Entity-Kontext, der die halbe Arbeit erspart hätte.

Beispiel-Anti-Muster (generisch):

> Ein Vision-basierter Plan-Extraktor analysiert ein PDF, baut ein Wand-Netzwerk, versucht Räume zu erkennen — ohne den Entity-Steckbrief zu lesen, der „Klinik mit 30 Patientenzimmern, Maßstab 1:50, 2.OG" sagt. Die Sanity-Erwartung wäre vor der Bildanalyse da. Der Aufwand wäre ein Lookup zum EntityStore.

Das Pattern dazu heißt **Pre-Lookup (M1)**, ist in [`05_REFLEXBOGEN.md`](05_REFLEXBOGEN.md) als Pattern P1 verbindlich gemacht. Realisiert über `Effector.pre_load(context)` (siehe [`08_GOLD_PATTERNS.md`](08_GOLD_PATTERNS.md)).

## Zielbild

Ein User stellt eine Frage:

> „Was ist beim 343er Vorgang noch offen?"

Die Antwort kommt in unter 3 Sekunden, ist quellenbelegt (Quelle A vom 02.05., Quelle B KW 18, `_todos.yaml`), und enthält neben der Aussage einen Vorschlag was als nächstes zu tun ist.

Auf dem Weg dahin:

- haben mehrere Effektoren beigetragen (über das Insight-Pattern, siehe [`02_NERVENSYSTEM.md`](02_NERVENSYSTEM.md))
- wurden Konflikte erkannt (Plan-Gate, ConflictDetector)
- wurden Lücken im Wissen identifiziert und dem User gemeldet (statt halluziniert)
- wurde die Konversation getrackt damit das System das nächste Mal schneller zur richtigen Antwort kommt (Trace + Lesson, siehe [`docs/OBSERVABILITY.de.md`](../OBSERVABILITY.de.md))

## Was wir nicht bauen

- Keine eigene Cloud-Plattform (Daten bleiben on-prem oder im konsumierenden System).
- Keine User-Verwaltung in Datenbanken (Mensch = OS-User).
- Keine Auto-Aktionen ohne Human-Approve (außer reine Lesevorgänge).
- Keine „intelligente Agenten" die selbst ungated Einsätze fahren.

## Erfolgs-Definition

Das System ist erfolgreich wenn:

1. Ein Effektor, der vor 6 Monaten gut war, ist heute besser — **ohne dass jemand am Effektor selbst geändert hat**. Verbesserung kommt aus Lessons aus anderen Effektoren, aus Plan-Gate-Approves, aus Master-Patterns.
2. Ein neuer Effektor kann in einem Tag angeschlossen werden, weil das Nervensystem (Engine, Validator, Plan-Gate, Lesson-Aggregator, EventBus) das Skelett bereitstellt.
3. Eine Anfrage an das System kommt nie mit „weiß nicht" zurück, sondern entweder mit Antwort oder mit „diese Quelle fehlt — soll ich sie anlegen?" (NEEDS_CLARIFICATION-Pfad, siehe [`docs/STAR.de.md`](../STAR.de.md)).
