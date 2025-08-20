import re

def to_katakana(word):
	CV_RE = re.compile(r"^([ptksmnlwjh]?)([aeiou])")
	VOWEL_MAP = {"a":"ア","i":"イ","u":"ウ","e":"エ","o":"オ"}


# https://sona.pona.la/wiki/sitelen_Ilakana_and_sitelen_Katakana
	CV_MAP = {
	"k": {"a":"カ","i":"キ","u":"ク","e":"ケ","o":"コ"},
	"s": {"a":"サ","i":"シ","u":"ス","e":"セ","o":"ソ"},
	"t": {"a":"タ","i":"?","u":"トゥ","e":"テ","o":"ト"},
	"n": {"a":"ナ","i":"ニ","u":"ヌ","e":"ネ","o":"ノ"},
	"p": {"a":"パ","i":"ピ","u":"プ","e":"ペ","o":"ポ"},
	"m": {"a":"マ","i":"ミ","u":"ム","e":"メ","o":"モ"},
	"j": {"a":"ヤ","i":"?","u":"ユ","e":"イェ","o":"ヨ"},
	"l": {"a":"ラ","i":"リ","u":"ル","e":"レ","o":"ロ"},
	"w": {"a":"ワ","i":"ウィ","u":"?","e":"ウェ","o":"?"},
	}
 

	wordf = word.strip().lower()
	out = []
	i = 0
	Len = len(wordf)
	while i < Len:
		# n
		if wordf[i] == "n":
			out.append("ン")
			i += 1
			continue
			
		
		match = CV_RE.match(wordf[i:])
		if not match:
			i += 1
			continue
			
		consonant, vowel = match.group(1), match.group(2)
		if consonant == "":
			out.append(VOWEL_MAP[vowel])
		else:
			kv = CV_MAP.get(consonant)
			if kv:
				out.append(kv.get(vowel))
			else:
				out.append(VOWEL_MAP[vowel])
		i += len(match.group(0))

	return "".join(out)
