# utils/image_utils.py
import os
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter
import google.generativeai as genai
from io import BytesIO
import logging
from typing import Optional, Dict, Tuple, Any
from enum import Enum
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MAX_IMAGE_SIZE = (2048, 2048)
QUALITY_SETTINGS = {"high": 95, "medium": 85, "low": 75}
FALLBACK_TIMEOUT = 30  # seconds


class ImageStyle(Enum):
    """Enumeration of available image enhancement styles."""

    VIBRANT = "Vibrant"
    STUDIO = "Studio"
    FESTIVE = "Festive"


class ImageProcessor:
    """Handles image preprocessing and optimization."""

    @staticmethod
    def validate_image(image: Image.Image) -> bool:
        """Validate image for processing."""
        if not isinstance(image, Image.Image):
            logger.error("Invalid image type")
            return False

        if image.size[0] < 64 or image.size[1] < 64:
            logger.error("Image too small")
            return False

        if image.size[0] > 4096 or image.size[1] > 4096:
            logger.error("Image too large")
            return False

        return True

    @staticmethod
    def optimize_for_ai(image: Image.Image) -> Image.Image:
        """Optimize image for AI processing."""
        try:
            # Create a copy to avoid modifying original
            optimized = image.copy()

            # Convert to RGB if needed
            if optimized.mode in ("RGBA", "P", "LA"):
                # Create white background for transparency
                background = Image.new("RGB", optimized.size, (255, 255, 255))
                if optimized.mode == "P":
                    optimized = optimized.convert("RGBA")
                background.paste(
                    optimized,
                    mask=optimized.split()[-1] if optimized.mode == "RGBA" else None,
                )
                optimized = background
            elif optimized.mode != "RGB":
                optimized = optimized.convert("RGB")

            # Resize if too large
            if (
                optimized.size[0] > MAX_IMAGE_SIZE[0]
                or optimized.size[1] > MAX_IMAGE_SIZE[1]
            ):
                optimized.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)

            # Enhance image quality slightly
            enhancer = ImageEnhance.Sharpness(optimized)
            optimized = enhancer.enhance(1.1)

            logger.info(f"Image optimized: {image.size} -> {optimized.size}")
            return optimized

        except Exception as e:
            logger.error(f"Image optimization failed: {e}")
            return image

    @staticmethod
    def create_fallback_enhancement(image: Image.Image, style: str) -> Image.Image:
        """Create fallback enhancement using PIL when AI fails."""
        try:
            enhanced = image.copy()

            if style == ImageStyle.VIBRANT.value:
                # Increase saturation and contrast
                enhancer = ImageEnhance.Color(enhanced)
                enhanced = enhancer.enhance(1.3)
                enhancer = ImageEnhance.Contrast(enhanced)
                enhanced = enhancer.enhance(1.2)
                enhancer = ImageEnhance.Brightness(enhanced)
                enhanced = enhancer.enhance(1.1)

            elif style == ImageStyle.STUDIO.value:
                # Apply subtle sharpening and brightness adjustment
                enhanced = enhanced.filter(
                    ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3)
                )
                enhancer = ImageEnhance.Brightness(enhanced)
                enhanced = enhancer.enhance(1.05)
                enhancer = ImageEnhance.Contrast(enhanced)
                enhanced = enhancer.enhance(1.1)

            elif style == ImageStyle.FESTIVE.value:
                # Warm tone enhancement
                enhancer = ImageEnhance.Color(enhanced)
                enhanced = enhancer.enhance(1.2)
                enhancer = ImageEnhance.Brightness(enhanced)
                enhanced = enhancer.enhance(1.15)

                # Apply warm filter effect
                warm_overlay = Image.new("RGB", enhanced.size, (255, 220, 180))
                enhanced = Image.blend(enhanced, warm_overlay, 0.1)

            logger.info(f"Fallback enhancement applied: {style}")
            return enhanced

        except Exception as e:
            logger.error(f"Fallback enhancement failed: {e}")
            return image


