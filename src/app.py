from pathlib import Path
import shutil
import time
import requests
import genanki
import logging
import html
import re
import json
import hashlib
import os
import random

import argparse
from transliterate import to_katakana

# args
parser = argparse.ArgumentParser("simple_example")
parser.add_argument("-f", "--forceChange", help="force build even if there are no changes", default=False, required=False, action="store_true")
parser.add_argument("-l", "--lang", help="language to run", default=None, required=False, metavar="LANG", type=str)
parser.add_argument("-d", "--requestDelay", help="delay between lang requests", default=1, required=False, metavar="SECONDS", type=float)
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

MODEL_ID = 1747075454
DECK_ID_BASE = 1747151651209

REQUEST_DELAY = args.requestDelay or 2

BASE_DIR = Path(__file__).parent.parent




def get_latest_usage(w):
	usage_data = w.get("usage", {})
	if not usage_data:
		return 0
	latest_date = max(usage_data.keys())
	return usage_data[latest_date]


ids = []

# update languages file
LANGUAGE_FILE = BASE_DIR / "generated" / "languages.json"
LANGUAGE_CONFIGFILE = BASE_DIR / "languageconfig.json"
language_data = {}
language_config_data = {}
if LANGUAGE_FILE.exists():
	with LANGUAGE_FILE.open("r", encoding="utf-8") as f:
		language_data = json.load(f)
else:
	logger.warning("language file doesn't exist")

if LANGUAGE_CONFIGFILE.exists():
	with LANGUAGE_CONFIGFILE.open("r", encoding="utf-8") as f:
		language_config_data = json.load(f)
else:
	logger.fatal("language config file doesn't exist")
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
		# create a random number id
		id = random.randint(100,999)
		language_config_data[l] = {
			"enabled": False,
			"id": id,
		}
LANGUAGE_CONFIGFILE.write_text(json.dumps(language_config_data, sort_keys=True, ensure_ascii=False, indent='\t'), encoding="utf-8")

CARD_DIR = BASE_DIR / "cards"
WORD_A_HTML = CARD_DIR / "word" / "a.html"
WORD_Q_HTML = CARD_DIR / "word" / "q.html"
SITELEN_A_HTML = CARD_DIR / "sitelenpona" / "a.html"
SITELEN_Q_HTML = CARD_DIR / "sitelenpona" / "q.html"
CSS_FILE = CARD_DIR / "stylesheet.css"

with WORD_A_HTML.open("r", encoding="utf-8") as f: word_a_html = f.read()
with WORD_Q_HTML.open("r", encoding="utf-8") as f: word_q_html = f.read()
with SITELEN_A_HTML.open("r", encoding="utf-8") as f: sitelenpona_a_html = f.read()
with SITELEN_Q_HTML.open("r", encoding="utf-8") as f: sitelenpona_q_html = f.read()
with CSS_FILE.open("r", encoding="utf-8") as f: csscontent = f.read()


my_model = genanki.Model(
	MODEL_ID, 
	"Toki Pona Model",
	fields=[
		{"name": "sort_id"}, # deck sort order
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
		{"name": "Glyph Etymology"},
		{"name": "Links"},
		{"name": "WordAlt"},
		#  {"name": },
		#  {"name": },
		],
		templates=[
		{
			"name": "Toki Pona Word",
			"qfmt": word_q_html,
			"afmt": word_a_html
		},
		{
			"name": "Toki Pona sitelen pona",
			"qfmt": sitelenpona_q_html,
			"afmt": sitelenpona_a_html
		}],
		css=csscontent,
		sort_field_index=0

)

