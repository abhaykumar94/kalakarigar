# utils/ai_utils.py
import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import logging
from typing import Dict, Optional, List, Any
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MODEL_NAME = "gemini-2.5-flash"
MAX_DESCRIPTION_LENGTH = 120
DEFAULT_CAPTION_COUNT = 2
DEFAULT_HASHTAG_COUNT = 15


class ContentGenerator:
    """Handles AI content generation for marketing materials."""

    def __init__(self):
        self._model = None

    @property
    def model(self):
        """Lazy load the Gemini model."""
        if self._model is None:
            try:
                self._model = genai.GenerativeModel(MODEL_NAME)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini model: {e}")
                raise
        return self._model

    def _build_prompt(self, craft_details: Dict[str, Any]) -> str:
        """Build optimized prompt for content generation."""
        name = craft_details.get("name", "the artisan")
        craft_type = craft_details.get("craft_type", "N/A")
        description = craft_details.get("description", "N/A")
        materials = craft_details.get("materials", "N/A")
        tags = craft_details.get("tags", [])

        tags_str = ", ".join(tags) if tags else "N/A"

        return f"""You are an expert e-commerce marketing assistant for Indian artisan {name}. 
Create a complete marketing kit based on the image and artisan's details.

**Product Details:**
- Craft Type: {craft_type}
- Description: {description}
- Materials: {materials}
- AI Tags: {tags_str}

Generate JSON with exactly these keys: "product_description", "social_media_captions", "hashtags"

Requirements:
1. **product_description**: Professional 80-100 word description incorporating relevant AI tags
2. **social_media_captions**: Array of {DEFAULT_CAPTION_COUNT} engaging, varied captions
3. **hashtags**: Array of {DEFAULT_HASHTAG_COUNT} relevant hashtags including AI tags

Ensure JSON is valid and complete."""

    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse and validate AI response."""
        try:
            # Clean response
            cleaned = response_text.strip()

            # Remove common markdown formatting
            for marker in ["```json", "```", "`"]:
                cleaned = cleaned.replace(marker, "")

            # Parse JSON
            content = json.loads(cleaned)

            # Validate structure
            required_keys = ["product_description", "social_media_captions", "hashtags"]
            if not all(key in content for key in required_keys):
                logger.warning(
                    f"Missing required keys in response: {list(content.keys())}"
                )
                return None

            # Validate types
            if not isinstance(content["social_media_captions"], list):
                content["social_media_captions"] = [
                    str(content["social_media_captions"])
                ]

            if not isinstance(content["hashtags"], list):
                content["hashtags"] = str(content["hashtags"]).split()

            return content

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return None
        except Exception as e:
            logger.error(f"Response parsing error: {e}")
            return None

    def _create_fallback_content(self, craft_details: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback content if AI generation fails."""
        craft_type = craft_details.get("craft_type", "Handmade Product")
        materials = craft_details.get("materials", "quality materials")

        return {
            "product_description": f"Beautiful {craft_type} crafted with {materials}. "
            f"This authentic handmade piece showcases traditional craftsmanship "
            f"and attention to detail, perfect for those who appreciate unique artistry.",
            "social_media_captions": [
                f"✨ Discover the beauty of {craft_type} - where tradition meets artistry! 🎨",
                f"🌟 Handcrafted with love and {materials}. Each piece tells a story! 💖",
            ],
            "hashtags": [
                "#handmade",
                "#indian",
                "#artisan",
                "#craft",
                "#traditional",
                "#authentic",
                "#handcrafted",
                "#art",
                "#culture",
                "#heritage",
            ],
        }


@st.cache_data(ttl=3600, show_spinner=False)
def get_gemini_response(
    image_bytes: bytes, craft_details: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Generate marketing content from image and craft details.

    Args:
        image: PIL Image object of the product
        craft_details: Dictionary with craft information

    Returns:
        Dictionary with generated content or None if error occurs
    """

    # ✅ Convert the input bytes back to a PIL Image object
    image = Image.open(BytesIO(image_bytes))

    generator = ContentGenerator()

    try:
        # Build prompt
        prompt = generator._build_prompt(craft_details)

        # Generate content
        with st.spinner("Generating content..."):
            response = generator.model.generate_content([prompt, image])

        if not response or not response.text:
            logger.error("Empty response from Gemini")
            return generator._create_fallback_content(craft_details)

        # Parse response
        content = generator._parse_response(response.text)

        if content is None:
            logger.warning("Using fallback content due to parsing failure")
            return generator._create_fallback_content(craft_details)

        logger.info("Successfully generated marketing content")
        return content

    except Exception as e:
        logger.error(f"Content generation error: {e}")
        st.error(f"Content generation failed: {e}")
        return generator._create_fallback_content(craft_details)


def validate_generated_content(content: Dict[str, Any]) -> bool:
    """Validate the structure and quality of generated content."""
    if not isinstance(content, dict):
        return False

    required_keys = ["product_description", "social_media_captions", "hashtags"]

    # Check required keys exist
    if not all(key in content for key in required_keys):
        return False

    # Check content quality
    desc = content.get("product_description", "")
    if not desc or len(desc.strip()) < 50:
        return False

    captions = content.get("social_media_captions", [])
    if not isinstance(captions, list) or len(captions) < 1:
        return False

    hashtags = content.get("hashtags", [])
    if not isinstance(hashtags, list) or len(hashtags) < 5:
        return False

    return True
