from pathlib import Path
import shutil
import requests
import genanki
import logging
import html
import re

# set custom guid with only the Word so it can be overwritten in future!
class MyNote(genanki.Note):
  @property
  def guid(self):
    return genanki.guid_for("iamasink toki pona", self.fields[0])

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s %(levelname)s: %(message)s",
	datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
AUDIO_SUBDIR = Path("ijo") / "kalama"
GLYPH_SUBDIR = Path("ijo") / "sitelensitelen" / "jonathangabel"
AUDIO_PEOPLE = ["kalaasi2023", "jlakuse"]

TARGET_AUDIO_DIR = BASE_DIR / "files" / "audio"
TARGET_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

ENABLED_CATEGORIES = [
	"core",
	"common",
	"uncommon",
	# "obscure",
	# "sandbox" # won't work by default
]

# Define your model
my_model = genanki.Model(
	1747075454,
	"Simple Model",
	fields=[
		{"name": "Word"}, 
		{"name": "Definition"},
		{"name": "Commentary"},
		{"name": "Creator"},
		{"name": "Coined Era"},
		{"name": "Coined Year"},
		{"name": "Book"},
		{"name": "Usage"},
		{"name": "Usage Category"},
		{"name": "Audio"}, # can have multiple "[sound:name.mp3] [sound:name2.mp3]"
		{"name": "Glyph"}
		#  {"name": },
		#  {"name": },
		 ],
		templates=[{
		"name": "Toki Pona Word",
		"qfmt": """
			<strong>{{Word}}</strong><br>
		""",
		"afmt": """
			<br/>
			{{FrontSide}}
			<hr id="answer">
			<div class="warningbanner">
				<span class="warning warningbanner-obscure warning{{Usage Category}}">This word is <span class="bold usagecatobscure">obscure</span>, so most speakers will not understand it.</span>
				<span class="warning warningbanner-sandbox warning{{Usage Category}}">This word is in the <b>sandbox</b>, so almost no speakers will understand it.</span>
			</div>
			{{Audio}}
			<br/>
			{{Glyph}}
			<br/>
			{{Definition}}
			<br/>
			Coined by <em>{{Creator}}</em> {{Coined Era}}, {{Coined Year}}
			Found in <span class="book">{{#Book}}{{Book}}{{/Book}}{{^Book}}No Book{{/Book}}</span>
			<hr>
			Usage: <span class="usagespan usagecat{{Usage Category}}">{{Usage Category}} · {{Usage}}</span>
			<div class="comment">{{Commentary}}</div>
		""",
		}],
	css="""
/* colours from nimi.li */
.usagecatcore {
	color: rgb(52 211 153);
}
.usagecatcommon {
	color: rgb(56 189 248);
}
.usagecatuncommon {
	color: rgb(250 204 21);
}
.usagecatobscure {
	color: rgb(232 121 249);
}
.usagecatsandbox {
	color: rgb(209 213 219);
}
/* unknown or unset category */
.usagecat {
	color: rgb(209 213 219);
}
.book, .bold {
	font-weight: bolder;
}
.warningbanner-obscure.warningobscure {
	visibility: visible !important;
}
.warningbanner-sandbox.warningsandbox {
	visibility: visible !important;
} 
.warning {
	visibility: collapse;
}
"""
)


# Create your deck
my_deck = genanki.Deck(
	2059400110,
	"Sample Deck"
)
my_package = genanki.Package(my_deck)

# Fetch all words and their details in a single request
logger.info("Fetching words with full info...")
LANG = "en"

try:
	resp = requests.get("https://api.linku.la/v1/words?lang=" + LANG)
	logger.info(f"Requested /words endpoint, received status {resp.status_code}")
	resp.raise_for_status()
	words = resp.json()  # List of dicts with keys like "word", "translations", "definition", etc.
	logger.info(f"Got {len(words)} entries.")
except Exception as e:
	logger.error(f"Failed to fetch words: {e}")
	raise


# Loop through entries and add cards
for entry in words:
	word = words[entry]
	wordname = word["word"]

	logger.info(f"Processing entry for word: '{wordname}'")
	if word["usage_category"] not in ENABLED_CATEGORIES:
		logger.info(f"skipping word, its in category {word["usage_category"]}, which isn't enabled.")
		continue

	# Extract answer from translations or definition
	definition = html.escape(word["translations"][LANG]["definition"])
	commentary = html.escape(word["translations"][LANG]["commentary"])
	creator = html.escape(", ".join((word["creator"])))
	coined_era = html.escape(word["coined_era"])
	coined_year =html.escape(word["coined_year"])

	book = html.escape(word["book"])

	usage_data = word["usage"]
	latest_date = max(usage_data.keys())
	latest_usage = usage_data[latest_date]
	usage = html.escape(f"{latest_usage}")
	usage_category = html.escape(f"{word["usage_category"]}")


	# Audio (relative path)
	# audio_html = ""
	# for person in AUDIO_PEOPLE:
	# 	rel_mp3 = AUDIO_SUBDIR / person / f"{wordname}.mp3"
	# 	abs_mp3 = BASE_DIR / rel_mp3
	# 	if abs_mp3.exists():
	# 		audio_html += f"[sound:{rel_mp3.name}]"
	# 		my_package.media_files.append(str(rel_mp3))
	# audio = html.escape(audio_html)

	# Audio: copy to files/audio/word-author.mp3 and reference relatively
	audio_html = ""
	for author in AUDIO_PEOPLE:
		rel_source = AUDIO_SUBDIR / author / f"{wordname}.mp3"
		abs_source = BASE_DIR / rel_source
		if abs_source.exists():
			logger.info(f"adding audio from {abs_source}")
			# define target filename
			target_filename = f"{wordname}-{author}.mp3"
			abs_target = TARGET_AUDIO_DIR / target_filename
			# copy file
			shutil.copy2(abs_source, abs_target)
			# register in package using relative path
			my_package.media_files.append(str(abs_target))
			# add sound tag with correct filename
			audio_html += f"[sound:{target_filename}] "
	audio = html.escape(audio_html)
	logger.info(audio)

	# Glyphs (relative paths)
	pattern = re.compile(rf"^{re.escape(wordname)}-(\d+)\.png$")
	glyphs = sorted(
		(p for p in (BASE_DIR / GLYPH_SUBDIR).iterdir() if pattern.match(p.name)),
		key=lambda p: int(pattern.match(p.name).group(1))
	)
	glyph_html = "".join(f"<img src='{p.name}'/>" for p in glyphs)
	for p in glyphs:
		rel_img = GLYPH_SUBDIR / p.name
		my_package.media_files.append(str(rel_img))
	glyph = html.escape(glyph_html)
	

	# answer = definition + "\n" + commentary
	# print(answer)

	# Create and add note
	note = MyNote(
		model=my_model,
		fields=[wordname, definition, commentary, creator, coined_era, coined_year, book, usage, usage_category, audio, glyph]
	)



	my_deck.add_note(note)
	# logger.debug(f"Added card: {word}")

# Write out the .apkg file
output_file = "toki-pona-deck.apkg"
logger.info(my_package.media_files)
my_package.write_to_file(output_file)
logger.info(f"Done! Written {len(my_deck.notes)} notes to {output_file}")
