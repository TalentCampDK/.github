import os
import requests
import base64
import json

# --- KONFIGURATION ---
GITHUB_ORG = os.getenv("GITHUB_ORG")
TOKEN = os.getenv("GH_TOKEN")
HEADERS = {"Authorization": f"token {TOKEN}"}

README_PATH = "profile/README.md"


def get_course_data():
    """
    Henter kursusdata fra alle repositories i GitHub-organisationen.
     - For hver repository, tjekker den for en 'meta.json' fil.
     - Hvis filen findes, dekoder den indholdet og tilføjer det til kursuslisten.
     - Returnerer en liste af kursusmetadata.
    """
    all_courses = []
    page = 1
    while True:
        repos_url = (
            f"https://api.github.com/orgs/{GITHUB_ORG}/repos?per_page=100&page={page}"
        )
        res = requests.get(repos_url, headers=HEADERS, timeout=30)
        repos = res.json()

        if not repos or len(repos) == 0:
            break

        for repo in repos:
            meta_url = f"https://api.github.com/repos/{GITHUB_ORG}/{repo['name']}/contents/meta.json"
            meta_res = requests.get(meta_url, headers=HEADERS, timeout=30)

            if meta_res.status_code == 200:
                content = base64.b64decode(meta_res.json()["content"]).decode("utf-8")
                meta = json.loads(content)
                meta["url"] = repo["html_url"]
                all_courses.append(meta)
        page += 1
    return all_courses


# TODO: sørg for at det ikke lukket helt hvis en meta.json er forkert formateret,
# TODO: sørg for at der til hvert kursus er den rigtige information, lige nu er informationen i loopet, hvilket er forker
def build_markdown(courses):
    """
    Bygger en Markdown-struktur baseret på kursusdataene.
     - Kurserne grupperes først efter type (Aspirant eller Folkeskole).
     - Derefter grupperes de efter årstal.
     - For Aspirant-kurser, grupperes de yderligere efter samling.
     - For Folkeskole-kurser, vises de direkte under årstallet.
     - Returnerer den færdige Markdown-struktur som en streng.
    """
    # Vi bygger et træ: Type -> Årstal -> (Evt. Samling) -> Kurser
    tree = {}
    for c in courses:
        # Standardisering af data
        raw_type = str(c.get("type", "Andet")).lower()
        c_type = "Aspirant" if "aspirant" in raw_type else "Folkeskole"
        grade = str(c.get("grade", ""))
        year = c.get("year", "Ukendt år")
        camp_number = str(c.get("camp_number", "?"))

        if c_type not in tree:
            tree[c_type] = {}
        if year not in tree[c_type]:
            tree[c_type][
                year
            ] = []  # Vi starter med en liste, som vi kan strukturere senere

        tree[c_type][year].append(c)

    md = "# Kursus Arkiv\n\n"

    # Sorter typer (Aspirant øverst, så Folkeskole)
    for c_type in sorted(tree.keys()):
        md += f"## {c_type}\n\n"

        # Sorter årstal (nyeste først)
        for year in sorted(tree[c_type].keys(), reverse=True):
            md += f"<details>\n  <summary><h3>Årstal: {year}</h3></summary>\n\n"

            courses_in_year = tree[c_type][year]

            if c_type == "Aspirant":
                # LOGIK FOR ASPIRANT: Grupper efter Samling
                camps = {}
                for c in courses_in_year:
                    camp_name = f"Samling {camp_number}"
                    if camp_name not in camps:
                        camps[camp_name] = []
                    camps[camp_name].append(c)

                for camp_name in sorted(camps.keys()):
                    md += f"  <details style='margin-left: 20px;'>\n    <summary><h4>{camp_name}</h4></summary>\n\n"
                    for repo in camps[camp_name]:
                        name = repo.get(
                            "display_name", repo.get("name", "Navn mangler")
                        )
                        md += f"  * [{name}]({repo['url']})\n"
                    md += "  </details>\n"

            else:
                folkeskole_display = f"{grade}. klasse, camp {camp_number} *()*"
                # LOGIK FOR FOLKESKOLE: Ingen samlinger, brug 'long_display_name'
                # Vi sorterer dem alfabetisk efter det lange navn
                sorted_folkeskole = sorted(
                    courses_in_year, key=lambda x: x.get("long_display_name", "")
                )
                for repo in sorted_folkeskole:
                    md += f"  * [{folkeskole_display}]({repo['url']})\n"

            md += "</details>\n\n"

        md += "---\n\n"
    return md


def overwrite_readme(new_content):
    """
    Overskriver README.md med det nye indhold.
    Hvis filen ikke findes, oprettes den.
    """
    os.makedirs(os.path.dirname(README_PATH), exist_ok=True)
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)


if __name__ == "__main__":
    data = get_course_data()
    archive_md = build_markdown(data)
    overwrite_readme(archive_md)
    print(f"Succes! {README_PATH} er opdateret.")
