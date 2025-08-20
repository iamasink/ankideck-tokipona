# choose a font from ijo/nasinsitelen
fontname = "sitelenselikiwenmonoasuki"

import os
import subprocess

if __name__ == "__main__":
	font_name = "sitelenselikiwenmonoasuki"
	args = [
		"python",
		"scripts/svg2png.py",
		"--directory", "./sitelenpona/sitelenselikiwenmonoasuki",
	]
	subprocess.run(args, check=True)
