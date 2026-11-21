"""Assemble rendered slide PNGs into MIT_Team.pptx (16:9, one full-bleed image per slide) and MIT_Team.pdf."""
import glob, os, sys
from PIL import Image
from pptx import Presentation
from pptx.util import Emu

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
pngs = sorted(glob.glob(os.path.join(src, "slide_*.png")))
titles = ["Title: PathFinder, Track 03", "The problem", "Solution", "Architecture", "Track 3 final output",
          "Differentiation", "Tools and tech stack", "Demo and local setup", "Brownie points", "Thank you"]
prs = Presentation()
prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
blank = prs.slide_layouts[6]
for i, p in enumerate(pngs):
    s = prs.slides.add_slide(blank)
    pic = s.shapes.add_picture(p, 0, 0, prs.slide_width, prs.slide_height)
    pic.name = titles[i] if i < len(titles) else f"slide {i+1}"
    s.notes_slide.notes_text_frame.text = titles[i] if i < len(titles) else ""
prs.core_properties.title = "MIT_Team: PathFinder, Samsung PRISM XR Hackathon 2026 Track 3"
prs.core_properties.author = "Nadir Hussain, Abdul Haq"
prs.save(os.path.join(out, "MIT_Team.pptx"))
ims = [Image.open(p).convert("RGB") for p in pngs]
ims[0].save(os.path.join(out, "MIT_Team.pdf"), save_all=True, append_images=ims[1:], resolution=144)
print(len(pngs), "slides ->", out)
