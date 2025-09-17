from typing import Tuple

import cv2
import numpy as np


def decode_image(image_bytes: bytes) -> np.ndarray:
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


def encode_jpeg(image: np.ndarray) -> bytes:
    success, buffer = cv2.imencode(".jpg", image)
    if not success:
        raise ValueError("Failed to encode image")
    return buffer.tobytes()

def crop(image: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = bbox
    h_img, w_img = image.shape[:2]
    x0 = int(max(0, round(x)))
    y0 = int(max(0, round(y)))
    x1 = int(min(w_img, x0 + round(w)))
    y1 = int(min(h_img, y0 + round(h)))
    return image[y0:y1, x0:x1]
