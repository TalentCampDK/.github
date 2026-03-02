import os
import requests
import base64
import json

# --- KONFIGURATION ---
GITHUB_ORG = os.getenv("GITHUB_ORG")
TOKEN = os.getenv("GH_TOKEN")
HEADERS = {"Authorization": f"token {TOKEN}"}

README_PATH = "profiles/README.md"


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


def build_markdown(courses):
    """
    Bygger en Markdown-struktur baseret på kursusdata.
    """
    tree = {}
    for c in courses:
        y = c.get("year", "Ukendt år")
        cn = f"Samling {c.get('camp_number', '?')}"
        tree.setdefault(y, {}).setdefault(cn, []).append(c)

    md = "# Kursus Arkiv\n\n"
    for year in sorted(tree.keys(), reverse=True):
        md += f"<details>\n  <summary><h2>Årstal: {year}</h2></summary>\n\n"
        for camp in sorted(tree[year].keys()):
            md += f"  <details style='margin-left: 20px;'>\n    <summary><h3>{camp}</h3></summary>\n\n"
            for repo in tree[year][camp]:
                md += f"    * [{repo['display_name']}]({repo['url']}) — *{repo['grade_level']}*\n"
            md += "  </details>\n"
        md += "</details>\n"
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
