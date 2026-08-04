import json
from typing import Any

from services.crossfit_movements import (
    find_movement,
    movement_patterns_to_classification,
)
from services.mistral_service import call_mistral
from services.utils import (
    clean_json_response,
    create_stable_hash,
    normalize_classification,
)


MOVEMENT_PATTERNS = [
    "squat",
    "hinge",
    "lunge",
    "horizontal_push",
    "vertical_push",
    "horizontal_pull",
    "vertical_pull",
    "carry",
    "locomotion",
    "rotation",
    "anti_rotation",
    "anti_extension",
    "anti_flexion",
    "isolation",
    "mixed",
]

MUSCLE_GROUPS = [
    "quadriceps",
    "hamstrings",
    "glutes",
    "adductors",
    "abductors",
    "calves",
    "hip_flexors",
    "chest",
    "latissimus",
    "trapezius",
    "rhomboids",
    "front_delts",
    "side_delts",
    "rear_delts",
    "biceps",
    "triceps",
    "forearms_grip",
    "abdominals",
    "obliques",
    "spinal_erectors",
    "deep_core",
]

TRAINING_GOALS = [
    "max_strength",
    "hypertrophy",
    "strength_endurance",
    "speed_strength",
    "explosive_strength",
    "aerobic_base",
    "threshold",
    "vo2max",
    "anaerobic_capacity",
    "technique",
    "mobility",
    "recovery",
]

LOAD_TYPES = [
    "mechanical",
    "metabolic",
    "eccentric",
    "concentric",
    "isometric",
    "impact",
    "cardiovascular",
    "neuromuscular",
    "coordination",
    "grip",
]

VOLUME_METRICS = [
    "sets",
    "repetitions",
    "weight_kg",
    "volume_load_kg",
    "duration_minutes",
    "distance_km",
    "elevation_m",
    "rounds",
    "work_seconds",
    "rest_seconds",
    "time_in_zone_minutes",
    "weight_distance",
]


def create_coach_state_key(
    *,
    name: str,
    sportart: str,
    level: str,
    duration_minutes: int,
    rpe: int,
    score: int,
    injuries: str,
    comment: str,
    exercises: list[dict[str, Any]],
    history_summary: dict[str, Any],
    training_analysis: dict[str, Any],
) -> str:
    """
    Erstellt einen Cache-Schlüssel aus aktuellem Workout
    und Trainingshistorie.

    Die regelbasierten Coach-Daten werden aus diesen Eingaben
    abgeleitet und müssen deshalb nicht separat gehasht werden.
    """

    return create_stable_hash(
        {
            "name": name,
            "sportart": sportart,
            "level": level,
            "duration_minutes": (
                duration_minutes
            ),
            "rpe": rpe,
            "score": score,
            "injuries": injuries,
            "comment": comment,
            "exercises": exercises,
            "history_summary": (
                history_summary
            ),
            "training_analysis": (
                training_analysis
            ),
        }
    )


