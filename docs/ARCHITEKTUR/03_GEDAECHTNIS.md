# 03 — Gedächtnis

> Wo lebt die Wahrheit? Wer darf was lesen, wer darf was schreiben?

## Vier Ebenen Gedächtnis

```
   ┌──────────────────────────────────────────────────────────────┐
   │ Externe Quelle (z.B. Mounted Filesystem, DMS, externes API)  │
   │ Read-only — KEIN SCHREIBEN durch das KI-System                │
   └──────────────────────────────────────────────────────────────┘
                          │  scan (Verzeichnisstruktur, Metadaten)
                          ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ EntityStore   (memory/entities/<entity_id>/)                  │
   │ Steckbriefe, Sub-Indizes, Korrespondenz, Protokolle           │
   │ Markdown + YAML, manuell editierbar, git-tracked              │
   └──────────────────────────────────────────────────────────────┘
                          │  index
                          ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ Vector-Store  (z.B. ChromaDB, Pinecone, OpenSearch)           │
   │ Vektorisierter Suchindex                                      │
   │ KEIN Wahrheitsspeicher, NUR Suche                             │
   └──────────────────────────────────────────────────────────────┘
                          │  serve
                          ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ Effektor-RAM  (Sessions, Caches, in-flight)                   │
   │ Verwirft sich beim Neustart                                   │
   └──────────────────────────────────────────────────────────────┘
```

## Externe Quelle — die Welt-Wirklichkeit

