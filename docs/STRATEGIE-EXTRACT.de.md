*[🇬🇧 English version](STRATEGIE-EXTRACT.md)*

# Strategie und Trenn-Vertrag

> Governance-Prinzipien des organism-core-Skeletts. Welche Logik gehört hier hinein, welche nicht?

## Mission

organism-core ist eine **Reference-Implementation** für DoD-getriebene Multi-Tool-Architekturen. Es liefert ein opinionated Pattern-Set, das in einer Codebasis zusammen funktioniert — nicht ein generischer Toolkit, der alle Patterns unterstützt.

Konsumenten erweitern das Skelett für ihre konkrete Domäne (siehe [`DEMOS.de.md`](DEMOS.de.md) für Vorlagen). Das Skelett selbst bleibt **domänen-neutral**.

## Trenn-Test (verbindlich)

Vor jedem Commit ins Skelett-Repo:

> **„Würde dieselbe Logik in einer Steuerberatung Sinn ergeben?"**

- Ja, mit umbenannten Variablen → gehört ins Skelett
- Ja, aber nur mit Plugin-Punkten → gehört ins Skelett mit klaren Erweiterungs-Stellen
- Nein, wäre dort nutzlos → gehört NICHT ins Skelett

Bei Unsicherheit: **nicht committen**. Frage offen lassen, Trenn-Test durch Schreiben einer Mini-Demo (siehe `examples/tax_lite/` oder `examples/cfo_lite/` als Vorlage) beantworten.

Verifiziert wird der Trenn-Test automatisiert über `tests/examples/test_cross_demo.py`: alle drei Demo-Domänen (Architekturbüro, Steuerberatung, CFO-Office) müssen identische Pipeline-Counts produzieren. Wenn einer abweicht, ist die Pipeline domänen-spezifisch geworden.

## Was ins Skelett gehört

- DoD-Engine + Validator + 6 Source-Patterns ([`STAR.de.md`](STAR.de.md))
- Plan-Gate + Lifecycle-State-Machine + Orchestrator ([`LIFECYCLE.de.md`](LIFECYCLE.de.md))
- Provenance + Trace + Lessons + EventBus + OTel-Converter ([`OBSERVABILITY.de.md`](OBSERVABILITY.de.md))
- Settings-Layer (admin-UI-fähig)
- Effector-Protocol (5-Kontakt-Vertrag)
- Demo-Domains als Genericity-Disziplin

## Was NICHT ins Skelett gehört

### Echte Domänen-Daten

Niemals echte oder anonymisierte Steckbriefe / Mandanten-Daten / Floor-Plans / Buchungen / etc. **Strukturmuster sickern durch Anonymisierung durch** — wer die Daten kennt, erkennt sie auch in der „anonymisierten" Form.

Demo-Daten in `examples/` sind **frei erfunden**. Keine Anonymisierung-Pipeline aus realer Quelle.

### Domänen-spezifisches Vokabular im `src/`

Im Skelett-Code (`src/organism/`) keine domänen-spezifischen Begriffe. Generische Begriffe sind:

- ✓ `Entity`, `EntityStore`, `Effector`, `Action`, `Stage`, `Lesson`, `Trace`
- ✗ `Projekt`, `Bauherr`, `Gewerk` (Architekturbüro-spezifisch)
- ✗ `Mandant`, `Buchung`, `Steuerklasse` (Steuer-spezifisch)
- ✗ `Cost-Center`, `Budget-Variance` (CFO-spezifisch)

In `examples/<domain>/` sind domain-spezifische Begriffe natürlich erlaubt — das ist der Sinn der Demos.

### Domänen-spezifische Hardcoded-Logik

Keine `if entity.type == "wohnbau"`-Verzweigungen im Skelett. Domain-Logik gehört in die Effektoren der Konsumenten oder in das `frontmatter.dod.criteria`-Format der Entity-Steckbriefe.

### Tools-of-the-day

Keine konkreten LLM-Provider-SDK-Einbindungen, keine konkreten Vector-DB-Clients, keine konkreten OTel-Exporter im Skelett. Stattdessen: Stub-Sources (Phase 2.3) mit stabiler API, die Konsumenten gegen ihre konkrete Tooling-Wahl verdrahten.