def build_coach_prompt(
    *,
    user_name: str,
    user_sport: str,
    user_level: str,
    duration_minutes: int,
    user_rpe: int,
    total_score: int,
    status_text: str,
    user_injuries: str,
    user_comment: str,
    exercises: list[dict[str, Any]],
    history_summary: dict[str, Any],
    training_analysis: dict[str, Any],
    readiness: dict[str, Any],
    weekly_focus: dict[str, Any],
    positive_observations: list[str],
) -> str:
    """
    Erstellt den Coach-Prompt aus regelbasierten Befunden
    und der kompakten Trainingshistorie.
    """

    top_findings = (
        training_analysis.get(
            "top_findings",
            [],
        )
        if isinstance(
            training_analysis,
            dict,
        )
        else []
    )

    analysis_overview = (
        training_analysis.get(
            "overview",
            {},
        )
        if isinstance(
            training_analysis,
            dict,
        )
        else {}
    )

    window_7 = (
        history_summary.get(
            "windows",
            {},
        ).get(
            "7_days",
            {},
        )
        if isinstance(
            history_summary,
            dict,
        )
        else {}
    )

    window_28 = (
        history_summary.get(
            "windows",
            {},
        ).get(
            "28_days",
            {},
        )
        if isinstance(
            history_summary,
            dict,
        )
        else {}
    )

    compact_history = {
        "7_days": window_7,
        "28_days": window_28,
        "days_since_last_load": (
            history_summary.get(
                "days_since_last_load",
                {},
            )
            if isinstance(
                history_summary,
                dict,
            )
            else {}
        ),
        "crossfit_coverage": (
            history_summary.get(
                "crossfit_coverage",
                {},
            )
        ),

        "missing_crossfit_movements": (
            history_summary.get(
                "missing_crossfit_movements",
                [],
            )
        ),
    }

    return f"""
Du bist ein erfahrener Performance Coach für CrossFit, HYROX,
Laufen und funktionelles Krafttraining.

Der Athlet folgt grundsätzlich einem eigenen Trainingsplan oder dem
Programming seines Gyms. Die App ersetzt dieses Programming nicht.
Bewerte das tatsächlich absolvierte Workout im Kontext der
Trainingshistorie und unterstütze nur bei Einordnung, Anpassung oder
einer kleinen optionalen Ergänzung.

Die regelbasierten Coach-Daten unten sind deine primäre
Entscheidungsgrundlage. Formuliere sie verständlich und natürlich,
ohne ihnen zu widersprechen. Ergänze nur Aussagen, die durch die
übrigen Trainingsdaten eindeutig gestützt werden.

SCHREIBSTIL

- Schreibe ausschließlich auf Deutsch.
- Schreibe klar, direkt, konstruktiv und persönlich.
- Vermeide technische Sprache und Fitnessfloskeln.
- Wiederhole Daten nicht bloß, sondern erkläre ihre Bedeutung.
- Verwende innerhalb der Abschnitte Markdown für echte Formatierung:
  **fett** für zentrale Begriffe und *kursiv* nur sparsam.
- Verwende keine Markdown-Überschriften und keine sichtbaren
  Rautenzeichen.
- Schreibe insgesamt maximal 190 Wörter.

VERBINDLICHE ANALYSEREGELN

- Triff nur Aussagen, die aus den übergebenen Daten ableitbar sind.
- Erfinde keine Informationen.
- Mache keine Aussagen über Motivation, Disziplin, Konzentration,
  mentale Stärke oder Übungstechnik, sofern dafür keine Daten vorliegen.
- Jede Empfehlung muss auf einer konkreten Beobachtung beruhen.
- Verwende nur Zahlen und Zeiträume, die in den Daten enthalten oder
  eindeutig daraus berechenbar sind.
- Nenne Belastungsscores nicht als absolute Zahlen. Beschreibe nur,
  ob die Belastung gestiegen, gesunken oder stabil geblieben ist.
- Wenn die Daten für eine Aussage nicht ausreichen, lasse sie weg.
- Keine Diagnosen und keine medizinischen Aussagen.
- Bei Beschwerden nur vorsichtige Belastungssteuerung oder
  professionelle Abklärung empfehlen.
- Gib keine widersprüchlichen Empfehlungen.
- Erstelle keinen Wochenplan und keine vollständige Trainingsprogrammierung.
- Fordere den Athleten niemals pauschal auf, sein bestehendes Programming zu ersetzen.
- Formuliere Empfehlungen immer in einer dieser Rollen:
  Einordnung des bestehenden Plans, Intensitätsanpassung, kleine optionale Ergänzung
  oder einzelne Ersatzoption, falls eine geplante Einheit verpasst wurde.
- Der regelbasierte Trainingsstatus ist verbindlich.
- Der regelbasierte Schwerpunkt ist verbindlich, sofern er nicht
  offensichtlich mit dokumentierten Beschwerden kollidiert.
- Die drei positiven Beobachtungen sind bevorzugt zu verwenden.
  Formuliere sie natürlicher, aber verändere ihre Aussage nicht.

INTERNE BEGRIFFE

Interne Kategorien, Variablennamen und englische Trainingscodes dürfen
für den Athleten niemals sichtbar sein.

Übersetze sie verständlich, zum Beispiel:

vertical_pull → Klimmzüge oder Latziehen
horizontal_pull → Rudern
vertical_push → Überkopfdrücken
horizontal_push → Liegestütze oder Bankdrücken
hinge → Kreuzheben oder Hüftstreckbewegungen
squat → Kniebeugen
carry → Trageübungen
aerobic_base → lockeres Ausdauertraining
strength_endurance → Kraftausdauer
explosive_strength → Explosivkraft

ANTWORTFORMAT

Das Dashboard zeigt Trainingsstatus, positive Beobachtungen und einen
unterstützenden Schwerpunkt bereits regelbasiert an. Wiederhole diese
Bereiche nicht. Behandle den Athleten als jemanden mit bestehendem Plan.

Nutze exakt diese zwei Überschriften als einfache Textzeilen,
jeweils ohne ##, ** oder Doppelpunkt:

Coach-Zusammenfassung

Schreibe 3 bis 5 kurze Sätze. Erkläre die wichtigste Entwicklung und
warum der regelbasierte Schwerpunkt aktuell sinnvoll ist. Verknüpfe
Trainingshäufigkeit, Belastung oder Trainingsmix nur, wenn die Daten
eine klare Aussage erlauben. Wiederhole die drei positiven
Beobachtungen nicht als Liste.

Empfehlung für dein nächstes Training

Gib eine übersichtliche, unmittelbar umsetzbare Entscheidungshilfe aus.
Sie muss enthalten:
- **Umgang mit dem Plan:** normal folgen, kontrolliert anpassen oder bei freier Wahl ersetzen
- **Optionale Ergänzung:** nur wenn aus den Daten sinnvoll; klein genug, um das Haupttraining nicht zu ersetzen
- **Intensität:** klare Belastungsvorgabe
- **Begründung:** eine konkrete Beobachtung aus den Daten

Wenn der bestehende Plan problemlos passt, sage das ausdrücklich.
Wenn eine Ergänzung sinnvoll ist, nenne höchstens einen kompakten Block
mit konkreten Übungen oder Trainingsbestandteilen. Erstelle niemals einen
Wochenplan. Die Empfehlung muss zum Trainingsstatus, zum regelbasierten
Fokus, zum Sportziel und zu dokumentierten Beschwerden passen.

REGELBASIERTE COACH-DATEN

Trainingsstatus:
{json.dumps(readiness, ensure_ascii=False, indent=2)}

Priorisierter Schwerpunkt:
{json.dumps(weekly_focus, ensure_ascii=False, indent=2)}

Belegbare positive Beobachtungen:
{json.dumps(positive_observations[:3], ensure_ascii=False, indent=2)}

ATHLETENPROFIL

Name:
{user_name}

Sport:
{user_sport}

Level:
{user_level}

Trainingsdauer:
{duration_minutes} Minuten

RPE:
{user_rpe}

Belastungsstatus:
{status_text}

Beschwerden:
{user_injuries if user_injuries else "Keine"}

Kommentar:
{user_comment if user_comment else "Keiner"}

AKTUELLES WORKOUT

{json.dumps(exercises, ensure_ascii=False, indent=2)}

TRAININGSHISTORIE

{json.dumps(compact_history, ensure_ascii=False, indent=2)}

PRIORISIERTE FINDINGS

{json.dumps(top_findings[:5], ensure_ascii=False, indent=2)}

ANALYSE

{json.dumps(analysis_overview, ensure_ascii=False, indent=2)}
""".strip()