Beispiele: ein gemountetes Domain-Verzeichnis (`\\fileserver\projects\`), ein externes DMS, eine API.

**Strikte Regel: NUR scannen, NIE schreiben.** Die externe Quelle gehört dem Geschäftsprozess, nicht dem KI-System. Wir lesen Verzeichnisstruktur und Dateinamen für Erkennung; Inhalte nur wenn nötig (zu viele Zwischenstände, zu viele False-Positives).

Wer dagegen verstößt, hat einen kritischen Bug. Test im Code: Effektoren dürfen nur `iterdir`, `name`, `is_dir` aufrufen — kein `read_text` ohne expliziten Bedarf, kein `write_text`.

Das Skelett implementiert keine externe-Quelle-Anbindung — das ist Konsumenten-Verantwortung (Phase 7+).

## EntityStore — das aktive Gedächtnis

`organism.memory.EntityStore` (Phase 1.2). Layout: `memory/entities/<entity_id>/`.

Pro Entity können verschiedene Dateien liegen:

| Datei | Was | Wer schreibt |
|---|---|---|
| `_entity_profile.md` | YAML-Frontmatter + Freitext, Entity-Zusammenfassung | Effektoren via PlanGate, manuell |
| `_entity_profile_meta.yaml` | KI-erkannte Metadaten | Effektor-spezifisch |
| `_dod.yaml` o.ä. | Strukturierte Felder, Welt-Koordinaten | Effektor-spezifisch |
| `_kontext_status.yaml` | Universelles Wahrheitsregister | mehrere Effektoren |
| `_medien_index.yaml` | Foto/Dokument-Metadaten (EXIF, KI-Tags) | Index-Effektor |
| `_todos.yaml` | Aufgaben aus Quellen | Effektoren |
| `_ki_fakten.yaml` | Bestätigtes Faktenwissen pro Entity | Effektoren |
| `_aenderungen.yaml` | Audit-Log strukturierter Änderungen | alle Effektoren |
| `_prozesse.yaml` | Laufende Prozesse | manuell |
| `korrespondenz/*.md` | Mail-Volltexte, Telefonnotizen | Mail-Effektor |
| `protokolle/*.md` | Besprechungsprotokolle | Protokoll-Effektor |
| `medien/*.png/.pdf` | Thumbnails + Originale | Medien-Effektor |

Welche Sub-Indizes konkret existieren ist Konsumenten-spezifisch. Das Skelett spezifiziert nur die Konvention `_entity_profile.md` mit YAML-Frontmatter (Phase 1.1) und das EntityStore-Layout (Phase 1.2).

**Format-Wahl ist absichtlich**:

- `.md` für Inhalte, die ein Mensch lesen will (Steckbrief, Korrespondenz, Protokolle)
- `.yaml` für Daten, die strukturiert ausgewertet werden
- niemals `.json` (Kommentare nicht erlaubt, Mensch liest schwerer)
- niemals SQLite/proprietär (kein Editor, keine git-Diffs)

## Vector-Store — der Suchindex

Generischer Vektor-Index (ChromaDB, Pinecone, Weaviate, OpenSearch — Konsumenten-Wahl).

Was reinkommt:

- Steckbrief-Texte (für Entity-Suche)
- Volltext-Quellen mit Kategorie-Tags
- Bestätigte Fakten aus `_ki_fakten.yaml`

Was NICHT reinkommt:

- Rohdaten ohne Kuratierung
- Wahrheits-Updates (die gehen IMMER zuerst in EntityStore, dann vielleicht hier rein)
- Embeddings als Datenbank-Wahrheit

**Regel: Vector-Store ist eine Lupe, nicht ein Tresor.** Wenn du dir vorstellst die Vektor-DB zu löschen — das System überlebt das, der Index würde aus EntityStore neu aufgebaut. Andersrum (EntityStore weg) wäre katastrophal.

Das Skelett liefert die `VectorSearchSource` (Phase 2.3) als Stub für die DoD-Engine. Konsumenten verbinden den eigentlichen Vector-Client (Phase 7+).

## Effektor-RAM

Sessions, Caches, in-flight Daten. Verwirft sich beim Neustart.

Beispiele:

- Effektor-Cache von häufig gefragten Entities (vom EntityStore gepullt)
- Plan-IDs, die gerade ausgehandelt werden
- LessonsAggregator-Query-Caches

Skelett-Komponenten halten heute keinen expliziten Cache — bei Bedarf wird das in Konsumenten-Effektoren implementiert.

## Provenance — wer hat was wann warum gesagt

`organism.provenance.Provenance` (Phase 4.0). Jede KI-erzeugte Aussage wird mit einem Provenance-Container versehen:

```yaml
groesse_qm: 1850
_provenance:
  author: floor_plan_extractor
  source: "Vision-Call zu PDF X vom 2026-04-12"
  confidence: 0.85
  validated_by_user: false
  timestamp: "2026-04-12T14:32:00+00:00"
```

Wer Provenance schreibt:

- Alle Effektoren, die in EntityStore schreiben (über M2 Upstream-Pattern, siehe [`08_GOLD_PATTERNS.md`](08_GOLD_PATTERNS.md))
- ActionOrchestrator beim Trace-Recording (Phase 4.1)
- LessonsAggregator beim Lesson-Recording (Phase 4.2)

Was Provenance ermöglicht:

- „Quelle anzeigen" in der UI (warum behauptet die KI X?)
- Konfidenz-basierte Filter („zeig nur >0.9")
- User-Validierung umkehrbar (`validated_by_user` togglen)

Detail: [`docs/OBSERVABILITY.de.md`](../OBSERVABILITY.de.md).

## Steckbrief — die Königsdaten

Pro Entity die einzige Datei, die **jeder Effektor zuerst lesen sollte** bevor er handelt. Sie enthält den Anker für jeden weiteren Datenfluss.

YAML-Frontmatter (nur was bekannt ist, der Rest fehlt einfach):

```yaml
---
id: "343"
name: "Beispiel-Vorgang"
status: aktiv         # aktiv | abgeschlossen | in_anbahnung
type: <domain-spezifisch>
owner:
  name: "Firma GmbH"
location:
  city: "Stuttgart"
tags: [tag_a, tag_b]
dod:
  criteria:
    - name: <kriterium>
      expected: <wert>
      weight: 1.0
---
# Beispiel-Vorgang
Freitext-Beschreibung, Eigenheiten, gelernte Lessons.
```

**Felder sind optional**. Wer ein Feld nicht sicher weiß, lässt es weg, statt zu raten. Neue Felder dürfen jederzeit angelegt werden — Effektoren die sie nicht kennen ignorieren sie.

**Bei Konflikten**: User-Eingabe schlägt KI-Vorschlag, geprüfter Eintrag schlägt unbestätigten.

Der `dod`-Block ist die Konvention für [`docs/STAR.de.md`](../STAR.de.md) — die `EntityFrontmatterSource` (Phase 2.2) liest ihn aus.

## Entity-Cache

Ein In-Memory-Cache von Entity-Steckbriefen ist üblich für Performance — `EntityStore.read(entity_id)` selbst hält keinen Cache (Phase 1.2 entscheidet bewusst dafür: jeder Read trifft das Filesystem). Konsumenten können einen Cache-Wrapper über EntityStore legen, falls für Latenz nötig.

## Wo Gedächtnis im Skelett heute lückenhaft ist

1. **Cross-Entity-Lessons schwach indexiert.** `_ki_erfahrung.yaml` (oder Äquivalent) ist global, aber Effektoren fragen ihn selten. LessonsAggregator (Phase 4.2) liefert die Infrastruktur; Konsumenten verdrahten den Pull-Pfad.

2. **Provenance-Lücken.** Provenance-Container ist da (Phase 4.0), aber die existing Phase-1+2+3-Typen (Plan, DoD, LifecycleTransition) haben heute partielle Provenance — Phase 6 unifiziert.

3. **Versionierung.** git tracked das Entity-Verzeichnis — aber strukturierte Diffs (was hat sich semantisch geändert) fehlen. `_aenderungen.yaml` als Audit-Log ist Konvention, kein Tooling zum Vergleich „Steckbrief Stand März vs. Stand Mai".

4. **Externe-Quelle-Drift.** Der Scan zeigt Verzeichnisse, aber wenn ein Mitarbeiter manuell auf der externen Quelle eine wichtige Datei anlegt, merkt das KI-System es nicht zeitnah. Üblich: Scan periodisch, das ist hinreichend aber nicht reaktiv.
