from PIL import Image as PILImage
import numpy as np
import cv2
import piexif
from loguru import logger


def order_points(pts):
    """
    Given 4 corner points in any order, return them sorted as:
    [top-left, top-right, bottom-right, bottom-left].

    OpenCV needs to know which corner maps to which destination point.

    Args:
        pts (np.ndarray): Array of shape (4, 2) — four (x, y) coordinates.

    Returns:
        np.ndarray: The same 4 points reordered as [TL, TR, BR, BL].
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    rect[0] = pts[np.argmin(s)]      # top-left
    rect[2] = pts[np.argmax(s)]      # bottom-right
    rect[1] = pts[np.argmin(diff)]   # top-right
    rect[3] = pts[np.argmax(diff)]   # bottom-left
    return rect

def load_with_exif_rotation(path):
    """
    Load an image from disk and apply any rotation encoded in its EXIF (photo) metadata.

    Args:
        path (str): Path to the image file.

    Returns:
        np.ndarray: BGR image array (OpenCV's native format), correctly rotated.
    """
    logger.debug("Loading image | path={}", path)
    pil_img = PILImage.open(path)
    # Try to read the orientation tag from EXIF data
    try:
        exif_data = piexif.load(pil_img.info.get("exif", b""))
        orientation = exif_data["0th"].get(piexif.ImageIFD.Orientation, 1)
    except:
        orientation = 1 # Default: no rotation needed
    # EXIF orientation codes and their corresponding rotation angles
    rotation_map = {3: 180, 6: -90, 8: 90}
    if orientation in rotation_map:
        angle = rotation_map[orientation]
        logger.debug("Applying EXIF rotation | angle={}°", angle)
        pil_img = pil_img.rotate(angle, expand=True)
    else:
        logger.debug("No EXIF rotation needed | orientation={}", orientation)
    # Convert from Pillow (RGB) to OpenCV (BGR) format
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

# un-skew the document
def perspective_correct(image):
    """
    Detect the document in the image and apply a perspective transform to make
    it appear as if photographed as a flat rectangular scan.

    HOW IT WORKS:
        1. Convert to grayscale and detect edges (Canny edge detector)
        2. Find contours (closed shapes) in the edge map
        3. Look for the largest 4-sided contour — that's likely the document
        4. Compute a perspective transform from those 4 corners to a rectangle
        5. Warp the image using that transform

    Args:
        image (np.ndarray): BGR image (as loaded by OpenCV).

    Returns:
        np.ndarray: Perspective-corrected BGR image, or the original if no
                    document contour was found.
    """
    orig = image.copy()
    #Grayscale + blur to reduce noise before edge detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # Canny edge detector: finds sharp intensity changes (i.e. document borders)
    # The two numbers (75, 200) are the lower and upper thresholds
    edged = cv2.Canny(blurred, 75, 200)
    #Find all contours, keep the 5 largest by area
    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    # Among those contours, find the first one that's roughly quadrilateral
    doc_contour = None
    for c in contours:
        # approxPolyDP simplifies the contour to fewer points
        # 0.02 * perimeter is the tolerance for how much the shape can deviate
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:  # A page has 4 corners
            doc_contour = approx
            break

    if doc_contour is None:
        logger.warning("No document contour found — skipping perspective correction")
        return image  # Return the image unchanged

    # Order the 4 corners consistently (TL, TR, BR, BL)
    pts = order_points(doc_contour.reshape(4, 2))
    tl, tr, br, bl = pts

    # compute output rectangle dimensions
    widthA = np.linalg.norm(br - bl)   # Bottom edge width
    widthB = np.linalg.norm(tr - tl)   # Top edge width
    heightA = np.linalg.norm(tr - br)  # Right edge height
    heightB = np.linalg.norm(tl - bl)  # Left edge height
    maxW = int(max(widthA, widthB))
    maxH = int(max(heightA, heightB))

    # Define where the 4 corners should map to in the output (a flat rectangle)
    dst = np.array([
        [0, 0],
        [maxW - 1, 0],
        [maxW - 1, maxH - 1],
        [0, maxH - 1]
    ], dtype="float32")

    # Compute and apply the perspective transform
    logger.debug("Perspective correction applied | output={}x{}", maxW, maxH)
    M = cv2.getPerspectiveTransform(pts, dst)
    warped = cv2.warpPerspective(orig, M, (maxW, maxH))
    return warped


def process_document(image_path: str) -> np.ndarray:
    """
    Load and pre-process a document photo to produce a clean, binarized image
    that looks like a high-quality scan.

    WHY PRE-PROCESS?
    Raw photos have uneven lighting, perspective distortion, and colour noise.
    OCR models work much better on clean, high-contrast black-and-white images.

    Steps applied:
        1. Load with EXIF rotation correction
        2. Perspective correction (un-skew the document)
        3. Convert to grayscale
        4. Normalize uneven lighting (e.g. shadows from phone flash)
        5. Adaptive binarization (convert to pure black and white)
        6. Morphological cleanup (remove small noise specks)

    Args:
        image_path (str): Path to the input image.

    Returns:
        np.ndarray: A cleaned, binarized (black & white) image ready for OCR.
    """
    logger.debug("process_document start | path={}", image_path)
    # Fix rotation and perspective
    image = load_with_exif_rotation(image_path)
    image = perspective_correct(image)

    # the OCR model doesn't need colour information
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    #  Normalize lighting
    # GaussianBlur with a large kernel (51x51) creates a smooth "background brightness" map.
    # Dividing the image by this map removes lighting gradients (e.g. one side darker than other).
    blur = cv2.GaussianBlur(gray, (51, 51), 0)
    norm = cv2.divide(gray, blur, scale=255)

   # Step 5: Adaptive thresholding — converts grayscale to pure black & white.
    # Unlike simple thresholding, ADAPTIVE_THRESH_GAUSSIAN_C computes a local
    # threshold for each pixel based on its neighbourhood. This handles cases
    # where different parts of the image have different brightness levels.
    binary = cv2.adaptiveThreshold(
        norm, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        51,   # Block size: size of the neighbourhood area (must be odd)
        15    # C: a constant subtracted from the mean to fine-tune the threshold
    )

    # Step 6: Morphological opening — erodes then dilates to remove tiny noise specks.
    # A small 2x2 kernel means only very small artefacts are removed.
    kernel = np.ones((2, 2), np.uint8)
    clean = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    logger.debug("process_document complete | output_shape={}", clean.shape)
    return clean