def get_coach_feedback(
    *,
    api_key: str,
    model: str,
    user_name: str,
    user_sport: str,
    user_level: str,
    duration_minutes: int,
    user_rpe: int,
    total_score: int,
    status_text: str,
    user_injuries: str,
    user_comment: str,
    exercises: list[dict[str, Any]],
    history_summary: dict[str, Any],
    training_analysis: dict[str, Any],
    readiness: dict[str, Any],
    weekly_focus: dict[str, Any],
    positive_observations: list[str],
) -> str:
    """
    Erstellt den Prompt und ruft den Mistral-Coach auf.
    """

    prompt = build_coach_prompt(
        user_name=user_name,
        user_sport=user_sport,
        user_level=user_level,
        duration_minutes=duration_minutes,
        user_rpe=user_rpe,
        total_score=total_score,
        status_text=status_text,
        user_injuries=user_injuries,
        user_comment=user_comment,
        exercises=exercises,
        history_summary=history_summary,
        training_analysis=training_analysis,
        readiness=readiness,
        weekly_focus=weekly_focus,
        positive_observations=positive_observations,
    )

    return call_mistral(
        api_key=api_key,
        model=model,
        content=prompt,
    )


def build_workout_classification_prompt(
    *,
    exercises: list[dict[str, Any]],
    user_rpe: int | None = None,
    sport_goal: str = "",
) -> str:
    """
    Erstellt den Prompt für die Klassifikation
    aller Übungen eines Workouts.
    """

    taxonomy = {
        "movement_patterns": MOVEMENT_PATTERNS,
        "muscle_groups": MUSCLE_GROUPS,
        "training_goals": TRAINING_GOALS,
        "load_types": LOAD_TYPES,
        "volume_metrics": VOLUME_METRICS,
    }

    output_example = {
        "workout_erkannt": True,
        "uebungen": [
            {
                "name": "Back Squat",
                "details": "4 x 5 mit 80 kg",
                "canonical_name": "Back Squat",
                "canonical_id": "back_squat",
                "movement_patterns": [
                    {
                        "type": "squat",
                        "role": "primary",
                        "contribution": 1.0,
                    }
                ],
                "muscle_groups": [
                    {
                        "type": "quadriceps",
                        "role": "primary",
                        "contribution": 1.0,
                    },
                    {
                        "type": "glutes",
                        "role": "primary",
                        "contribution": 0.8,
                    },
                ],
                "training_goal": {
                    "type": "max_strength",
                    "confidence": 0.9,
                    "reason": "Schwere Sätze mit wenigen Wiederholungen.",
                },
                "load_types": [
                    {
                        "type": "mechanical",
                        "weight": 1.0,
                    },
                    {
                        "type": "neuromuscular",
                        "weight": 0.8,
                    },
                ],
                "volume": {
                    "sets": 4,
                    "repetitions": 5,
                    "weight_kg": 80,
                    "volume_load_kg": 1600,
                    "duration_minutes": None,
                    "distance_km": None,
                    "elevation_m": None,
                    "rounds": None,
                    "work_seconds": None,
                    "rest_seconds": None,
                    "time_in_zone_minutes": None,
                    "weight_distance": None,
                },
                "supported_volume_metrics": [
                    "sets",
                    "repetitions",
                    "weight_kg",
                    "volume_load_kg",
                ],
                "overall_confidence": 0.95,
                "ambiguity_reason": None,
                "notes": [],
            }
        ],
    }

    return f"""
Du bist ein präzises sportwissenschaftliches
Klassifikationssystem für eine Trainings-App.

Ordne jede angegebene Übung ausschließlich den
vorgegebenen Kategorien zu.

VORGEGEBENE KATEGORIEN:

{json.dumps(taxonomy, ensure_ascii=False, indent=2)}

REGELN:

1. Erfinde keine zusätzlichen Kategorien.

2. Jede Übung muss eindeutig anhand ihres Bewegungsnamens identifiziert werden.

3. canonical_name darf ausschließlich den kanonischen englischen
Übungsnamen enthalten.

4. Muskelgruppen erhalten eine Rolle:
   - primary
   - secondary
   - stabilizer

5. contribution und weight müssen zwischen
   0 und 1 liegen.

6. Die Summe der Muskelbeiträge muss nicht
   1 ergeben.

7. Das Trainingsziel muss anhand der konkreten
   Durchführung bestimmt werden.

8. Berücksichtige dafür insbesondere:
   - Wiederholungen,
   - Sätze,
   - Gewicht,
   - Dauer,
   - Distanz,
   - RPE,
   - Pausen,
   - Workout-Kontext.

9. Wenn das Trainingsziel nicht sicher bestimmbar ist:
   - training_goal.type = null
   - confidence entsprechend reduzieren
   - den Grund konkret benennen

10. Verändere die Eingabe niemals.
Die Felder "name" und "details" müssen exakt aus der Eingabe übernommen werden.
Übersetze, normalisiere, ergänze oder korrigiere diese Felder nicht.

11. canonical_name must contain ONLY the canonical exercise name.

Never include:
- repetitions
- sets
- distance
- duration
- weight
- workout structure (Buy-in, Cash-out, EMOM, AMRAP, For Time, Chipper, etc.)
- descriptive words (Heavy, Light, Fast, Strict, Weighted, etc.)

Examples:

✓ Run
✓ Row
✓ SkiErg
✓ BikeErg
✓ Back Squat
✓ Front Squat
✓ Thruster
✓ Clean
✓ Clean & Jerk
✓ Sit-up
✓ Russian Twist

Never:

✗ 800 Meter Run
✗ 50 Cal Row
✗ Heavy Back Squat
✗ Buy-in Row
✗ Cash-out Sit-ups

12. canonical_id must be the snake_case version of canonical_name.

    Examples:

    Run -> run
    Row -> row
    Back Squat -> back_squat
    Clean & Jerk -> clean_and_jerk
    Sit-up -> sit_up
    Russian Twist -> russian_twist

13. Volumenwerte nur eintragen, wenn sie aus der
    Eingabe eindeutig ableitbar sind.

14. volume_load_kg berechnet sich als:
    Sätze × Wiederholungen × Gewicht.

15. weight_distance berechnet sich als:
    Gesamtgewicht × Distanz in Metern.

16. Bei AMRAP, EMOM, RFT oder Chipper darf ein
    gesamter Block als Übung bestehen bleiben.

17. Bei mehrdeutigen oder unbekannten Übungen:
    - overall_confidence reduzieren
    - ambiguity_reason ausfüllen

18. Gib ausschließlich valides JSON zurück.

19. Verwende keinen Markdown-Codeblock.

20. Beginne die Antwort unmittelbar mit {{ und beende sie unmittelbar mit }}.

21. Schreibe vor oder nach dem JSON keinerlei Erklärung.

22. Verwende für fehlende Werte null und niemals Python-Werte
    wie None, True oder False. Verwende ausschließlich
    null, true und false.

23. Verwende keine Kommentare innerhalb des JSON.

24. Verwende niemals //-Kommentare oder /* ... */-Kommentare.

25. Schätze keine Dauer, Arbeitszeit, Pausenzeit,
    Wiederholungszahl oder Distanz.

26. Trage einen Volumenwert nur ein, wenn er direkt und
    eindeutig aus der Eingabe hervorgeht.

27. Erfinde niemals Informationen, die nicht ausdrücklich in der Eingabe enthalten sind.

Schätze oder ergänze niemals:
- Distanzen
- Rundenzahlen
- Wiederholungen
- Sätze
- Dauer
- Pausenzeiten
- Gewichte
- Workout-Struktur

Wenn eine Information nicht eindeutig aus der Eingabe hervorgeht, verwende null.

28. Berechne weight_distance nur für Übungen, bei denen
    ein Gewicht tatsächlich über eine Distanz getragen,
    geschoben oder gezogen wird.

29. Berechne weight_distance niemals aus dem Gewicht einer
    anderen Übung und der Distanz des Ruderns oder Laufens.

30. Verwende ausschließlich gültiges JSON ohne Kommentare,
    Erklärungen oder Anmerkungen außerhalb von Stringwerten.




SPORTLICHES ZIEL:

{sport_goal or "Nicht angegeben"}

GESAMT-RPE:

{user_rpe if user_rpe is not None else "Nicht angegeben"}

ÜBUNGEN:

{json.dumps(exercises, ensure_ascii=False, indent=2)}

ERWARTETE JSON-STRUKTUR:

{json.dumps(output_example, ensure_ascii=False, indent=2)}
""".strip()


