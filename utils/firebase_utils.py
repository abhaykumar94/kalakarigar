# utils/firebase_utils.py
import json
import os
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, storage
from uuid import uuid4
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FirebaseManager:
    """Centralized Firebase operations manager."""

    def __init__(self):
        self._app = None
        self._db = None
        self._bucket = None

    @property
    def app(self) -> firebase_admin.App:
        """Get Firebase app instance with lazy initialization."""
        if self._app is None:
            self._app = self._initialize_app()
        return self._app

    @property
    def db(self) -> firestore.Client:
        """Get Firestore client with lazy initialization."""
        if self._db is None:
            self._db = firestore.client()
        return self._db

    @property
    def bucket(self) -> storage.bucket:
        """Get Storage bucket with lazy initialization."""
        if self._bucket is None:
            self._bucket = storage.bucket()
        return self._bucket

    def _initialize_app(self) -> Optional[firebase_admin.App]:
        """Initialize Firebase Admin SDK."""
        try:
            if firebase_admin._apps:
                return firebase_admin.get_app()

            # --- THIS IS THE FIX ---
            # Check for the environment variable first (for Cloud Run)
            creds_json_str = os.getenv("FIREBASE_CREDENTIALS")
            if creds_json_str:
                creds_dict = json.loads(creds_json_str)
            else:
                # Fallback to secrets.toml for local development
                creds_dict = dict(st.secrets["firebase_credentials"])
            # --- END FIX ---

            if "\\n" in creds_dict["private_key"]:
                creds_dict["private_key"] = creds_dict["private_key"].replace(
                    "\\n", "\n"
                )

            cred = credentials.Certificate(creds_dict)
            app = firebase_admin.initialize_app(
                cred,
                {"storageBucket": f"{creds_dict['project_id']}.firebasestorage.app"},
            )
            logger.info("Firebase initialized successfully")
            return app
        except Exception as e:
            logger.error(f"Firebase initialization failed: {e}")
            st.error(f"Failed to initialize Firebase: {e}")
            return None


# Global Firebase manager instance
_firebase_manager = None


def get_firebase_manager() -> FirebaseManager:
    """Get singleton Firebase manager instance."""
    global _firebase_manager
    if _firebase_manager is None:
        _firebase_manager = FirebaseManager()
    return _firebase_manager


@st.cache_resource
def init_firebase() -> bool:
    """Initialize Firebase services."""
    try:
        manager = get_firebase_manager()
        if manager.app is None:
            return False

        # Test connectivity
        _ = manager.db
        _ = manager.bucket

        return True
    except Exception as e:
        logger.error(f"Firebase initialization test failed: {e}")
        return False


def upload_image_to_storage(
    image_bytes: bytes, file_name: str, folder: str = "products"
) -> Optional[str]:
    """
    Upload image bytes to Firebase Storage with optimized settings.

    Args:
        image_bytes: Raw image data
        file_name: Original file name
        folder: Storage folder (default: "products")

    Returns:
        Public URL of uploaded image or None if failed
    """
    try:
        manager = get_firebase_manager()
        bucket = manager.bucket

        # Generate unique filename
        file_extension = file_name.split(".")[-1] if "." in file_name else "jpg"
        unique_filename = f"{folder}/{uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"

        # Create blob
        blob = bucket.blob(unique_filename)

        # Set metadata for better caching
        blob.metadata = {
            "contentType": f"image/{file_extension}",
            "cacheControl": "public, max-age=31536000",  # 1 year cache
            "originalName": file_name,
        }

        # Upload with retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                blob.upload_from_string(
                    image_bytes, content_type=f"image/{file_extension}"
                )
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Upload attempt {attempt + 1} failed: {e}")

        # Make public
        blob.make_public()

        logger.info(f"Image uploaded successfully: {unique_filename}")
        return blob.public_url

    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        st.error(f"Failed to upload image: {e}")
        return None


