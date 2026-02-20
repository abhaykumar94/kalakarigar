# utils/gcp_ai_utils.py
import os
import json
import streamlit as st
from google.cloud import speech, translate_v2 as translate, vision
from google.oauth2 import service_account
from pydub import AudioSegment
import io
import logging
from typing import Optional, List, Union
from io import BytesIO
from PIL import Image
from contextlib import contextmanager
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
SUPPORTED_AUDIO_FORMATS = ["wav", "mp3", "flac", "ogg"]
MAX_AUDIO_SIZE_MB = 10
DEFAULT_SAMPLE_RATE = 16000
MAX_VISION_LABELS = 20


class GCPCredentialsManager:
    """Centralized GCP credentials management."""

    def __init__(self):
        self._credentials = None
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Load GCP credentials from Streamlit secrets."""
        try:
            # --- THIS IS THE FIX ---
            creds_json_str = os.getenv("GCP_SERVICE_ACCOUNT")
            if creds_json_str:
                creds_dict = json.loads(creds_json_str)
            else:
                creds_dict = st.secrets["gcp_service_account"]
            # --- END FIX ---

            self._credentials = service_account.Credentials.from_service_account_info(
                creds_dict
            )
            logger.info("GCP credentials loaded successfully")
        except Exception as e:
            logger.error(f"Error loading GCP credentials: {e}")
            st.error(f"Error loading GCP credentials: {e}")

    @property
    def credentials(self) -> Optional[service_account.Credentials]:
        """Get GCP credentials."""
        return self._credentials

    def is_available(self) -> bool:
        """Check if credentials are available."""
        return self._credentials is not None


# Global credentials manager
_creds_manager = None


def get_credentials_manager() -> GCPCredentialsManager:
    """Get singleton credentials manager."""
    global _creds_manager
    if _creds_manager is None:
        _creds_manager = GCPCredentialsManager()
    return _creds_manager


@contextmanager
def temp_audio_file(audio_data: bytes, format_type: str = "wav"):
    """Create temporary audio file for processing."""
    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{format_type}")
        temp_file.write(audio_data)
        temp_file.close()
        yield temp_file.name
    finally:
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


class AudioProcessor:
    """Optimized audio processing utilities."""

    @staticmethod
    def validate_audio_size(audio_bytes: bytes) -> bool:
        """Validate audio file size."""
        size_mb = len(audio_bytes) / (1024 * 1024)
        return size_mb <= MAX_AUDIO_SIZE_MB

    @staticmethod
    def convert_to_mono(
        audio_bytes: bytes, target_sample_rate: int = DEFAULT_SAMPLE_RATE
    ) -> bytes:
        """
        Convert audio to mono with optimized settings.

        Args:
            audio_bytes: Raw audio data
            target_sample_rate: Target sample rate (default: 16000)

        Returns:
            Processed audio bytes
        """
        try:
            # Load audio with pydub
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))

            # Convert to mono and set sample rate
            audio = audio.set_channels(1).set_frame_rate(target_sample_rate)

            # Export to bytes
            buffer = io.BytesIO()
            audio.export(buffer, format="wav")

            processed_audio = buffer.getvalue()
            logger.info(
                f"Audio converted: {len(audio_bytes)} -> {len(processed_audio)} bytes"
            )
            return processed_audio

        except Exception as e:
            logger.error(f"Audio conversion error: {e}")
            return audio_bytes  # Return original on failure

    @staticmethod
    def detect_audio_properties(audio_bytes: bytes) -> dict:
        """Detect audio properties for optimization."""
        try:
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            return {
                "channels": audio.channels,
                "frame_rate": audio.frame_rate,
                "sample_width": audio.sample_width,
                "duration_seconds": len(audio) / 1000.0,
                "format": "wav",  # Default after conversion
            }
        except Exception as e:
            logger.error(f"Audio property detection failed: {e}")
            return {"channels": 1, "frame_rate": DEFAULT_SAMPLE_RATE, "format": "wav"}


@st.cache_data(ttl=300, show_spinner=False)
def transcribe_audio(
    audio_bytes: bytes,
    language_code: str = "en-US",
    enable_automatic_punctuation: bool = True,
) -> Optional[str]:
    """
    Transcribe audio using Google Cloud Speech-to-Text with optimizations.

    Args:
        audio_bytes: Raw audio data
        language_code: Language code (e.g., 'en-US', 'hi-IN')
        enable_automatic_punctuation: Enable automatic punctuation

    Returns:
        Transcribed text or None if failed
    """
    creds_manager = get_credentials_manager()
    if not creds_manager.is_available():
        st.error("GCP credentials not available for speech recognition.")
        return None

    # Validate audio size
    if not AudioProcessor.validate_audio_size(audio_bytes):
        st.error(f"Audio file too large. Maximum size: {MAX_AUDIO_SIZE_MB}MB")
        return None

    try:
        # Initialize client
        client = speech.SpeechClient(credentials=creds_manager.credentials)

        # Process audio
        processor = AudioProcessor()
        processed_audio = processor.convert_to_mono(audio_bytes)
        audio_properties = processor.detect_audio_properties(processed_audio)

        # Prepare recognition config
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            language_code=language_code,
            sample_rate_hertz=audio_properties["frame_rate"],
            enable_automatic_punctuation=enable_automatic_punctuation,
            audio_channel_count=audio_properties["channels"],
            model="latest_long",  # Use latest model for better accuracy
            use_enhanced=True,  # Enable enhanced model if available
        )

        audio = speech.RecognitionAudio(content=processed_audio)

        # Perform transcription
        with st.spinner("Transcribing audio..."):
            response = client.recognize(config=config, audio=audio)

        if response.results:
            transcript = response.results[0].alternatives[0].transcript
            confidence = response.results[0].alternatives[0].confidence

            logger.info(f"Transcription successful (confidence: {confidence:.2f})")

            # Show confidence warning if low
            if confidence < 0.7:
                st.warning("Transcription confidence is low. Please verify the result.")

            return transcript
        else:
            logger.warning("No transcription results returned")
            st.warning("No speech detected in audio. Please try again.")
            return None

    except Exception as e:
        logger.error(f"Speech-to-Text Error: {e}")
        st.error(f"Transcription failed: {str(e)}")
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def translate_text(
    text: str, target_language: str = "en", source_language: Optional[str] = None
) -> Optional[str]:
    """
    Translate text using Google Cloud Translation with caching.

    Args:
        text: Text to translate
        target_language: Target language code
        source_language: Source language code (auto-detect if None)

    Returns:
        Translated text or None if failed
    """
    creds_manager = get_credentials_manager()
    if not creds_manager.is_available():
        st.error("GCP credentials not available for translation.")
        return None

    if not text or not text.strip():
        logger.warning("Empty text provided for translation")
        return None

    try:
        # Initialize client
        translate_client = translate.Client(credentials=creds_manager.credentials)

        # Perform translation
        with st.spinner("Translating text..."):
            result = translate_client.translate(
                text, target_language=target_language, source_language=source_language
            )

        translated_text = result["translatedText"]
        detected_language = result.get("detectedSourceLanguage")

        logger.info(f"Translation successful: {detected_language} -> {target_language}")

        # Show detected language info
        if detected_language and not source_language:
            st.info(f"Detected source language: {detected_language}")

        return translated_text

    except Exception as e:
        logger.error(f"Translation Error: {e}")
        st.error(f"Translation failed: {str(e)}")
        return None


class VisionAnalyzer:
    """Optimized image analysis using Google Cloud Vision."""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> Optional[vision.ImageAnnotatorClient]:
        """Get Vision API client with lazy initialization."""
        if self._client is None:
            creds_manager = get_credentials_manager()
            if creds_manager.is_available():
                self._client = vision.ImageAnnotatorClient(
                    credentials=creds_manager.credentials
                )
        return self._client

    def _prepare_image(self, image: Image.Image) -> bytes:
        """Prepare PIL image for Vision API."""
        # Optimize image size for API
        max_size = (1024, 1024)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image = image.copy()
            image.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Convert to bytes
        buffer = BytesIO()
        format_type = "JPEG" if image.mode == "RGB" else "PNG"
        image.save(buffer, format=format_type, quality=85, optimize=True)
        return buffer.getvalue()


@st.cache_data(ttl=3600, show_spinner=False)
def get_image_labels(
    image_bytes: bytes, max_results: int = MAX_VISION_LABELS, min_score: float = 0.5
) -> List[str]:
    """
    Analyze image using Google Cloud Vision AI with optimization.

    Args:
        image: PIL Image object
        max_results: Maximum number of labels to return
        min_score: Minimum confidence score for labels

    Returns:
        List of relevant labels/tags
    """
    creds_manager = get_credentials_manager()
    if not creds_manager.is_available():
        st.error("GCP credentials not available for Vision AI.")
        return []

    try:
        # ✅ Convert bytes back to a PIL Image for processing
        image = Image.open(BytesIO(image_bytes))

        analyzer = VisionAnalyzer()
        client = analyzer.client

        if not client:
            logger.error("Failed to initialize Vision API client")
            return []

        # Prepare image (the rest of the function uses the restored 'image' object)
        prepared_image_bytes = analyzer._prepare_image(image)
        vision_image = vision.Image(content=prepared_image_bytes)

        # Perform label detection
        with st.spinner("Analyzing image..."):
            response = client.label_detection(
                image=vision_image, max_results=max_results
            )

        if response.error.message:
            raise Exception(f"Vision API error: {response.error.message}")

        # Filter and sort labels
        labels = [
            label.description
            for label in response.label_annotations
            if label.score >= min_score
        ]

        # Sort by relevance (score)
        sorted_labels = sorted(
            response.label_annotations, key=lambda x: x.score, reverse=True
        )

        result_labels = [
            label.description for label in sorted_labels if label.score >= min_score
        ][:max_results]

        logger.info(f"Vision analysis successful: {len(result_labels)} labels found")
        return result_labels

    except Exception as e:
        logger.error(f"Cloud Vision AI Error: {e}")
        st.error(f"Image analysis failed: {str(e)}")
        return []


def detect_text_in_image(image: Image.Image) -> Optional[str]:
    """
    Detect and extract text from image using OCR.

    Args:
        image: PIL Image object

    Returns:
        Extracted text or None if failed
    """
    creds_manager = get_credentials_manager()
    if not creds_manager.is_available():
        st.error("GCP credentials not available for text detection.")
        return None

    try:
        analyzer = VisionAnalyzer()
        client = analyzer.client

        if not client:
            logger.error("Failed to initialize Vision API client")
            return None

        # Prepare image
        image_bytes = analyzer._prepare_image(image)
        vision_image = vision.Image(content=image_bytes)

        # Perform text detection
        with st.spinner("Detecting text in image..."):
            response = client.text_detection(image=vision_image)

        if response.error.message:
            raise Exception(f"Vision API error: {response.error.message}")

        texts = response.text_annotations
        if texts:
            # Return the first (most comprehensive) text annotation
            detected_text = texts[0].description
            logger.info(f"Text detection successful: {len(detected_text)} characters")
            return detected_text
        else:
            logger.info("No text detected in image")
            return None

    except Exception as e:
        logger.error(f"Text detection error: {e}")
        st.error(f"Text detection failed: {str(e)}")
        return None


@st.cache_data(ttl=300)
def check_gcp_services_health() -> dict:
    """
    Check GCP services health status.

    Returns:
        Dictionary with service health status
    """
    health_status = {
        "credentials": False,
        "speech": False,
        "translate": False,
        "vision": False,
        "overall": False,
    }

    creds_manager = get_credentials_manager()
    health_status["credentials"] = creds_manager.is_available()

    if not health_status["credentials"]:
        return health_status

    # Test Speech API
    try:
        speech.SpeechClient(credentials=creds_manager.credentials)
        health_status["speech"] = True
    except Exception as e:
        logger.warning(f"Speech API health check failed: {e}")

    # Test Translation API
    try:
        translate.Client(credentials=creds_manager.credentials)
        health_status["translate"] = True
    except Exception as e:
        logger.warning(f"Translation API health check failed: {e}")

    # Test Vision API
    try:
        vision.ImageAnnotatorClient(credentials=creds_manager.credentials)
        health_status["vision"] = True
    except Exception as e:
        logger.warning(f"Vision API health check failed: {e}")

    health_status["overall"] = all(
        [health_status["speech"], health_status["translate"], health_status["vision"]]
    )

    return health_status
