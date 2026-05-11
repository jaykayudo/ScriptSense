from __future__ import annotations

import cv2
import numpy as np
from loguru import logger
from PIL import Image as PILImage
from ultralytics import YOLO

from app.core.config import SETTINGS

_yolo_model: YOLO | None = None


def _get_model() -> YOLO:
    global _yolo_model
    if _yolo_model is None:
        logger.info("Loading YOLO model | path={}", SETTINGS.yolo_model_path)
        _yolo_model = YOLO(SETTINGS.yolo_model_path)
        logger.info("YOLO model loaded")
    return _yolo_model


def get_crops_for_image(image_source: str | np.ndarray) -> list[PILImage.Image]:
    """
    Run YOLO line detection on a single image and return line crops sorted top-to-bottom.

    Args:
        image_source: file path string OR a numpy array (grayscale 2-D or BGR/RGB 3-D).

    Returns:
        List of RGB PIL Image crops. Falls back to the whole image if no lines detected.
    """
    # Resolve to a 3-channel BGR array first — YOLO requires 3 channels.
    if isinstance(image_source, str):
        img = cv2.imread(image_source)
    elif image_source.ndim == 2:
        img = cv2.cvtColor(image_source, cv2.COLOR_GRAY2BGR)
    else:
        img = image_source

    logger.debug("YOLO predict | input_shape={}", img.shape)
    yolo = _get_model()
    results = yolo.predict(source=img, conf=0.25, verbose=False)

    boxes = results[0].boxes.xyxy.cpu().numpy()
    if len(boxes) == 0:
        logger.warning("No lines detected — falling back to full image as single crop")
        return [PILImage.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))]

    boxes = boxes[boxes[:, 1].argsort()]
    logger.debug("Lines detected | count={}", len(boxes))
    crops = []
    for x1, y1, x2, y2 in boxes:
        crop = img[int(y1):int(y2), int(x1):int(x2)]
        crops.append(PILImage.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)))
    return crops


def get_crops_for_images(
    image_sources: list[str | np.ndarray],
) -> list[list[PILImage.Image]]:
    """Run line detection on multiple images. Returns one crop list per image."""
    return [get_crops_for_image(src) for src in image_sources]


# Keep original signature for backward compatibility
def get_crops_for_ocr(
    image_path: str, model_path: str | None = None
) -> list[PILImage.Image]:
    if model_path:
        m = YOLO(model_path)
        results = m.predict(source=image_path, conf=0.25, verbose=False)
        img = cv2.imread(image_path)
        boxes = results[0].boxes.xyxy.cpu().numpy()
        if len(boxes) == 0:
            return [PILImage.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))]
        boxes = boxes[boxes[:, 1].argsort()]
        return [
            PILImage.fromarray(
                cv2.cvtColor(
                    img[int(y1):int(y2), int(x1):int(x2)], cv2.COLOR_BGR2RGB
                )
            )
            for x1, y1, x2, y2 in boxes
        ]
    return get_crops_for_image(image_path)
