# you must have fontforge

# choose a font from ijo/nasinsitelen
# remember:
# > WARNING: You CANNOT directly use the output. It MUST be hand-processed.
# > Different fonts use different variant numbers.
# > You must also get permission to commit any dumped font data, respecting the license.
# fonts that use different numbers won't work correctly... but we can trust the one used on linku.la right?
fontname = "sitelenselikiwenmonoasuki"

import os
import subprocess

def run_dump(font_path: str, out_dir: str):
	ffpython = os.path.join("C:\\", "Program Files (x86)", "FontForgeBuilds", "bin", "ffpython.exe")
	script = os.path.join(".", "scripts", "dump_font.py")


	# ensure output directory exists
	os.makedirs(out_dir, exist_ok=True)

	args = [
		ffpython,
		script,
		"--font", font_path,
		"--directory", out_dir,
	]
	subprocess.run(args, check=True)    

if __name__ == "__main__":
	font_path = os.path.join("ijo", "nasinsitelen", f"{fontname}.ttf")
	out_dir   = os.path.join("sitelenpona", fontname)
	run_dump(font_path, out_dir)
