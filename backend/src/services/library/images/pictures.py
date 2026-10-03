import io
from dataclasses import dataclass

from PIL import Image, ImageOps, ImageStat

FULL_WIDTH = 1280
CARD_SIZE = (640, 480)
QUALITY = 82
MIME_TYPE = "image/webp"
BORDER_THRESHOLD = 24
MIN_SPREAD = 12.0


class UnusableImageError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Prepared:
    image: bytes
    card: bytes
    width: int
    height: int


def load(data: bytes) -> Image.Image:
    try:
        with Image.open(io.BytesIO(data)) as opened:
            opened.load()
            picture = ImageOps.exif_transpose(opened)
    except (OSError, SyntaxError, ValueError) as e:
        raise UnusableImageError(str(e)) from e
    if picture.mode != "RGB":
        picture = picture.convert("RGB")
    return picture


def trim_dark_border(picture: Image.Image) -> Image.Image:
    gray = picture.convert("L").point(lambda v: 255 if v > BORDER_THRESHOLD else 0)
    box = gray.getbbox()
    if box is None:
        return picture
    left, top, right, bottom = box
    if (right - left) < picture.width * 0.5 or (bottom - top) < picture.height * 0.5:
        return picture
    return picture.crop(box)


def is_flat(picture: Image.Image) -> bool:
    spread = ImageStat.Stat(picture.convert("L").resize((64, 48))).stddev[0]
    return spread < MIN_SPREAD


def encode(picture: Image.Image) -> bytes:
    buffer = io.BytesIO()
    picture.save(buffer, format="WEBP", quality=QUALITY, method=6)
    return buffer.getvalue()


def jpeg_preview(data: bytes, width: int = CARD_SIZE[0]) -> bytes:
    picture = trim_dark_border(load(data))
    picture.thumbnail((width, width))
    buffer = io.BytesIO()
    picture.save(buffer, format="JPEG", quality=80)
    return buffer.getvalue()


def prepare(data: bytes) -> Prepared:
    picture = trim_dark_border(load(data))
    if is_flat(picture):
        message = "flat image"
        raise UnusableImageError(message)
    full = picture.copy()
    if full.width > FULL_WIDTH:
        full = full.resize(
            (FULL_WIDTH, round(full.height * FULL_WIDTH / full.width)),
            Image.Resampling.LANCZOS,
        )
    card = ImageOps.fit(picture, CARD_SIZE, Image.Resampling.LANCZOS)
    return Prepared(
        image=encode(full), card=encode(card), width=full.width, height=full.height
    )
