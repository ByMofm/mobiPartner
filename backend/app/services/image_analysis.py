import base64
import json
import logging
from io import BytesIO

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.property import Property, PropertyListing
from app.models.image_analysis import ImageAnalysis

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """Analiza estas fotos de una propiedad inmobiliaria. Evalúa:
1. Estado general (construcción, paredes, pisos, aberturas) - 1 a 5
2. Renovación (nuevo/renovado/original/necesita_reforma)
3. Limpieza y orden - 1 a 5
4. Luz natural - 1 a 5

Responde SOLO en JSON: {"condition": 1-5, "renovation": "nuevo|renovado|original|necesita_reforma", "cleanliness": 1-5, "light": 1-5}"""

CONDITION_LABELS = {
    5: "excelente",
    4: "bueno",
    3: "regular",
    2: "malo",
    1: "malo",
}

RENOVATION_MAP = {
    "nuevo": "nuevo",
    "renovado": "renovado",
    "original": "original",
    "necesita_reforma": "necesita_reforma",
    "necesita reforma": "necesita_reforma",
}


async def _download_image_as_base64(url: str) -> str | None:
    """Download an image and return its base64 encoding."""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return base64.b64encode(resp.content).decode("utf-8")
    except Exception as e:
        logger.debug(f"Failed to download image {url}: {e}")
        return None


def _select_representative_images(image_urls: list[str], max_images: int) -> list[str]:
    """Select representative images: first, middle, and last."""
    if len(image_urls) <= max_images:
        return image_urls

    indices = set()
    indices.add(0)  # first
    indices.add(len(image_urls) - 1)  # last

    # Fill remaining from evenly spaced positions
    remaining = max_images - len(indices)
    step = len(image_urls) / (remaining + 1)
    for i in range(1, remaining + 1):
        indices.add(int(i * step))

    return [image_urls[i] for i in sorted(indices)][:max_images]


async def _call_ollama(images_b64: list[str], model: str) -> dict | None:
    """Send images to Ollama API and parse the JSON response."""
    url = f"{settings.ollama_url}/api/generate"
    payload = {
        "model": model,
        "prompt": ANALYSIS_PROMPT,
        "images": images_b64,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.json()
    except Exception as e:
        logger.error(f"Ollama API error: {e}")
        return None

    response_text = result.get("response", "")

    # Try to extract JSON from response
    try:
        # Find JSON in response (may be wrapped in markdown code blocks)
        json_match = response_text
        if "```" in json_match:
            # Extract from code block
            parts = json_match.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    json_match = part
                    break

        return json.loads(json_match)
    except (json.JSONDecodeError, ValueError):
        logger.warning(f"Could not parse Ollama response as JSON: {response_text[:200]}")
        return None


def _compute_condition_score(analysis: dict) -> int:
    """Convert analysis dict to a 1-100 condition score."""
    condition = analysis.get("condition", 3)
    cleanliness = analysis.get("cleanliness", 3)
    light = analysis.get("light", 3)

    # Clamp values to 1-5
    condition = max(1, min(5, int(condition)))
    cleanliness = max(1, min(5, int(cleanliness)))
    light = max(1, min(5, int(light)))

    # Weighted average: condition 50%, cleanliness 30%, light 20%
    raw = condition * 0.5 + cleanliness * 0.3 + light * 0.2
    # Normalize from 1-5 scale to 1-100
    return max(1, min(100, round((raw - 1) / 4 * 99 + 1)))


async def analyze_property_images(db: Session, property_id: int, image_urls: list[str]) -> dict | None:
    """Analyze images for a single property using Ollama vision model."""
    selected = _select_representative_images(image_urls, settings.image_analysis_max_images)

    # Download images
    images_b64 = []
    for url in selected:
        b64 = await _download_image_as_base64(url)
        if b64:
            images_b64.append(b64)

    if len(images_b64) < 2:
        logger.debug(f"Property {property_id}: only {len(images_b64)} images downloadable, skipping")
        return None

    # Call Ollama
    analysis = await _call_ollama(images_b64, settings.image_analysis_model)
    if not analysis:
        return None

    condition_score = _compute_condition_score(analysis)
    condition_val = max(1, min(5, int(analysis.get("condition", 3))))
    condition_label = CONDITION_LABELS.get(condition_val, "regular")
    renovation = RENOVATION_MAP.get(analysis.get("renovation", ""), "original")

    # Save to DB
    existing = db.query(ImageAnalysis).filter(ImageAnalysis.property_id == property_id).first()
    if existing:
        existing.condition_score = condition_score
        existing.condition_label = condition_label
        existing.renovation_state = renovation
        existing.natural_light = max(1, min(5, int(analysis.get("light", 3))))
        existing.cleanliness = max(1, min(5, int(analysis.get("cleanliness", 3))))
        existing.raw_analysis = analysis
        existing.images_analyzed = len(images_b64)
    else:
        db.add(ImageAnalysis(
            property_id=property_id,
            condition_score=condition_score,
            condition_label=condition_label,
            renovation_state=renovation,
            natural_light=max(1, min(5, int(analysis.get("light", 3)))),
            cleanliness=max(1, min(5, int(analysis.get("cleanliness", 3)))),
            raw_analysis=analysis,
            images_analyzed=len(images_b64),
        ))

    # Update property
    prop = db.query(Property).filter(Property.id == property_id).first()
    if prop:
        prop.condition_score = condition_score

    return {
        "property_id": property_id,
        "condition_score": condition_score,
        "condition_label": condition_label,
        "renovation_state": renovation,
        "images_analyzed": len(images_b64),
    }


async def batch_analyze(db: Session, max_properties: int | None = None) -> int:
    """Analyze images for properties that haven't been analyzed yet.

    Only processes properties with at least 2 images.
    """
    if max_properties is None:
        max_properties = settings.image_analysis_max_per_run

    # Find properties with images but no analysis
    analyzed_ids = db.query(ImageAnalysis.property_id).subquery()

    candidates = (
        db.query(Property.id, PropertyListing.image_urls)
        .join(PropertyListing, PropertyListing.property_id == Property.id)
        .filter(
            Property.is_active == True,
            Property.id.notin_(analyzed_ids),
            func.array_length(PropertyListing.image_urls, 1) >= 2,
        )
        .limit(max_properties)
        .all()
    )

    # Deduplicate by property_id, merge image URLs
    property_images: dict[int, list[str]] = {}
    for pid, imgs in candidates:
        if imgs:
            property_images.setdefault(pid, []).extend(imgs)

    # Deduplicate image URLs per property
    for pid in property_images:
        property_images[pid] = list(dict.fromkeys(property_images[pid]))

    analyzed = 0
    for pid, imgs in property_images.items():
        if len(imgs) < 2:
            continue
        result = await analyze_property_images(db, pid, imgs)
        if result:
            analyzed += 1
            if analyzed % 10 == 0:
                db.flush()
                logger.info(f"Analyzed {analyzed}/{len(property_images)} properties")

    db.commit()
    logger.info(f"Image analysis complete: {analyzed} properties analyzed")
    return analyzed
