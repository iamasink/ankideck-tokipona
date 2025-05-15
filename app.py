from pathlib import Path
import shutil
import requests
import genanki
import logging
import html
import re
import json
import hashlib
import os

import argparse



parser = argparse.ArgumentParser("simple_example")
parser.add_argument("-f", "--forceChange", help="Whether to force build even if there are no changed", default=False, required=False, action="store_true")
args = parser.parse_args()

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s.%(msecs)03d %(levelname)s: %(message)s",
	datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


logger.info(args)

FORCE_CHANGE = args.forceChange
FONT_NAME = "sitelenselikiwenmonoasuki"





def get_latest_usage(w):
	usage_data = w.get("usage", {})
	if not usage_data:
		return 0
	latest_date = max(usage_data.keys())
	return usage_data[latest_date]


ids = []

with open('cards/word.html','r', encoding="utf-8") as f:
	wordhtml = f.read(-1)
with open('cards/sitelenpona.html','r', encoding="utf-8") as f:
	sitelenponahtml = f.read(-1)
with open('cards/css.css','r', encoding="utf-8") as f:
	csscontent = f.read(-1)


# update languages file
LANGUAGE_FILE = Path("generated/languages.json")
LANGUAGE_CONFIGFILE = Path("languageconfig.json")
language_data = {}
language_config_data = {}
if LANGUAGE_FILE.exists():
	with LANGUAGE_FILE.open("r", encoding="utf-8") as f:
		language_data = json.load(f)
else:
	logger.fatal("language file doesn't exist")
	exit()

if LANGUAGE_CONFIGFILE.exists():
	with LANGUAGE_CONFIGFILE.open("r", encoding="utf-8") as f:
		language_config_data = json.load(f)
else:
	logger.fatal("language file doesn't exist")
	exit()

resp = requests.get("https://api.linku.la/v1/languages")
logger.info(f"Requested /languages endpoint, received status {resp.status_code}")
resp.raise_for_status()
apilanguages = resp.json() 
logger.info(f"Got {len(apilanguages)} languages.")

for l in apilanguages:
	if not l in language_data:
		language_data[l] = {}
	language_data[l] = apilanguages[l]

# write back to file
LANGUAGE_FILE.write_text(json.dumps(language_data, sort_keys=True, ensure_ascii=False, indent='\t'), encoding="utf-8")
for l in apilanguages:
	if not l in language_config_data:
		language_config_data[l] = {
			"enabled": False,
			"id": -1,
		}
LANGUAGE_CONFIGFILE.write_text(json.dumps(language_config_data, sort_keys=True, ensure_ascii=False, indent='\t'), encoding="utf-8")

# Define your model
my_model = genanki.Model(
	1747075454,
	"Toki Pona Model",
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
		{"name": "Glyph"},
		{"name": "Links"},
		#  {"name": },
		#  {"name": },
		],
		templates=[{
		"name": "Toki Pona Word",
		"qfmt": """
<div class="centered">
<strong>{{Word}}</strong><br>
</div>
		""",
		"afmt": wordhtml
		},
		{
			"name": "Toki Pona sitelen pona",
			"qfmt": """
<div class="centered">
<strong>{{Glyph}}</strong><br>
</div>
		""",
		"afmt": sitelenponahtml
		}
		
		],
	css=csscontent
)



languagecount = len(language_data)


