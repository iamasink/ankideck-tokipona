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
FORCE_CHANGE = True
FONT_NAME = "sitelenselikiwenmonoasuki"





# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s.%(msecs)03d %(levelname)s: %(message)s",
	datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)





def get_latest_usage(w):
	usage_data = w.get("usage", {})
	if not usage_data:
		return 0
	latest_date = max(usage_data.keys())
	return usage_data[latest_date]




JUST_FETCH_ENGLISH = False

ids = []


if (JUST_FETCH_ENGLISH):
	LANGUAGES = ["en"]
else:
	LANGUAGES = ["en","eo","ar","ceb_l","cs","cy","da","de","el","es","fi","fr","haw","he","hi","hr","id","io","isv_c","isv_l","it","ith_n","ja","ko","la","lou","lt","mi","nl","nn","nb","pa","pl","pt","ro","ru","sl","sv","tkl","tl_l","tok","tr","uk","ur","yi","zh_hans","ca","wuu","hu","yue","fa","kbt"]
	# LANGUAGES = ["en"]


# get languages from api https://api.linku.la/v1/languages
# add any that don't already exist in LANGUAGES
# Existing list of languages
if (not JUST_FETCH_ENGLISH):
	try:
		resp = requests.get("https://api.linku.la/v1/languages")
		resp.raise_for_status()
		api_languages = resp.json()

		for lang in api_languages:
			if lang not in LANGUAGES:
				LANGUAGES.append(lang)
				logger.info("added language not previously in list: " + lang)

		logger.info(f"Updated LANGUAGES list: {LANGUAGES}")
	except requests.RequestException as e:
		logger.error(f"Error fetching languages: {e}")

totallanguages = len(LANGUAGES)


for lang in LANGUAGES:
	index = LANGUAGES.index(lang)
	percent = (index) / totallanguages * 100
	logger.info(f"running language '{lang}' {index+1}/{totallanguages} ({percent:.1f}%)")


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
		# "sandbox" # won't work by default
	]

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
			{"name": "Glyph"}
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
			"afmt": """
			<div class="centered">
				{{FrontSide}}
				<hr id="answer">
				<div class="warningbanner">
					<span class="warning warningbanner-obscure warning{{Usage Category}}">This word is <span class="bold usagecatobscure">obscure</span>, so most speakers will not understand it.</span>
					<br/>
					<span class="warning warningbanner-sandbox warning{{Usage Category}}">This word is in the <b>sandbox</b>, so almost no speakers will understand it.</span>
				</div>
				{{Audio}}
				<br/>
				{{Glyph}}
				<br/>
				{{Definition}}
				<br/>
				<div class="comment">{{Commentary}}</div>
				<hr>
				<br/>
				Usage: <span class="usagespan usagecat{{Usage Category}}">{{Usage Category}} · {{Usage}}</span>
				<br/>
				Coined by <em>{{Creator}}</em>, {{Coined Era}}, {{Coined Year}}
				<br/>
				Found in <span class="book">{{#Book}}{{Book}}{{/Book}}{{^Book}}No Book{{/Book}}</span>
			</div>
			""",
			},
			{
				"name": "Toki Pona sitelen pona",
				"qfmt": """
			<div class="centered">
				<strong>{{Glyph}}</strong><br>
			</div>
			""",
			"afmt": """
			<div class="centered">
				{{FrontSide}}
				<hr id="answer">
				<div class="warningbanner">
					<span class="warning warningbanner-obscure warning{{Usage Category}}">This word is <span class="bold usagecatobscure">obscure</span>, so most speakers will not understand it.</span>
					<br/>
					<span class="warning warningbanner-sandbox warning{{Usage Category}}">This word is in the <b>sandbox</b>, so almost no speakers will understand it.</span>
				</div>
				{{Word}}
				<br/>
				{{Audio}}
				<br/>
				{{Definition}}
				<br/>
				<div class="comment">{{Commentary}}</div>
				<hr>
				<br/>
				Usage: <span class="usagespan usagecat{{Usage Category}}">{{Usage Category}} · {{Usage}}</span>
				<br/>
				Coined by <em>{{Creator}}</em>, {{Coined Era}}, {{Coined Year}}
				<br/>
				Found in <span class="book">{{#Book}}{{Book}}{{/Book}}{{^Book}}No Book{{/Book}}</span>
			</div>
"""
			}
			
			],
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
	.centered {
		text-align: center;
	}
	"""
	)

	# get the langid from the code 
	# this is to automatically support future languages with unique ids
	# maybe this is a bad way to do it but /shrug
	langupper = lang.replace("_","").replace("-","").replace(":","").upper()
	lang3 = langupper[:4] + langupper[-1:]
	langid = ''.join(str(ord(c) - ord("A")) if c.isalpha() else 'A' for c in lang3)
	deckid = int(1747151651209 + int(langid))
	ids.append(deckid)

	# Create your deck
	my_deck = genanki.Deck(
		# custom id per lang
		deckid,
		"toki pona " + lang
	)

	my_package = genanki.Package(my_deck)

	# Fetch all words and their details in a single request
	logger.info("Fetching words with full info...")

	try:
		resp = requests.get("https://api.linku.la/v1/words?lang=" + lang)
		logger.info(f"Requested /words endpoint, received status {resp.status_code}")
		resp.raise_for_status()
		words = resp.json()  # List of dicts with keys like "word", "translations", "definition", etc.
		logger.info(f"Got {len(words)} entries.")
		def hash_data(data):
			return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
		# Load old data hash
		if DATA_FILE.exists():
			with DATA_FILE.open("r", encoding="utf-8") as f:
				old_data = json.load(f)
			if hash_data(old_data) == hash_data(resp.text):
				if not FORCE_CHANGE:
					logger.info("Data unchanged.")
					continue

		# ensure folder exist
		DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

		# Save new data
		with DATA_FILE.open("w", encoding="utf-8") as f:
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
	for entry in sorted_words:
		word = entry
		wordname = word["word"]

		# logger.info(f"Processing entry for word: '{wordname}'")

		if word["usage_category"] not in ENABLED_CATEGORIES:
			# logger.info("skipping word, its in category" + word["usage_category"] + "which isn't enabled.")
			continue

		# Extract answer from translations or definition
		definition = html.escape(word["translations"][lang]["definition"])
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


		# add tags
		tag_prefix = "TP::"
		mytags = [
			tag_prefix + "book_" + origbook.replace(" ", "-"),
			tag_prefix + "usage_" + usage_category.replace(" ", "-")
		]
		

		# Create and add note
		note = MyNote(
			model=my_model,
			fields=[wordname, definition, commentary, creator, coined_era, coined_year, book, usage, usage_category, audio, glyph],
			tags=mytags,
			due=0,
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