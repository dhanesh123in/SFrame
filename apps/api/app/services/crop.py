from pathlib import Path

from PIL import Image, ImageOps

from app.services.color_adjust import apply_color_adjust
from app.services.image_io import open_image, save_image


def transform_image(
    img: Image.Image,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    rotate: int = 0,
    flip_horizontal: bool = False,
    flip_vertical: bool = False,
) -> Image.Image:
    if flip_horizontal:
        img = ImageOps.mirror(img)
    if flip_vertical:
        img = ImageOps.flip(img)
    if rotate:
        img = img.rotate(-rotate % 360, expand=True)
    box = (x, y, x + width, y + height)
    return img.crop(box)


def apply_crop(
    source: Path,
    dest: Path,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    rotate: int = 0,
    flip_horizontal: bool = False,
    flip_vertical: bool = False,
    output_mime: str = "image/png",
    exposure: float = 0.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
    brightness: float = 1.0,
    temperature: float = 0.0,
    tint: float = 0.0,
) -> tuple[int, int]:
    img = open_image(source)
    img = apply_color_adjust(
        img,
        exposure=exposure,
        contrast=contrast,
        saturation=saturation,
        brightness=brightness,
        temperature=temperature,
        tint=tint,
    )
    img = transform_image(
        img,
        x=x,
        y=y,
        width=width,
        height=height,
        rotate=rotate,
        flip_horizontal=flip_horizontal,
        flip_vertical=flip_vertical,
    )
    save_image(img, dest, mime=output_mime)
    return img.size


def apply_crop_image(
    img: Image.Image,
    dest: Path,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    rotate: int = 0,
    flip_horizontal: bool = False,
    flip_vertical: bool = False,
    output_mime: str = "image/tiff",
    exposure: float = 0.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
    brightness: float = 1.0,
    temperature: float = 0.0,
    tint: float = 0.0,
) -> tuple[int, int]:
    img = apply_color_adjust(
        img,
        exposure=exposure,
        contrast=contrast,
        saturation=saturation,
        brightness=brightness,
        temperature=temperature,
        tint=tint,
    )
    img = transform_image(
        img,
        x=x,
        y=y,
        width=width,
        height=height,
        rotate=rotate,
        flip_horizontal=flip_horizontal,
        flip_vertical=flip_vertical,
    )
    save_image(img, dest, mime=output_mime)
    return img.size