# supported wasona langs https://wasona.com/translate/
WASONA_LANGS = ["en", "de", "pl", "ru", "he"]
# order of word introduction from wasona https://wasona.com
WASONA_WORDS = {
	# "1":["mi", "ken", "jan", "kute", "nanpa", "kalama", "akesi",],
	"3":["soweli", "waso", "pipi", "kasi", "moku", "lukin", "sona",],
	"4":["suli", "lili", "pona", "ike", "wawa", "sona", "suwi",],
	"5":["lukin", "moku", "sona", "suli", "pona", "waso",],
	"6":["ni", "mi", "sina", "ona",],
	"7":["nimi", "jan", "sitelen", "toki", "ma", "tomo",],
	"8":["weka", "pana", "kama", "awen", "tawa", "lon", "tan",],
	"9":["utala", "lape", "kalama", "musi", "nasa",
	"kama", "awen",
	"wile", "ken", "alasa",],
	"11":["ilo", "lipu", "poki", "supa", "lupa", "len", "open", "pini", "jo",],
	"12": ["o",],
	"13":["kon", "telo", "ko", "kiwen", "seli", "lete", "sewi",],
	"14": ["ala",],
	"15":["kepeken", "sama", "ante", "pali", "leko", "tawa", "lon", "tan", "kepeken", "sama",],
	"16": ["kulupu", "nasin", "esun", "mani", "moli", "mute",],
	"17":["musi", "seme", "anu",],
	"18":["pilin", "jaki", "monsuta", "pakala", "toki", "pona", "sona", "wawa", "lon", "pipi", "a", "ken",],
	"20":["tenpo", "sike", "mun", "suno", "sin", "poka", "la",],
	"21":["akesi", "kala", "pan", "kili", "soko", "misikeke", "namako",],
	"22":["pi",],
	"23":["selo", "insa", "monsi", "sinpin", "anpa",],
	"24":["lawa", "kute", "nena", "uta", "sijelo", "luka", "noka", "palisa", "linja",],
	"25":["wan", "tu", "luka", "mute", "ale", "kipisi",],
	"26":[ "olin",  "unpa",  "mama",  "mije",  "meli",  "tonsi",  "en",],
	"27":["kule", "walo", "pimeja", "loje", "jelo", "laso", "kin",],
	"28":["taso", "n", "mu", "kijetesantakalu", "pu", "ku",],
}

	# order of word introduction from wasona https://wasona.com
	# word_order =  [
	# "jan", "kute", "nanpa", "kalama", "akesi", 
 	# "soweli", "waso", "pipi", "kasi", "moku",
	# "lukin", "sona", "li", "e", "suli", "lili", "pona", "ike", "wawa", "suwi",
	# "ni", "mi", "sina", "ona", "nimi", "sitelen", "toki", "ma", "tomo", "weka", "pana", "kama",
	# "awen", "tawa", "lon", "tan", "utala", "lape", "musi", "nasa", "wile", "ken",
	# "alasa", "ilo", "lipu", "poki", "supa", "lupa", "len", "open", "pini", "jo", "ijo", "o", "kon",
	# "telo", "ko", "kiwen", "seli", "lete", "sewi", "ala", "kepeken", "sama", "ante", "pali",
	# "leko", "kulupu", "nasin", "esun", "mani", "moli", "mute", "seme", "anu", "pilin", "jaki", "monsuta",
	# "pakala", "a", "tenpo", "sike", "mun", "suno", "sin", "poka", "la", "kala", "pan",
	# "kili", "soko", "misikeke", "namako", "pi", "selo", "insa", "monsi", "sinpin", "anpa",
	# "lawa", "nena", "uta", "sijelo", "luka", "noka", "palisa", "linja", "wan", "tu",
	# "ale", "kipisi", "olin", "unpa", "mama", "mije", "meli", "tonsi",
	# "en", "kule", "walo", "pimeja", "loje", "jelo", "laso", "kin", "taso", "n", "mu",
	# "kijetesantakalu", "pu", "ku", "su", "lanpan"
	# ]

CATEGORIES = {
	"particle": {"a", "ala", "anu", "e", "en", "la", "li", "nanpa", "o", "pi", "seme", "taso", "kin","te","to"},
	"preposition": {"kepeken","lon","sama","tan","tawa"},
	"interjection": {"a","n","kulijo","wa"},
	"number": {"ala","wan","tu","san","po","luka","mute"},
	"pronoun": {"mi","sina","ona"},
	"preverb": {"wile","ken","kama","awen","alasa",		"sona","lukin"}
}