class GeminiImageGenerator:
    """Handles Gemini AI image generation with optimizations."""

    def __init__(self):
        self._model = None
        self._style_prompts = {
            ImageStyle.VIBRANT.value: (
                "Create a vibrant, professional product photograph with enhanced colors. "
                "The image should have vivid, saturated colors with high contrast and sharp focus. "
                "Ensure the lighting brings out all the details and textures. The background should "
                "complement the product without distracting from it. Make it look premium and eye-catching "
                "for e-commerce use."
            ),
            ImageStyle.STUDIO.value: (
                "Create a professional studio product shot with clean, minimalist aesthetics. "
                "Use soft, even lighting against a clean light background (white or light gray). "
                "The lighting should highlight the craftsmanship details and textures without harsh shadows. "
                "The result should look elegant, high-end, and suitable for luxury product marketing."
            ),
            ImageStyle.FESTIVE.value: (
                "Create a festive-themed product photograph with warm, celebratory atmosphere. "
                "Add warm lighting with subtle traditional Indian elements or warm bokeh lights in the background. "
                "The lighting should be inviting and warm, evoking feelings of celebration like Diwali or weddings. "
                "Maintain focus on the product while creating a joyful, festive mood."
            ),
        }

    @property
    def model(self) -> Optional[genai.GenerativeModel]:
        """Get Gemini model with lazy initialization."""
        if self._model is None:
            try:
                api_key = st.secrets.get("GEMINI_API_KEY")
                if not api_key:
                    logger.error("GEMINI_API_KEY not found in secrets")
                    return None

                genai.configure(api_key=api_key)
                self._model = genai.GenerativeModel("gemini-2.5-flash-image-preview")
                logger.info("Gemini model initialized successfully")

            except Exception as e:
                logger.error(f"Failed to initialize Gemini model: {e}")
                return None

        return self._model

    def generate_enhanced_image(
        self, image: Image.Image, style: str
    ) -> Optional[Image.Image]:
        """Generate enhanced image using Gemini AI."""
        if not self.model:
            logger.error("Gemini model not available")
            return None

        try:
            prompt = self._style_prompts.get(
                style,
                "Create a high-quality, professional product photograph with enhanced visual appeal.",
            )

            # Generate content with timeout handling
            start_time = time.time()

            with st.spinner(f"Applying {style} enhancement with AI..."):
                response = self.model.generate_content([prompt, image])

            elapsed_time = time.time() - start_time
            logger.info(f"AI generation completed in {elapsed_time:.2f} seconds")

            if not response.candidates:
                logger.warning("No candidates returned from Gemini")
                return None

            # Process response - use original structure
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    try:
                        enhanced_image = Image.open(BytesIO(part.inline_data.data))
                        logger.info(
                            f"Successfully generated enhanced image: {enhanced_image.size}"
                        )
                        return enhanced_image

                    except Exception as decode_err:
                        logger.error(f"Failed to decode generated image: {decode_err}")

                elif part.text:
                    logger.warning(
                        f"Gemini returned text instead of image: {part.text[:100]}..."
                    )

            logger.warning("No valid image data found in Gemini response")
            return None

        except Exception as e:
            logger.error(f"Gemini image generation failed: {e}")
            return None


@st.cache_data(ttl=300, show_spinner=False)
def generate_enhanced_image(image_bytes: bytes, style: str) -> Optional[Image.Image]:
    """
    Generate enhanced image with fallback support and caching.

    Args:
        image_bytes: Raw image bytes to enhance
        style: Enhancement style (Vibrant, Studio, Festive)

    Returns:
        Enhanced Image object or None if all methods fail
    """
    # Convert bytes back to a PIL Image at the beginning
    image = Image.open(BytesIO(image_bytes))

    # Validate inputs
    processor = ImageProcessor()
    if not processor.validate_image(image):
        st.error("Invalid image provided for enhancement")
        return None

    if style not in [s.value for s in ImageStyle]:
        logger.warning(f"Unknown style '{style}', using Vibrant as fallback")
        style = ImageStyle.VIBRANT.value

    # Optimize image for processing
    optimized_image = processor.optimize_for_ai(image)

    # Try AI enhancement first
    generator = GeminiImageGenerator()
    enhanced_image = None

    try:
        # Set a timeout for AI generation
        start_time = time.time()
        enhanced_image = generator.generate_enhanced_image(optimized_image, style)

        elapsed_time = time.time() - start_time
        if elapsed_time > FALLBACK_TIMEOUT:
            logger.warning(
                f"AI generation took too long ({elapsed_time:.2f}s), may timeout"
            )

        if enhanced_image:
            logger.info("AI enhancement successful")
            return enhanced_image

    except Exception as e:
        logger.error(f"AI enhancement failed: {e}")

    # Fallback to PIL enhancement
    logger.info("Using fallback PIL enhancement")

    try:
        with st.spinner(f"Applying {style} enhancement (fallback mode)..."):
            enhanced_image = processor.create_fallback_enhancement(
                optimized_image, style
            )

        if enhanced_image and enhanced_image != optimized_image:
            st.info("Enhancement applied using fallback method")
            return enhanced_image
        else:
            logger.warning("Fallback enhancement produced no changes")

    except Exception as e:
        logger.error(f"Fallback enhancement failed: {e}")

    # Last resort - return original optimized image
    logger.warning("All enhancement methods failed, returning optimized original")
    st.warning("Enhancement failed, returning optimized original image")
    return optimized_image