## Was Konsumenten ergänzen

| Schicht | Skelett liefert | Konsument liefert |
|---|---|---|
| Effektor-Implementation | Protocol + BaseEffector + 5-Kontakt-Vertrag | konkrete `act()`-Logik mit LLM-/Vision-/API-Calls |
| Vector-Store | `VectorSearchSource`-Stub | echten Vector-Client (ChromaDB, Pinecone, Weaviate) |
| Externe-Quelle-Anbindung | EntityStore-Pattern | Mount-Reader für DMS / Filesystem / API |
| Plan-Gate-UI | API + State-Machine | Web-Cockpit mit Notifications |
| OTel-Export | struktur-only Converter | Exporter zu Langfuse / Jaeger / Phoenix |
| Self-Improvement-Worker | Konzept-Doku in [`ARCHITEKTUR/06_SELF_IMPROVEMENT.md`](ARCHITEKTUR/06_SELF_IMPROVEMENT.md) | Sandbox-Implementation (E2B / Firecracker / Container) |

## Format-Konventionen

### Truth ist file-based

Strukturierte Daten im Wahrheits-Speicher sind **YAML oder Markdown**. Kein JSON (Kommentare nicht erlaubt), kein Pickle, kein proprietäres Binärformat.

Vector-Stores sind erlaubt als Index-Schicht — aber niemals als Wahrheitsquelle. „Wenn du dir vorstellst die Vektor-DB zu löschen — das System überlebt das, der Index würde aus EntityStore neu aufgebaut."

### Provenance auf jedem KI-Output

Jeder KI-erzeugte Eintrag in den Wahrheits-Speicher hat einen `_provenance`-Block:

```yaml
groesse_qm: 1850
_provenance:
  author: my_effector
  source: "Vision-Call zu PDF X vom 2026-04-12"
  confidence: 0.85
  validated_by_user: false
  timestamp: "2026-04-12T14:32:00+00:00"
```

Ohne Provenance ist ein Eintrag nicht zurückführbar. Bei Konflikten zwischen zwei Aussagen entscheidet `validated_by_user` (true gewinnt über false), dann `confidence`. Detail: [`OBSERVABILITY.de.md`](OBSERVABILITY.de.md).

### Plan-Gate ist nicht optional

Schreibvorgänge mit Außenwirkung gehen **immer** durch das Plan-Gate (ab Lifecycle-Stage `(b) PROPOSED`). Wer sich daran vorbeischreibt, hat einen Bug. Test: kann der User die Aktion rückgängig machen ohne `git revert`? Wenn nein → muss durchs Plan-Gate.

Detail: [`LIFECYCLE.de.md`](LIFECYCLE.de.md).

## Erfolgs-Definition

Das Skelett ist erfolgreich wenn:

1. Ein Effektor, der vor 6 Monaten gut war, ist heute besser — **ohne dass jemand am Effektor selbst geändert hat**. Verbesserung kommt aus Lessons aus anderen Effektoren, aus Plan-Gate-Approves, aus Master-Patterns.
2. Ein neuer Effektor kann in einem Tag angeschlossen werden, weil das Nervensystem (Engine, Validator, Plan-Gate, Lessons-Aggregator, EventBus) das Skelett bereitstellt.
3. Eine Anfrage an das System kommt nie mit „weiß nicht" zurück, sondern entweder mit Antwort oder mit „diese Quelle fehlt — soll ich sie anlegen?" (NEEDS_CLARIFICATION-Pfad, siehe [`STAR.de.md`](STAR.de.md)).

## Lizenz und Eigentum

- **Skelett-Repo** (`organism-core`): GNU AGPL-3.0, dual-lizenziert (kommerzielle Ausnahme via `info@brachia.dev`). Apache 2.0 bis v0.2.0; ab v0.3.0 AGPL-3.0.
- **Konsumenten-Repos**: jeweils eigene Lizenz-Wahl. Konsumieren `organism-core` als Dependency oder via Code-Adopt.

Niemand außerhalb der Konsumenten-Organisation bekommt Zugriff auf konsumenten-spezifische Daten — das ist Voraussetzung für die file-first-Memory-Philosophie.
