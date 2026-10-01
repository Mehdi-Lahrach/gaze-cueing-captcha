"""Render the four gaze-cueing stimulus videos (gaze left/right x compatible/incompatible).

Mirrors the geometry and timing of index.html (captcha preset):
  blank 500 ms -> direct gaze 1000 ms -> gaze shift -> 250 ms -> target 500 ms (gaze stays) -> blank 500 ms
Output: videos/gaze-<dir>_<compatible|incompatible>.mp4 (1280x720, 60 fps, H.264) + a 3-frame preview PNG.

Requires Pillow and ffmpeg on PATH.
"""
import os, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw

W, H, FPS, SS = 1280, 720, 60, 2            # SS = supersampling factor for antialiasing
G = dict(faceDiameter=260, eyeDiameter=44, eyeOffsetX=50, eyeOffsetY=-35, pupilDiameter=20, pupilShift=14,
         targetEcc=350, targetSize=40, background=(255, 255, 255), ink=(17, 17, 17))
T = dict(blank_pre=500, direct=1000, soa=250, target=500, blank_post=500)   # ms

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")


def draw_frame(gaze="center", target=None):
    s = SS
    img = Image.new("RGB", (W * s, H * s), G["background"])
    d = ImageDraw.Draw(img)
    cx, cy = W * s / 2, H * s / 2
    D = G["faceDiameter"] * s
    r = D / 2
    ink = G["ink"]
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=G["background"], outline=ink, width=4 * s)
    ey = cy + G["eyeOffsetY"] * s
    shift = {"left": -1, "right": 1}.get(gaze, 0) * G["pupilShift"] * s
    for sgn in (-1, 1):
        ex = cx + sgn * G["eyeOffsetX"] * s
        er = G["eyeDiameter"] * s / 2
        d.ellipse([ex - er, ey - er, ex + er, ey + er], fill=G["background"], outline=ink, width=3 * s)
        pr = G["pupilDiameter"] * s / 2
        d.ellipse([ex + shift - pr, ey - pr, ex + shift + pr, ey + pr], fill=ink)
    nr = max(3 * s, D / 52)
    d.ellipse([cx - nr, cy + 0.046 * D - nr, cx + nr, cy + 0.046 * D + nr], fill=ink)
    # mouth: quadratic Bezier from (cx-0.173D, cy+0.21D) via (cx, cy+0.315D) to (cx+0.173D, cy+0.21D)
    p0, p1, p2 = (cx - 0.173 * D, cy + 0.21 * D), (cx, cy + 0.315 * D), (cx + 0.173 * D, cy + 0.21 * D)
    pts = []
    for i in range(41):
        t = i / 40
        pts.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]))
    d.line(pts, fill=ink, width=max(2 * s, int(D / 65)), joint="curve")
    if target in ("left", "right"):
        tx = cx + (-1 if target == "left" else 1) * G["targetEcc"] * s
        ts = G["targetSize"] * s / 2
        d.rectangle([tx - ts, ey - ts, tx + ts, ey + ts], fill=ink)
    return img.resize((W, H), Image.LANCZOS)


def blank():
    return Image.new("RGB", (W, H), G["background"])


def frames_for(gaze, target):
    n = lambda ms: round(ms * FPS / 1000)
    seq = ([("blank", None)] * n(T["blank_pre"]) + [("center", None)] * n(T["direct"]) +
           [(gaze, None)] * n(T["soa"]) + [(gaze, target)] * n(T["target"]) + [("blank", None)] * n(T["blank_post"]))
    return seq


def render(gaze, target, name):
    tmp = tempfile.mkdtemp()
    cache = {}
    for i, (g, t) in enumerate(frames_for(gaze, target)):
        key = (g, t)
        if key not in cache:
            cache[key] = blank() if g == "blank" else draw_frame(g, t)
        cache[key].save(os.path.join(tmp, f"{i:04d}.png"))
    out = os.path.join(OUT, name)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "%04d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print("wrote", out, f"({len(frames_for(gaze, target))} frames, {len(frames_for(gaze, target)) / FPS:.2f} s)")


def preview():
    panels = [("Direct gaze (1000 ms)", draw_frame("center")), ("Gaze shift (250 ms)", draw_frame("left")),
              ("Target, compatible", draw_frame("left", "left"))]
    pw, ph = W // 2, H // 2
    sheet = Image.new("RGB", (pw * 3 + 40, ph + 60), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for i, (label, im) in enumerate(panels):
        x = 10 + i * (pw + 10)
        sheet.paste(im.resize((pw, ph), Image.LANCZOS), (x, 40))
        d.rectangle([x, 40, x + pw - 1, 40 + ph - 1], outline=(180, 180, 180))
        d.text((x, 14), label, fill=(0, 0, 0))
    p = os.path.join(OUT, "trial_phases_preview.png")
    sheet.save(p)
    print("wrote", p)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg not found on PATH")
    for gaze in ("left", "right"):
        for compatible in (True, False):
            target = gaze if compatible else ("right" if gaze == "left" else "left")
            render(gaze, target, f"gaze-{gaze}_{'compatible' if compatible else 'incompatible'}.mp4")
    preview()
