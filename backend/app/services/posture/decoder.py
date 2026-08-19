"""
Shared image decode helper for the posture tool.

cv2.imdecode cannot decode HEIC/HEIF (OpenCV ships no HEIF decoder due to
licensing). It returns None on such input rather than raising, so every
call site must guard against None -- this module centralizes that guard
and the HEIC fallback so detector.py and annotator.py don't each
reimplement it slightly differently.
"""

import io

import cv2
import numpy as np
import pillow_heif
from PIL import Image, ImageOps


def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    """
    Decode raw image bytes (JPEG/PNG/HEIC/HEIF) into a BGR numpy array,
    as OpenCV expects.

    EXIF orientation is corrected for both the fast (cv2) and HEIC
    fallback paths, so a HEIC captured in iPhone portrait orientation
    (commonly stored rotated with an orientation tag rather than
    physically rotated) does not get fed to MediaPipe sideways --
    that would silently skew every angle-based clinical parameter
    without raising any error.

    Raises
    ------
    ValueError("Failed to decode image")
        If the bytes cannot be decoded by either path.
    """

    np_arr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if image is not None:
        # cv2.imdecode does not apply EXIF orientation. Re-run the bytes
        # through Pillow's EXIF-aware path only if an orientation tag is
        # actually present, to avoid an unnecessary re-decode on the
        # common case.
        try:
            pil_image = Image.open(io.BytesIO(image_bytes))
            exif = pil_image.getexif()
            if exif.get(0x0112, 1) != 1:  # 0x0112 = Orientation tag
                pil_image = ImageOps.exif_transpose(pil_image)
                rgb = np.array(pil_image.convert("RGB"))
                image = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        except Exception:
            # If EXIF inspection fails for any reason, fall back to the
            # already-successfully-decoded image rather than raising --
            # this path is a correction, not the primary decode.
            pass

        return image

    # cv2 couldn't decode it -- try HEIC/HEIF via pillow-heif.
    try:
        heif_file = pillow_heif.read_heif(image_bytes)
        pil_image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
            heif_file.mode,
            heif_file.stride,
        )

        # pillow-heif surfaces orientation via heif_file.info["exif"] if
        # present; apply it the same way as the cv2 path above.
        exif_bytes = heif_file.info.get("exif")
        if exif_bytes:
            try:
                pil_image.info["exif"] = exif_bytes
                exif = pil_image.getexif()
                if exif.get(0x0112, 1) != 1:
                    pil_image = ImageOps.exif_transpose(pil_image)
            except Exception:
                pass

        rgb = np.array(pil_image.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    except Exception:
        raise ValueError("Failed to decode image")