def classify_workout(
    *,
    api_key: str,
    model: str,
    exercises: list[dict[str, Any]],
    user_rpe: int | None = None,
    sport_goal: str = "",
) -> dict[str, Any]:
    """
    Lässt Mistral alle Übungen klassifizieren und
    normalisiert anschließend die Antwort.
    """

    prompt = build_workout_classification_prompt(
        exercises=exercises,
        user_rpe=user_rpe,
        sport_goal=sport_goal,
    )

    raw_response = call_mistral(
        api_key=api_key,
        model=model,
        content=prompt,
    )

    print("=" * 80)
    print(raw_response)
    print("=" * 80)

    parsed_response = clean_json_response(
        raw_response
    )

    print("=" * 60)
    for exercise in parsed_response.get("uebungen", []):
        print(
            exercise.get("name"),
            "->",
            exercise.get("canonical_name"),
        )
    print("=" * 60)

    for exercise in parsed_response.get(
        "uebungen",
        [],
    ):
        if not isinstance(exercise, dict):
            continue

        movement = find_movement(
            exercise.get(
                "canonical_name",
                "",
            )
        )
        print(
            exercise.get("canonical_name"),
            "=>",
                movement.display_name if movement else "NICHT GEFUNDEN",
            )
        

        if movement is None:
            continue

        exercise["movement_patterns"] = (
            movement_patterns_to_classification(
                movement
            )
        )

    return normalize_classification(
        parsed_response,
        movement_patterns=MOVEMENT_PATTERNS,
        muscle_groups=MUSCLE_GROUPS,
        training_goals=TRAINING_GOALS,
        load_types=LOAD_TYPES,
        volume_metrics=VOLUME_METRICS,
    )