WORD_ORDER = []
for lesson in sorted(WASONA_WORDS, key=int):
	for w in WASONA_WORDS[lesson]:
		if w not in WORD_ORDER:
			WORD_ORDER.append(w)
    
    

languagecount = len(language_data)


for lang in language_data:
	if args.lang and lang != args.lang:
		logger.info(f"skipping language {lang}")
		continue

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


	DATA_FILE = BASE_DIR / "generated" /  f"cached_words-{lang}.json"
 

	AUDIO_SUBDIR = BASE_DIR / "ijo" / "kalama"
	GLYPH_SUBDIR = BASE_DIR / "ijo" / "sitelenpona" / "sitelen-seli-kiwen"
	AUDIO_PEOPLE = ["kalaasi2023", "jlakuse"]

	FILES_DIR = BASE_DIR / "files"
	# ensure dir exists
	FILES_DIR.mkdir(parents=True, exist_ok=True)

	ENABLED_CATEGORIES = [
		"core",
		"common",
		"uncommon",
		# "obscure",
		# "sandbox" # won't work by default (need to request sandbox api)
	]




	# logger.info(wordhtml)


	deckid = int(DECK_ID_BASE + int(langid))
	ids.append(deckid)
	endonym = langinfo["name"].get("endonym", "")
	tokname = langinfo["name"].get("tok", "")


	my_deck = genanki.Deck(
		# custom id per lang
		deckid,
		f"toki pona ({endonym})"
	)

	my_package = genanki.Package(my_deck)

	logger.info("Fetching words with full info...")

	try:
		## wait a bit between requests :)
		time.sleep(REQUEST_DELAY)
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
			hashed_old = hash_data(old_data)
			hashed_new = hash_data(words)
   
			if hashed_old == hashed_new:
				if not FORCE_CHANGE:
					logger.info("Data unchanged.")
					#continue

		# ensure folder exist
		DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

		# Save new data
		with DATA_FILE.open("w", encoding="utf-8") as f:
			logger.info("saving new data")
			json.dump(words, f, ensure_ascii=False, indent=2)
	except Exception as e:
		logger.error(f"Failed to fetch words: {e}")
		raise


	# get a list of word-dicts
	word_list = list(words.values())





	sorted_words = sorted(
		word_list,
		key=lambda w: (
			# sort by word order list
			WORD_ORDER.index(w["word"]) if w["word"] in WORD_ORDER else len(WORD_ORDER),
			# then sort by usage
			-get_latest_usage(w) if w["word"] not in WORD_ORDER else 0,
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
  
		wordid = html.escape(str(wordnum))
  
  
		if lang == "ja":
			wordaltscript = to_katakana(wordname)
		else:
			wordaltscript = ""

		# logger.info(f"Processing entry for word: '{wordname}'")

		if word["usage_category"] not in ENABLED_CATEGORIES:
			# logger.info("skipping word, its in category" + word["usage_category"] + "which isn't enabled.")
			continue

		# set definition and split newlines by ;
		worddef = word["translations"][lang]["definition"].replace("; ","\n").replace(";","\n")

		if word["deprecated"]:
			# add dewprecated warning
			# replace newline chars with <br/> + newline
			definition = html.escape("(This word is deprecated by its creator, and its use is discouraged.)\n" + worddef).replace("\n", "<br/>\n")
		else :
			# replace newline chars with <br/> + newline
			definition = html.escape(worddef).replace("\n", "<br/>\n")


		commentary = html.escape(word["translations"][lang]["commentary"])
		glyph_etymology = html.escape(word["translations"][lang]["sp_etymology"])
		
		creator = html.escape(", ".join((word["creator"])))
		coined_era = html.escape(word["coined_era"])
		coined_year = html.escape(word["coined_year"])
  

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

		# Audio: copy to custom filename so the imported file will have this filename
		# (to prevent conflicts)
		audio_html = ""
		for author in AUDIO_PEOPLE:
			src_audio = AUDIO_SUBDIR / author / f"{wordname}.mp3"
			if src_audio.exists():
				# logger.info(f"adding audio from {abs_source}")
				# define target filename
				target_filename = f"tp_{wordname}-{author}.mp3"
				target_audio = FILES_DIR / target_filename
				# copy file
				
				# check if it already exists
				if not target_audio.exists():
					shutil.copy2(src_audio, target_audio)
				else:
					# logger.info(f"{target_filename} already exists, skipping copy!")
					pass
    
				# register in package using relative path
				my_package.media_files.append(str(target_audio))
				# add sound tag with correct filename
				audio_html += f"[sound:{target_filename}] "
		audio = html.escape(audio_html)
		# logger.info(audio)



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

		glyphs_dict = {}
		for lig in processed:
			target_glyph_filename = f"tp_{lig}.png"
			src_glyph = GLYPH_SUBDIR / f"{lig}.png"
			# first ensure this exists, otherwise just skip it
			if (os.path.isfile(src_glyph)):
				target_glyph = BASE_DIR / "files" / target_glyph_filename
				# copy file
				# shutil.copy2(abs_img_source, abs_target)
    
    			# check if it already exists
				if not target_glyph.exists():
					shutil.copy2(src_glyph, target_glyph)
				else:
					# logger.info(f"{target_filename} already exists, skipping copy!")
					pass
    
				my_package.media_files.append(str(target_glyph) )
				glyphs_dict[target_glyph_filename] = True
    
				# glyphs_dict.append(f"<img src='{target_glyph_filename}'/>")
			else:
				logger.warning(f"file {src_glyph} doesn't exist.. skipping!")


		# join using dict
		glyph = "".join(f"<img src='{fn}'/>" for fn in glyphs_dict.keys())

		logger.info(glyph)



		# add links
		links = ""
		links += f"nimi.li: <a href='https://nimi.li/{wordname}'>{wordname}</a><br/>"

		for w in word["see_also"]:
			links += f" <a href='https://nimi.li/{w}'>{w}</a>"

		for r in word["resources"]:
			# logger.info(r)
			if r == "lipamanka_semantic":
				continue # skip lipamanka as its on nimi.li
			links += f"<br/> {r.replace("_"," ")}: <a href={word["resources"][r]}>{wordname}</a>"




		# add tags
		tag_prefix = "TP::"
		mytags = [
			tag_prefix + "book::" + origbook.replace(" ", "-"),
			tag_prefix + "usage::" + usage_category.replace(" ", "-"),
			tag_prefix + "era::" + coined_era.replace(" ", "-")
		]


		for cat, words in CATEGORIES.items():
			if wordname in words:
				mytags.append(f"TP::category::{cat}")
  
		word_lessons = []
		lesson_tag = None
		for lesson_num, lesson_words in WASONA_WORDS.items():
			if wordname in lesson_words:
				lesson_tag = f"{tag_prefix}lesson::{str(lesson_num).zfill(2)}"
				mytags.append(lesson_tag)
				word_lessons.append(lesson_num)

		wasona_lang = lang if lang in WASONA_LANGS else "en"
		if len(word_lessons) > 0:
			if len(word_lessons) > 1:
				links += "<br/>wasona lessons: "
			else:
				links += "<br/>wasona lesson: "

			lesson_links = "<br/>\n".join(f"<a href='https://wasona.com/{wasona_lang}/{str(ln).zfill(2)}'>lesson {ln}</a>" for ln in word_lessons)
			links += lesson_links

		# Create and add note
		note = MyNote(
			model=my_model,
			fields=[wordid, wordname, definition, commentary, creator, coined_era, coined_year, book, usage, usage_category, audio, glyph, glyph_etymology, links, wordaltscript],
			tags=mytags,
			due=wordnum,
		)



		my_deck.add_note(note)
		logger.debug(f"Added note: {word}")

	# Write out the .apkg file
	output_file = BASE_DIR / "generated" / f"toki-pona-deck-{lang}.apkg"
	my_package.write_to_file(output_file)
	logger.info(f"Done {lang}! Written {len(my_deck.notes)} notes to {output_file} (id {deckid})")