def save_enhanced_image(
    image: Image.Image, filename: str, quality: str = "high"
) -> Optional[BytesIO]:
    """
    Save enhanced image to BytesIO buffer with specified quality.

    Args:
        image: PIL Image to save
        filename: Base filename (without extension)
        quality: Quality level ('high', 'medium', 'low')

    Returns:
        BytesIO buffer containing the image or None if failed
    """
    try:
        buffer = BytesIO()

        # Determine format and quality
        format_type = "PNG" if image.mode == "RGBA" else "JPEG"
        quality_value = QUALITY_SETTINGS.get(quality, QUALITY_SETTINGS["high"])

        # Save image
        save_kwargs = {"format": format_type, "optimize": True}

        if format_type == "JPEG":
            save_kwargs["quality"] = quality_value
        elif format_type == "PNG":
            save_kwargs["compress_level"] = 6  # Good balance of size/speed

        image.save(buffer, **save_kwargs)
        buffer.seek(0)

        logger.info(f"Image saved: {format_type}, Quality: {quality}")
        return buffer

    except Exception as e:
        logger.error(f"Failed to save enhanced image: {e}")
        return None


def get_image_info(image: Image.Image) -> Dict[str, Any]:
    """
    Get comprehensive information about an image.

    Args:
        image: PIL Image object

    Returns:
        Dictionary with image information
    """
    try:
        info = {
            "size": image.size,
            "width": image.size[0],
            "height": image.size[1],
            "mode": image.mode,
            "format": getattr(image, "format", "Unknown"),
            "has_transparency": image.mode in ("RGBA", "LA", "P"),
            "aspect_ratio": round(image.size[0] / image.size[1], 2),
            "megapixels": round((image.size[0] * image.size[1]) / 1_000_000, 2),
        }

        # Add file size estimate
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        info["estimated_size_mb"] = round(len(buffer.getvalue()) / (1024 * 1024), 2)

        return info

    except Exception as e:
        logger.error(f"Failed to get image info: {e}")
        return {"error": str(e)}


def validate_enhancement_result(
    original: Image.Image, enhanced: Image.Image
) -> Dict[str, Any]:
    """
    Validate enhancement result by comparing original and enhanced images.

    Args:
        original: Original PIL Image
        enhanced: Enhanced PIL Image

    Returns:
        Dictionary with validation results
    """
    try:
        validation = {
            "is_valid": True,
            "messages": [],
            "warnings": [],
            "improvements": [],
        }

        # Size comparison
        if enhanced.size != original.size:
            if (
                enhanced.size[0] > original.size[0]
                or enhanced.size[1] > original.size[1]
            ):
                validation["improvements"].append("Resolution enhanced")
            else:
                validation["warnings"].append("Resolution reduced")

        # Mode comparison
        if enhanced.mode != original.mode:
            if enhanced.mode == "RGB" and original.mode in ("RGBA", "P"):
                validation["improvements"].append("Optimized for web display")

        # File size estimate
        orig_buffer = BytesIO()
        original.save(orig_buffer, format="PNG")
        orig_size = len(orig_buffer.getvalue())

        enh_buffer = BytesIO()
        enhanced.save(enh_buffer, format="PNG")
        enh_size = len(enh_buffer.getvalue())

        size_ratio = enh_size / orig_size
        if size_ratio < 0.8:
            validation["improvements"].append("File size optimized")
        elif size_ratio > 2.0:
            validation["warnings"].append("File size significantly increased")

        # Basic quality check
        if enhanced == original:
            validation["warnings"].append("No visible changes detected")
        else:
            validation["improvements"].append("Visual enhancements applied")

        # Overall validation
        validation["is_valid"] = (
            len(validation["warnings"]) == 0 or len(validation["improvements"]) > 0
        )

        return validation

    except Exception as e:
        logger.error(f"Enhancement validation failed: {e}")
        return {
            "is_valid": False,
            "messages": [f"Validation error: {str(e)}"],
            "warnings": [],
            "improvements": [],
        }


@st.cache_data(ttl=300)
def check_image_generation_health() -> Dict[str, bool]:
    """
    Check image generation service health.

    Returns:
        Dictionary with health status
    """
    health_status = {
        "gemini_api_key": False,
        "gemini_model": False,
        "pil_available": False,
        "overall": False,
    }

    # Check API key
    try:
        api_key = os.getenv("GEMINI_API_KEY", st.secrets.get("GEMINI_API_KEY"))
        health_status["gemini_api_key"] = bool(api_key)
    except Exception:
        pass

    # Check Gemini model
    if health_status["gemini_api_key"]:
        try:
            generator = GeminiImageGenerator()
            health_status["gemini_model"] = generator.model is not None
        except Exception as e:
            logger.warning(f"Gemini model health check failed: {e}")

    # Check PIL availability
    try:
        # Test basic PIL operations
        test_image = Image.new("RGB", (100, 100), "white")
        processor = ImageProcessor()
        processor.optimize_for_ai(test_image)
        health_status["pil_available"] = True
    except Exception as e:
        logger.warning(f"PIL health check failed: {e}")

    # Overall health (at least fallback should work)
    health_status["overall"] = health_status["pil_available"]

    return health_status
