from __future__ import annotations

import json
import random
from pathlib import Path

from faker import Faker
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
SAMPLES_DIR = ROOT / "samples"
GROUND_TRUTH_PATH = ROOT / "ground_truth.jsonl"

fake = Faker("en_IN")


def make_pan_number() -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    first_five = "".join(random.choice(letters) for _ in range(5))
    digits = "".join(str(random.randint(0, 9)) for _ in range(4))
    last = random.choice(letters)
    return f"{first_five}{digits}{last}"


def make_dob() -> str:
    year = random.randint(1985, 2000)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{day:02d}/{month:02d}/{year:04d}"


def make_card_record(sample_id: str, quality: str) -> dict:
    record = {
        "sample_id": sample_id,
        "image_file": f"{sample_id}.jpg",
        "image_quality": quality,
        "expected": {
            "full_name": fake.name().upper(),
            "father_name": fake.name().upper(),
            "pan_number": make_pan_number(),
            "date_of_birth": make_dob(),
        },
    }
    return record


def draw_text(draw, text: str, xy: tuple[int, int], font, fill: tuple[int, int, int], anchor: str = "la") -> None:
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)


def create_dummy_card(output_path: Path, expected: dict, quality: str) -> None:
    width, height = 1200, 680
    bg = (250, 247, 242)
    img = Image.new("RGB", (width, height), color=bg)
    draw = ImageDraw.Draw(img)

    # Border and panel
    draw.rounded_rectangle((30, 30, width - 30, height - 30), radius=18, outline=(46, 72, 122), width=4)
    draw.rectangle((70, 90, width - 70, height - 180), outline=(205, 216, 230), width=3)

    try:
        header_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 42)
        body_font = ImageFont.truetype("DejaVuSans.ttf", 30)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except OSError:
        header_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Branding
    draw.text((100, 70), "INCOME TAX DEPARTMENT", font=header_font, fill=(18, 46, 88))
    draw.text((100, 120), "Permanent Account Number Card", font=body_font, fill=(18, 46, 88))

    # PAN card details blocks
    left_x = 110
    label_x = 110
    y = 210
    fields = [
        ("Name", expected["full_name"]),
        ("Father's Name", expected["father_name"]),
        ("PAN", expected["pan_number"]),
        ("Date of Birth", expected["date_of_birth"]),
    ]

    for label, value in fields:
        draw.text((label_x, y), label, font=small_font, fill=(73, 75, 82))
        draw.text((label_x + 240, y), value, font=body_font, fill=(35, 35, 35))
        y += 70

    # PAN number box
    pan_box = (760, 200, 1090, 330)
    draw.rounded_rectangle(pan_box, radius=12, fill=(228, 236, 245), outline=(30, 84, 157), width=3)
    draw.text((790, 260), expected["pan_number"], font=header_font, fill=(17, 85, 165), anchor="la")

    # Watermark
    watermark = "SPECIMEN - NOT A REAL DOCUMENT"
    draw.text((width / 2, height / 2), watermark, font=header_font, fill=(180, 180, 180), anchor="mm", rotate=35)

    # Quality-specific alterations later
    if quality == "rotated":
        img = img.rotate(12, expand=True, fillcolor=bg)
    elif quality == "dark":
        img = Image.eval(img.convert("RGB"), lambda p: p * 0.55)
    elif quality == "blurry":
        img = img.filter(ImageFilter.GaussianBlur(radius=2.5))

    img.save(output_path, format="JPEG", quality=92)


def generate_samples() -> list[dict]:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    qualities = ["clean", "rotated", "dark", "blurry"]

    for idx in range(1, 6):
        sample_id = f"{qualities[(idx - 1) % len(qualities)]}_{idx:02d}"
        quality = sample_id.split("_")[0]
        record = make_card_record(sample_id, quality)
        output_path = SAMPLES_DIR / f"{sample_id}.jpg"
        create_dummy_card(output_path, record["expected"], quality)
        records.append(record)

    # Ensure a named clean/rotated/dark/blurry set exists as the examples requested.
    if not any(p.name.startswith("clean_") for p in SAMPLES_DIR.iterdir()):
        raise RuntimeError("No clean sample files were generated.")

    return records


def write_ground_truth(records: list[dict]) -> None:
    with GROUND_TRUTH_PATH.open("w", encoding="utf-8") as fp:
        for record in records:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    records = generate_samples()
    write_ground_truth(records)
    print(f"Wrote {len(records)} dummy PAN-card samples to {SAMPLES_DIR} and ground truth to {GROUND_TRUTH_PATH}.")


if __name__ == "__main__":
    from PIL import ImageFilter

    main()