for lang in language_data:
	logger.info("lang: "+ lang)
	langinfo = language_data[lang]
	langconfig = language_config_data[lang]

	logger.info("langinfo: " + str(langinfo))
	enabled = langconfig.get("enabled", False)
	
	if (not enabled):
		logger.info(f"skipping disabled language ({langinfo["name"]["en"]})")
		continue
	
	langid = langconfig["id"]
	logger.info(f"running language '{lang}' ({langinfo["name"]["en"]})")


	# set custom guid with only the Word so it can be overwritten in future!
	class MyNote(genanki.Note):
		@property
		def guid(self):
			return genanki.guid_for("iamasink toki pona " + lang, self.fields[0])


	BASE_DIR = Path(__file__).parent 
	DATA_FILE = BASE_DIR / "generated" /  f"cached_words-{lang}.json"
	AUDIO_SUBDIR = Path("ijo") / "kalama"
	# GLYPH_SUBDIR = Path("ijo") / "sitelensitelen" / "jonathangabel"
	GLYPH_SUBDIR = Path("ijo") / "sitelenpona" / "sitelen-seli-kiwen"
	AUDIO_PEOPLE = ["kalaasi2023", "jlakuse"]

	FILES_DIR = BASE_DIR / "files"
	FILES_DIR.mkdir(parents=True, exist_ok=True)

	ENABLED_CATEGORIES = [
		"core",
		"common",
		"uncommon",
		"obscure",
		# "sandbox" # won't work by default (need to request sandbox api)
	]




	# logger.info(wordhtml)


	deckid = int(1747151651209 + int(langid))
	ids.append(deckid)
	endonym = langinfo["name"].get("endonym", "")
	tokname = langinfo["name"].get("tok", "")

	# Create your deck
	my_deck = genanki.Deck(
		# custom id per lang
		deckid,
		f"toki pona {endonym} ({tokname})"
	)

	my_package = genanki.Package(my_deck)

	# Fetch all words and their details in a single request
	logger.info("Fetching words with full info...")

	try:
		resp = requests.get("https://api.linku.la/v1/words?lang=" + lang)
		logger.info(f"Requested /words endpoint, received status {resp.status_code}")
		resp.raise_for_status()
		words = resp.json()
		logger.info(f"Got {len(words)} entries.")
		def hash_data(data):
			return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
		# Load old data hash
		if DATA_FILE.exists():
			with DATA_FILE.open("r", encoding="utf-8") as f:
				old_data = json.load(f)
			# compare hash to see if changed
			if hash_data(old_data) == hash_data(resp.text):
				if not FORCE_CHANGE:
					logger.info("Data unchanged.")
					continue

		# ensure folder exist
		DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

		# Save new data
		with DATA_FILE.open("w", encoding="utf-8") as f:
			logger.info("saving new data")
			json.dump(resp.text, f, ensure_ascii=False, indent=2)
	except Exception as e:
		logger.error(f"Failed to fetch words: {e}")
		raise


	# # sort words by nimi pu -> nimi ku suli -> nimi ku lili -> no book
	# book_priority = {
	# "nimi pu": 0,
	# "nimi ku suli": 1,
	# "nimi ku lili": 2,
	# }
	# get a list of word-dicts
	word_list = list(words.values())


	# order of word introduction from wasona https://wasona.com
	word_order = [
	"jan", "kute", "nanpa", "kalama", "akesi", "soweli", "waso", "pipi", "kasi", "moku",
	"lukin", "sona", "li", "e", "suli", "lili", "pona", "ike", "wawa", "sona", "suwi",
	"ni", "mi", "sina", "ona", "nimi", "sitelen", "toki", "ma", "tomo", "weka", "pana", "kama",
	"awen", "tawa", "lon", "tan", "utala", "lape", "kalama", "musi", "nasa", "wile", "ken",
	"alasa", "ilo", "lipu", "poki", "supa", "lupa", "len", "open", "pini", "jo", "ijo", "o", "kon",
	"telo", "ko", "kiwen", "seli", "lete", "sewi", "ala", "kepeken", "sama", "ante", "pali",
	"leko", "kulupu", "nasin", "esun", "mani", "moli", "mute", "seme", "anu", "pilin", "jaki", "monsuta",
	"pakala", "tenpo", "sike", "mun", "suno", "sin", "poka", "la", "akesi", "kala", "pan",
	"kili", "soko", "misikeke", "namako", "pi", "selo", "insa", "monsi", "sinpin", "anpa",
	"lawa", "kute", "nena", "uta", "sijelo", "luka", "noka", "palisa", "linja", "wan", "tu",
	"luka", "mute", "ale", "kipisi", "nanpa", "olin", "unpa", "mama", "mije", "meli", "tonsi",
	"en", "kule", "walo", "pimeja", "loje", "jelo", "laso", "kin", "taso", "n", "mu",
	"kijetesantakalu", "pu", "ku", "su", "lanpan"
]

	sorted_words = sorted(
		word_list,
		key=lambda w: (
			# sort by word order list
			word_order.index(w["word"]) if w["word"] in word_order else len(word_order),
			# then sort by usage
			-get_latest_usage(w) if w["word"] not in word_order else 0,
			# then alphabetically
			w.get("word","")
		)
	)

	# logger.info(sorted_words)
	# for w in sorted_words:
		# logger.info(w["word"])

	# Loop through entries and add cards
	wordnum = 0

	for entry in sorted_words:
		wordnum+=1
		word = entry
		wordname = word["word"]

		# logger.info(f"Processing entry for word: '{wordname}'")

		if word["usage_category"] not in ENABLED_CATEGORIES:
			# logger.info("skipping word, its in category" + word["usage_category"] + "which isn't enabled.")
			continue

		# Extract answer from translations or definition
		worddef = word["translations"][lang]["definition"].replace(";","\n")

		if word["deprecated"]:
			definition = html.escape("(This word is deprecated by its creator, and its use is discouraged.)\n" + worddef).replace("\n", "<br/>\n")
		else :
			definition = html.escape(worddef).replace("\n", "<br/>\n")


		commentary = html.escape(word["translations"][lang]["commentary"])
		
		creator = html.escape(", ".join((word["creator"])))
		coined_era = html.escape(word["coined_era"])
		coined_year =html.escape(word["coined_year"])

		origbook = word["book"]
		if (not origbook or origbook == "none"):
			book = "no book"
		else:
			book = html.escape(word["book"])

		usage_data = word["usage"]
		latest_date = max(usage_data.keys())
		latest_usage = get_latest_usage(word)
		usage = html.escape(str(get_latest_usage(word)))
		usage_category = html.escape(word["usage_category"])


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
				# logger.info(f"adding audio from {abs_source}")
				# define target filename
				target_filename = f"tp_{wordname}-{author}.mp3"
				abs_target = FILES_DIR / target_filename
				# copy file
				shutil.copy2(abs_source, abs_target)
				# register in package using relative path
				my_package.media_files.append(str(abs_target))
				# add sound tag with correct filename
				audio_html += f"[sound:{target_filename}] "
		audio = html.escape(audio_html)
		# logger.info(audio)

		# Glyphs (relative paths)
		#
		ligatures = list(word["representations"]["ligatures"])
		# logger.info(ligatures)

		processed = []
		for lig in ligatures:
			# logger.info("processing " + lig)
			# If last char is not a digit, append “-1”
			if (lig and lig[-1].isdigit()):
				# add hyphen
				lig = lig[0:-1] + "-" + lig[-1]
			processed.append(lig)

		# logger.info("final ligatures: %s", processed)

		# glyphfolder = os.path.join(""sitelenpona", FONT_NAME)
		glyphfolder = os.path.join("ijo", "sitelenpona", "sitelen-seli-kiwen")

		glyphs_html = ""
		for p in processed:
			target_filename = f"tp_{p}.png"
			rel_img = os.path.join(glyphfolder, target_filename)
			abs_img_source = os.path.join(BASE_DIR, glyphfolder, p + ".png")
			# first ensure this exists, otherwise just skip it
			if (os.path.isfile(abs_img_source)):
				abs_target = BASE_DIR / "files" / target_filename
				# copy file
				shutil.copy2(abs_img_source, abs_target)
				my_package.media_files.append(str(abs_target) )
				glyphs_html += f"<img src='{target_filename}'/>"
			else:
				logger.warning(f"file {abs_img_source} doesn't exist.. skipping!")

		glyph = glyphs_html

		# logger.info(glyph)



		# add links
		links = ""
		links += f"nimi.li: <a href='https://nimi.li/{word["word"]}'>{word["word"]}</a><br/>"

		for w in word["see_also"]:
			links += f" <a href='https://nimi.li/{w}'>{w}</a>"

		for r in word["resources"]:
			links += f"<br/> {r.replace("_"," ")}: <a href={word["resources"][r]}>{word["word"]}</a>"





		# add tags
		tag_prefix = "TP::"
		mytags = [
			tag_prefix + "book_" + origbook.replace(" ", "-"),
			tag_prefix + "usage_" + usage_category.replace(" ", "-")
		]
		

		# Create and add note
		note = MyNote(
			model=my_model,
			fields=[wordname, definition, commentary, creator, coined_era, coined_year, book, usage, usage_category, audio, glyph, links],
			tags=mytags,
			due=wordnum,
		)



		my_deck.add_note(note)
		logger.debug(f"Added note: {word}")

	# Write out the .apkg file
	output_file = f"toki-pona-deck-{lang}.apkg"
	my_package.write_to_file("generated/" + output_file)
	logger.info(f"Done {lang}! Written {len(my_deck.notes)} notes to {output_file} (id {deckid})")

logger.info("all ids:")
logger.info(ids)

if len(ids) != len(set(ids)):
    logger.error("Duplicates found")