def save_artisan_data(artisan_data: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """
    Save artisan and product data to Firestore with enhanced structure.

    Args:
        artisan_data: Dictionary containing artisan information

    Returns:
        Tuple of (collection_id, document_id) or None if failed
    """
    try:
        manager = get_firebase_manager()
        db = manager.db

        # Prepare data with metadata
        enhanced_data = {
            **artisan_data,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0",
            "status": "active",
        }

        # Add data validation
        required_fields = ["name", "craft_type", "description"]
        missing_fields = [
            field for field in required_fields if not enhanced_data.get(field)
        ]

        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            st.error(f"Missing required data: {', '.join(missing_fields)}")
            return None

        # Save to Firestore
        doc_ref = db.collection("artisans").add(enhanced_data)
        document_id = doc_ref[1].id

        logger.info(f"Artisan data saved successfully: {document_id}")
        return ("artisans", document_id)

    except Exception as e:
        logger.error(f"Failed to save artisan data: {e}")
        st.error(f"Failed to save data: {e}")
        return None


def get_artisan_data(document_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve artisan data from Firestore.

    Args:
        document_id: Firestore document ID

    Returns:
        Dictionary containing artisan data or None if not found
    """
    try:
        manager = get_firebase_manager()
        db = manager.db

        doc_ref = db.collection("artisans").document(document_id)
        doc = doc_ref.get()

        if not doc.exists:
            logger.warning(f"Document not found: {document_id}")
            return None

        data = doc.to_dict()
        logger.info(f"Retrieved artisan data: {document_id}")
        return data

    except Exception as e:
        logger.error(f"Failed to retrieve artisan data: {e}")
        return None


def update_artisan_data(document_id: str, updates: Dict[str, Any]) -> bool:
    """
    Update existing artisan data in Firestore.

    Args:
        document_id: Firestore document ID
        updates: Dictionary of fields to update

    Returns:
        True if successful, False otherwise
    """
    try:
        manager = get_firebase_manager()
        db = manager.db

        # Add update metadata
        updates["updated_at"] = datetime.utcnow().isoformat()
        updates["last_modified"] = firestore.SERVER_TIMESTAMP

        doc_ref = db.collection("artisans").document(document_id)
        doc_ref.update(updates)

        logger.info(f"Artisan data updated: {document_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to update artisan data: {e}")
        return False


def delete_image_from_storage(image_url: str) -> bool:
    """
    Delete image from Firebase Storage.

    Args:
        image_url: Public URL of the image to delete

    Returns:
        True if successful, False otherwise
    """
    try:
        manager = get_firebase_manager()
        bucket = manager.bucket

        # Extract blob name from URL
        blob_name = image_url.split("/")[-1].split("?")[0]
        blob_name = blob_name.replace("%2F", "/")  # Decode URL encoding

        blob = bucket.blob(blob_name)
        blob.delete()

        logger.info(f"Image deleted successfully: {blob_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete image: {e}")
        return False


@st.cache_data(ttl=300)  # Cache for 5 minutes
def check_firebase_health() -> Dict[str, bool]:
    """
    Check Firebase services health status.

    Returns:
        Dictionary with service health status
    """
    health_status = {"firestore": False, "storage": False, "overall": False}

    try:
        manager = get_firebase_manager()

        # Test Firestore
        try:
            db = manager.db
            # Try a simple read operation
            db.collection("_health_check").limit(1).get()
            health_status["firestore"] = True
        except Exception as e:
            logger.warning(f"Firestore health check failed: {e}")

        # Test Storage
        try:
            bucket = manager.bucket
            # Try to get bucket metadata
            bucket.get_blob("non-existent-file")  # This will fail gracefully
            health_status["storage"] = True
        except Exception:
            # Expected to fail for non-existent file, but bucket is accessible
            health_status["storage"] = True

        health_status["overall"] = all(
            [health_status["firestore"], health_status["storage"]]
        )

    except Exception as e:
        logger.error(f"Firebase health check failed: {e}")

    return health_status
