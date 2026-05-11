from transformers import TrOCRProcessor, VisionEncoderDecoderModel
import torch
from PIL import Image as PILImage
import numpy as np
from loguru import logger

from app.core.config import SETTINGS

logger.info("Loading TrOCR model | name={}", SETTINGS.trocr_model_name)
processor = TrOCRProcessor.from_pretrained(SETTINGS.trocr_model_name)
model = VisionEncoderDecoderModel.from_pretrained(SETTINGS.trocr_model_name)
logger.info("TrOCR model loaded")

# Use a GPU if one is available — the model runs much faster on CUDA (Nvidia GPU)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = model.to(device)

# run TrOCR on a processed image
def run_ocr(clean: np.ndarray) -> str:
    """
    Run handwriting recognition on a pre-processed document image.

    HOW IT WORKS:
        1. Convert the NumPy array back to a PIL image in RGB mode
           (TrOCR expects a colour PIL image, even though ours is grayscale)
        2. The processor tokenizes the image into pixel_values tensors
        3. The model generates a sequence of token IDs (like a language model)
        4. The processor decodes those token IDs back into a string

    Args:
        clean (np.ndarray): A binarized grayscale image (output of process_document).

    Returns:
        str: The extracted text as a plain string.
    """
    logger.debug("OCR inference | input_shape={}", clean.shape)

    # TrOCR expects a 3-channel (RGB) PIL image — convert even though it's B&W
    pil_image = PILImage.fromarray(clean).convert('RGB')

    # Preprocess: resize, normalize, and convert to a PyTorch tensor
    pixel_values = processor(pil_image, return_tensors='pt').pixel_values.to(device)

    # Generate text token IDs using the model (greedy decoding by default)
    generated_ids = model.generate(pixel_values)

    # Decode token IDs back to a human-readable string
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    logger.debug("OCR result | chars={} preview={!r}", len(text), text[:60] + "…" if len(text) > 60 else text)
    return text