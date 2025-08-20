import requests

project_id = 2
token = "1addb5a9b8ee9e5080e879bb9cc8a896cc9fb4dd0aab60d6bac963f286d16685528e03279ad09f22"
headers = {"Authorization": f"Bearer {token}"}

# Get language metadata
lang_data = requests.get("https://api.linku.la/v1/languages").json()

# Get file IDs
files_url = f"https://linku.api.crowdin.com/api/v2/projects/{project_id}/files?limit=500"
files_resp = requests.get(files_url, headers=headers).json()

definitions_file_id = next((f['data']['id'] for f in files_resp['data'] if f['data']['name'] == "definitions.toml"), 106)
commentary_file_id = next((f['data']['id'] for f in files_resp['data'] if f['data']['name'] == "commentary.toml"), 104)

def get_progress(file_id):
    url = f"https://linku.api.crowdin.com/api/v2/projects/{project_id}/files/{file_id}/languages/progress?limit=500"
    resp = requests.get(url, headers=headers)
    return {entry['data']['language']['id']: entry['data']['translationProgress'] for entry in resp.json().get('data', [])}

definitions_progress = get_progress(definitions_file_id)
commentary_progress = get_progress(commentary_file_id)

# Merge and compute scores
merged = {}
for lang_id in set(definitions_progress) | set(commentary_progress):
    merged[lang_id] = {
        "definitions": definitions_progress.get(lang_id, 0),
        "commentary": commentary_progress.get(lang_id, 0)
    }

sorted_langs = sorted(
    merged.items(),
    key=lambda x: (
        -(x[1]["definitions"] + 0.1 * x[1]["commentary"]),  # descending score
        x[0]  # ascending lang_id
    )
)

# Find and remove English entry
english_entry = None
for i, (lang_id, stats) in enumerate(sorted_langs):
    if lang_id == "en":
        english_entry = sorted_langs.pop(i)
        break

replacements = {
    "ido": "io",
    "isvc": "isv",
    "ceb_l": "ceb",
    "tl_l": "tl"
}

# Generate README.md
with open('README.template.md', 'r', encoding='utf-8') as file:
    content = file.read()  # reads entire file as a string

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content + "  \n\n")
        for lang_id, stats in sorted_langs:
            # check if in replacements otherwise use langid
            lang_id = replacements.get(lang_id, lang_id)
            info = lang_data.get(lang_id)


            if not info:
                print("didnt find id for " + lang_id + ", searching locale")
                info = next((v for v in lang_data.values() if v.get("locale") == lang_id), {})
            name = info.get("name", {}).get("en", lang_id)
            endonym = info.get("name", {}).get("endonym", "")
            locale = info.get("locale", "")
            defs = stats["definitions"]
            comm = stats["commentary"]
            f.write(f"\n## {name}  \n({endonym}) - `{locale}`  \nDefinitions: {defs}%, Commentary: {comm}%  \nhttps://github.com/iamasink/ankideck-tokipona/releases/latest/download/toki-pona-deck-{lang_id}.apkg")

