import json
import random

# Визначаємо всі комбінації
cases = ["Nominativ", "Akkusativ", "Dativ", "Genitiv"]
genders = ["masculine", "feminine", "neuter", "plural"]

# Приклади речень для генерації
examples = {
    # --- Nominativ ---
    ("Nominativ", "masculine"): [
        ("___ Mann liest ein Buch.", ["Der", "Die", "Das", "Den"], 0,
         "У називному відмінку чоловічого роду артикль — 'der'."),
        ("___ Hund schläft.", ["Der", "Die", "Das", "Den"], 0,
         "У називному відмінку чоловічого роду артикль — 'der'."),
    ],
    ("Nominativ", "feminine"): [
        ("___ Frau trinkt Tee.", ["Der", "Die", "Das", "Den"], 1,
         "У називному відмінку жіночого роду артикль — 'die'."),
        ("___ Katze schläft.", ["Der", "Die", "Das", "Den"], 1,
         "У називному відмінку жіночого роду артикль — 'die'."),
    ],
    ("Nominativ", "neuter"): [
        ("___ Kind spielt im Garten.", ["Der", "Die", "Das", "Dem"], 2,
         "У називному відмінку середнього роду артикль — 'das'."),
        ("___ Auto ist neu.", ["Der", "Die", "Das", "Dem"], 2,
         "У називному відмінку середнього роду артикль — 'das'."),
    ],
    ("Nominativ", "plural"): [
        ("___ Kinder spielen Fußball.", ["Die", "Der", "Das", "Den"], 0,
         "У називному відмінку множини артикль — 'die'."),
        ("___ Bücher liegen auf dem Tisch.", ["Die", "Der", "Das", "Den"], 0,
         "У називному відмінку множини артикль — 'die'."),
    ],

    # --- Akkusativ ---
    ("Akkusativ", "masculine"): [
        ("Ich sehe ___ Hund.", ["Der", "Den", "Dem", "Des"], 1,
         "У знахідному відмінку чоловічого роду артикль — 'den'."),
        ("Er kauft ___ Tisch.", ["Der", "Den", "Dem", "Des"], 1,
         "У знахідному відмінку чоловічого роду артикль — 'den'."),
    ],
    ("Akkusativ", "feminine"): [
        ("Ich kenne ___ Frau.", ["Der", "Die", "Das", "Den"], 1,
         "У знахідному відмінку жіночого роду артикль — 'die'."),
        ("Er besucht ___ Schule.", ["Der", "Die", "Das", "Den"], 1,
         "У знахідному відмінку жіночого роду артикль — 'die'."),
    ],
    ("Akkusativ", "neuter"): [
        ("Sie hat ___ Buch.", ["Der", "Die", "Das", "Dem"], 2,
         "У знахідному відмінку середнього роду артикль — 'das'."),
        ("Er öffnet ___ Fenster.", ["Der", "Die", "Das", "Dem"], 2,
         "У знахідному відмінку середнього роду артикль — 'das'."),
    ],
    ("Akkusativ", "plural"): [
        ("Ich sehe ___ Kinder.", ["Die", "Der", "Das", "Den"], 0,
         "У знахідному відмінку множини артикль — 'die'."),
        ("Er liest ___ Zeitungen.", ["Die", "Der", "Das", "Den"], 0,
         "У знахідному відмінку множини артикль — 'die'."),
    ],

    # --- Dativ ---
    ("Dativ", "masculine"): [
        ("Ich helfe ___ Mann.", ["Der", "Den", "Dem", "Des"], 2,
         "У давальному відмінку чоловічого роду артикль — 'dem'."),
        ("Er gibt ___ Hund Futter.", ["Der", "Den", "Dem", "Des"], 2,
         "У давальному відмінку чоловічого роду артикль — 'dem'."),
    ],
    ("Dativ", "feminine"): [
        ("Ich danke ___ Frau.", ["Der", "Die", "Das", "Dem"], 0,
         "У давальному відмінку жіночого роду артикль — 'der'."),
        ("Er hilft ___ Katze.", ["Der", "Die", "Das", "Dem"], 0,
         "У давальному відмінку жіночого роду артикль — 'der'."),
    ],
    ("Dativ", "neuter"): [
        ("Ich spiele mit ___ Kind.", ["Der", "Die", "Das", "Dem"], 3,
         "У давальному відмінку середнього роду артикль — 'dem'."),
        ("Er sitzt bei ___ Auto.", ["Der", "Die", "Das", "Dem"], 3,
         "У давальному відмінку середнього роду артикль — 'dem'."),
    ],
    ("Dativ", "plural"): [
        ("Ich spreche mit ___ Kindern.", ["Die", "Der", "Den", "Dem"], 2,
         "У давальному відмінку множини артикль — 'den'."),
        ("Er hilft ___ Freunden.", ["Die", "Der", "Den", "Dem"], 2,
         "У давальному відмінку множини артикль — 'den'."),
    ],

    # --- Genitiv ---
    ("Genitiv", "masculine"): [
        ("Das Buch ___ Mannes ist interessant.", ["Der", "Die", "Das", "Des"], 3,
         "У родовому відмінку чоловічого роду артикль — 'des'."),
        ("Die Tasche ___ Hundes ist groß.", ["Der", "Die", "Das", "Des"], 3,
         "У родовому відмінку чоловічого роду артикль — 'des'."),
    ],
    ("Genitiv", "feminine"): [
        ("Das Kleid ___ Frau ist schön.", ["Der", "Die", "Das", "Des"], 0,
         "У родовому відмінку жіночого роду артикль — 'der'."),
        ("Die Farbe ___ Katze ist schwarz.", ["Der", "Die", "Das", "Des"], 0,
         "У родовому відмінку жіночого роду артикль — 'der'."),
    ],
    ("Genitiv", "neuter"): [
        ("Der Name ___ Kindes ist Peter.", ["Der", "Die", "Das", "Des"], 3,
         "У родовому відмінку середнього роду артикль — 'des'."),
        ("Die Tür ___ Hauses ist offen.", ["Der", "Die", "Das", "Des"], 3,
         "У родовому відмінку середнього роду артикль — 'des'."),
    ],
    ("Genitiv", "plural"): [
        ("Die Spiele ___ Kinder sind laut.", ["Der", "Die", "Das", "Des"], 0,
         "У родовому відмінку множини артикль — 'der'."),
        ("Die Seiten ___ Bücher sind alt.", ["Der", "Die", "Das", "Des"], 0,
         "У родовому відмінку множини артикль — 'der'."),
    ],
}

quiz = []

# Генеруємо по 10 завдань на кожну комбінацію
for case in cases:
    for gender in genders:
        base_examples = examples.get((case, gender), [])
        for i in range(10):
            if base_examples:
                q, opts, ans, expl = random.choice(base_examples)
                quiz.append({
                    "type": "singleSelect",
                    "case": case,
                    "gender": gender,
                    "question": q,
                    "options": opts,
                    "answer": [ans],
                    "explanation": expl
                })

# Зберігаємо у JSON
with open("deutch_articles.json", "w", encoding="utf-8") as f:
    json.dump(quiz, f, ensure_ascii=False, indent=2)

print(f"Згенеровано {len(quiz)} вправ")