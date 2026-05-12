# organism-core — Architektur

> Stand: 2026-05-09 · Pflege: bei jeder strukturellen Änderung

Dieses Verzeichnis ist die **Landkarte** des Skeletts. Es ist nicht der Code,
nicht die API-Doku und auch nicht die Roadmap — es ist der Plan, wie die
einzelnen Teile **zusammenwirken**, damit man sie verstehen und gezielt
verbessern kann ohne sich an Details zu verlieren.

## Wofür das gut ist

Das Skelett besteht aus mehreren Effektoren, einem zentralen Service-Layer,
mehreren Lernschleifen, einer Sandbox-Schicht und einem wachsenden
Telemetrie-System. Jedes Stück für sich ist überschaubar — das
**Zusammenspiel** ist die eigentliche Komplexität. Wenn ein Effektor
schlechte Ergebnisse liefert, liegt die Ursache fast nie nur im Effektor
selbst, sondern in einer fehlenden Verbindung (Tool hat Entity-Profile
nicht gelesen, hat User nicht gefragt, hat Lesson aus anderem Tool
ignoriert).

Diese Doku adressiert genau diese Verbindungen.

## Zwei Leitbilder, ein System

**Multi-Tool-System** (Strukturbild) — mehrere Effektoren, jeder mit
eigenem Zuständigkeitsbereich, verbunden über einen zentralen
Service-Layer. Beschreibt **wie** das System gebaut ist.

**Kohärenter Assistent** (Erlebnisbild) — eine Stimme, eine Persönlichkeit,
eine Schnittstelle, alles andere unsichtbar im Hintergrund. Beschreibt
**wie sich** das System anfühlen soll.

Heute näher am Multi-Tool-System als am kohärenten Assistenten. Die Lücke
ist das eigentliche Wachstums-Thema (siehe
[08_GOLD_PATTERNS.md](08_GOLD_PATTERNS.md)).

## Lese-Pfad

Wer das Projekt zum ersten Mal versteht, geht der Reihe nach:

| # | Datei | Frage die es beantwortet | Lesedauer |
|---|---|---|---|
| 0 | [00_LEITBILD.md](00_LEITBILD.md) | Was bauen wir, warum so, für wen? | 5 min |
| 1 | [01_ANATOMIE.md](01_ANATOMIE.md) | Welche Tools gibt es, was ist ihre Domäne? | 10 min |
| 2 | [02_NERVENSYSTEM.md](02_NERVENSYSTEM.md) | Wie koordinieren die Tools? Was macht der Service-Layer? | 10 min |
| 3 | [03_GEDAECHTNIS.md](03_GEDAECHTNIS.md) | Wo lebt die Wahrheit? Entity-Memory, Vector-Store, Provenance | 10 min |
| 4 | [04_LERNEN.md](04_LERNEN.md) | Wie verbessert sich das System? Human-Loop, Karpathy-Loop, Plan-Gate | 10 min |
| 5 | [05_REFLEXBOGEN.md](05_REFLEXBOGEN.md) | Welche Patterns sind verbindlich? (Entity-Profile-zuerst, Provenance-Pflicht ...) | 10 min |
| 6 | [06_SELF_IMPROVEMENT.md](06_SELF_IMPROVEMENT.md) | Self-Improvement-Loop — was wird für RL getrackt? | 5 min |
| 7 | [07_REIFEGRAD.md](07_REIFEGRAD.md) | Wo stehen wir, was wackelt, was kommt? | 10 min |
| 8 | [08_GOLD_PATTERNS.md](08_GOLD_PATTERNS.md) | Reasoning-Loop über die Doku — wo liegt der Hebel zum kohärenten Assistenten? | 10 min |
| 9 | [09_FRAMEWORK.md](09_FRAMEWORK.md) | Universelles Skelett — 5 Bauteile + Aktions-Lebenszyklus, übertragbar auf andere Domänen | 10 min |
| 10 | [10_LANDSCHAFT.md](10_LANDSCHAFT.md) | Was es draußen schon gibt — Adopt vs. Inspiration vs. USP, mit konkreten Bausteinen (Anthropic Skills, Langfuse, E2B, ...) | 15 min |

Wer **etwas Konkretes ändern** will, springt direkt zu 05 (Patterns), liest
die relevante Regel und vergleicht mit Anatomie/Nervensystem.

Wer **debuggt**, fängt mit 02 (Service-Layer) und 03 (Wahrheitsquellen) an
— die meisten Bugs sind Datenfluss-Bugs, nicht Algorithmik-Bugs.

## Verhältnis zu anderen Dokumenten

| Doku | Zweck | Verhältnis zu diesem Verzeichnis |
|---|---|---|
| [`docs/M5_WHITEPAPER.de.md`](../M5_WHITEPAPER.de.md) | Single-document Pattern-Whitepaper | Verdichtete Variante — hier mehr Detail, dort schneller Überblick |
| [`docs/STAR.de.md`](../STAR.de.md) | M5 Star-Engine Konzept-Doku | Vertiefung zu Kapitel 9 (Framework) und 5 (Reflexbogen P1/P3) |
| [`docs/LIFECYCLE.de.md`](../LIFECYCLE.de.md) | Action-Lifecycle a→e State-Machine | Vertiefung zu Kapitel 9 (Aktions-Lebenszyklus) |
| [`docs/OBSERVABILITY.de.md`](../OBSERVABILITY.de.md) | Provenance, OTel-GenAI, Langfuse-Adapter | Vertiefung zu Kapitel 3 (Gedächtnis) und 4 (Lernen) |

## Pflege-Regel

Eine strukturelle Änderung am System (neues Tool, neuer Service, neuer
Lern-Loop, neuer Datenfluss) wird in **diesem Verzeichnis** dokumentiert
**bevor** sie eingebaut wird. Die Doku ist das Vertragspapier, der Code
die Umsetzung.

Detail-Tweaks (Schwellwerte, Kernel-Größen, Prompt-Texte) gehören NICHT
hier rein — die leben im Code mit Inline-Kommentar.
