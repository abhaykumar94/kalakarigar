# utils/gdrive_utils.py
import os
import json
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
from io import BytesIO
from PIL import Image
import logging
from typing import Dict, Optional, List, Any, Tuple
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

ROOT_FOLDER_NAME = "KalaKarigar.ai Exports"
RETRY_ATTEMPTS = 3
RETRY_DELAY = 1  # seconds


class GoogleDriveManager:
    """Centralized Google Drive operations manager."""

    def __init__(self):
        self._flow = None
        self._drive_service = None
        self._people_service = None

    @property
    def flow(self) -> Optional[InstalledAppFlow]:
        """Get OAuth flow with lazy initialization."""
        if self._flow is None:
            self._flow = self._create_flow()
        return self._flow

    def _create_flow(self) -> Optional[InstalledAppFlow]:
        """Create OAuth flow from configuration, with debugging."""
        try:
            creds_json_str = os.getenv("GDRIVE_OAUTH_CREDENTIALS")
            if creds_json_str:
                client_config = json.loads(creds_json_str)
                # Extract the redirect_uri from the loaded config
                redirect_uri = client_config["web"]["redirect_uris"][0]
            else:
                # Fallback for local testing
                flat_creds = st.secrets["gdrive_oauth_credentials"]
                firebase_creds = st.secrets["firebase_credentials"]
                client_config = {
                    "web": {
                        "client_id": flat_creds["client_id"],
                        "project_id": firebase_creds["project_id"],
                        "auth_uri": flat_creds["auth_uri"],
                        "token_uri": flat_creds["token_uri"],
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "client_secret": flat_creds["client_secret"],
                        "redirect_uris": flat_creds["redirect_uris"],
                    }
                }
                redirect_uri = flat_creds["redirect_uris"][0]

            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            flow.redirect_uri = redirect_uri

            return flow
        except Exception as e:
            st.error(f"Could not configure Google Drive: {e}")
            return None

    def get_drive_service(self) -> Optional[Any]:
        """Get Drive service with credentials from session."""
        if not st.session_state.get("gdrive_credentials"):
            logger.error("No Google Drive credentials in session")
            return None

        try:
            creds_dict = st.session_state.gdrive_credentials
            creds = Credentials.from_authorized_user_info(creds_dict)

            # Check if credentials are valid
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    # Update session with refreshed credentials
                    st.session_state.gdrive_credentials = {
                        "token": creds.token,
                        "refresh_token": creds.refresh_token,
                        "token_uri": creds.token_uri,
                        "client_id": creds.client_id,
                        "client_secret": creds.client_secret,
                        "scopes": creds.scopes,
                    }
                else:
                    logger.error("Invalid credentials and cannot refresh")
                    return None

            service = build("drive", "v3", credentials=creds)
            logger.info("Drive service created successfully")
            return service

        except Exception as e:
            logger.error(f"Failed to create Drive service: {e}")
            return None

    def get_people_service(self) -> Optional[Any]:
        """Get People service for user info."""
        if not st.session_state.get("gdrive_credentials"):
            logger.error("No Google Drive credentials in session")
            return None

        try:
            creds_dict = st.session_state.gdrive_credentials
            creds = Credentials.from_authorized_user_info(creds_dict)

            service = build("people", "v1", credentials=creds)
            logger.info("People service created successfully")
            return service

        except Exception as e:
            logger.error(f"Failed to create People service: {e}")
            return None


# Global Drive manager instance
_drive_manager = None


def get_drive_manager() -> GoogleDriveManager:
    """Get singleton Drive manager instance."""
    global _drive_manager
    if _drive_manager is None:
        _drive_manager = GoogleDriveManager()
    return _drive_manager


def get_gdrive_flow() -> Optional[InstalledAppFlow]:
    """Get OAuth flow for Google Drive authentication."""
    manager = get_drive_manager()
    return manager.flow


@st.cache_data(ttl=300)
def get_gdrive_service_from_session() -> Optional[Any]:
    """Get Drive service using session credentials with caching."""
    manager = get_drive_manager()
    return manager.get_drive_service()


@st.cache_data(ttl=3600)
def get_user_info() -> Optional[Dict[str, str]]:
    """
    Fetch user's profile information with caching.

    Returns:
        Dictionary with user name and email or None if failed
    """
    manager = get_drive_manager()
    service = manager.get_people_service()

    if not service:
        logger.error("People service not available")
        return None

    try:
        profile = (
            service.people()
            .get(resourceName="people/me", personFields="names,emailAddresses")
            .execute()
        )

        name = profile.get("names", [{}])[0].get("displayName", "Unknown User")
        email = profile.get("emailAddresses", [{}])[0].get("value", "unknown@email.com")

        user_info = {"name": name, "email": email}
        logger.info(f"Retrieved user info for: {email}")
        return user_info

    except HttpError as e:
        logger.error(f"HTTP error fetching user info: {e}")
        st.error("Failed to fetch user information")
        return None
    except Exception as e:
        logger.error(f"Error fetching user info: {e}")
        st.error(f"Failed to get user information: {e}")
        return None


def retry_operation(func, *args, **kwargs):
    """Retry operation with exponential backoff."""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            return func(*args, **kwargs)
        except HttpError as e:
            if attempt == RETRY_ATTEMPTS - 1:
                raise

            # Check if it's a retryable error
            if e.resp.status in [429, 500, 502, 503, 504]:
                delay = RETRY_DELAY * (2**attempt)
                logger.warning(
                    f"Retrying operation in {delay}s (attempt {attempt + 1})"
                )
                time.sleep(delay)
            else:
                raise
        except Exception as e:
            if attempt == RETRY_ATTEMPTS - 1:
                raise
            delay = RETRY_DELAY * (2**attempt)
            logger.warning(
                f"Retrying operation in {delay}s (attempt {attempt + 1}): {e}"
            )
            time.sleep(delay)


class FolderManager:
    """Manages Google Drive folder operations."""

    def __init__(self, service):
        self.service = service

    def find_or_create_root_folder(self) -> Optional[str]:
        """Find or create the root export folder."""
        try:
            # Search for existing folder
            query = f"name='{ROOT_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            response = retry_operation(
                self.service.files().list,
                q=query,
                spaces="drive",
                fields="files(id, name)",
            ).execute()

            files = response.get("files", [])

            if files:
                folder_id = files[0]["id"]
                logger.info(f"Found existing root folder: {folder_id}")
                return folder_id

            # Create new folder
            folder_metadata = {
                "name": ROOT_FOLDER_NAME,
                "mimeType": "application/vnd.google-apps.folder",
                "description": "KalaKarigar.ai marketing pack exports",
            }

            folder = retry_operation(
                self.service.files().create, body=folder_metadata, fields="id"
            ).execute()

            folder_id = folder["id"]
            logger.info(f"Created new root folder: {folder_id}")
            return folder_id

        except Exception as e:
            logger.error(f"Failed to find/create root folder: {e}")
            return None

    def create_project_folder(
        self, parent_id: str, folder_name: str
    ) -> Optional[Tuple[str, str]]:
        """Create a project-specific folder."""
        try:
            # Add timestamp and user info for uniqueness
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_name = f"{folder_name}_{timestamp}"

            folder_metadata = {
                "name": unique_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
                "description": f"KalaKarigar.ai export created on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            }

            folder = retry_operation(
                self.service.files().create,
                body=folder_metadata,
                fields="id, webViewLink",
            ).execute()

            folder_id = folder["id"]
            folder_link = folder["webViewLink"]

            logger.info(f"Created project folder: {unique_name} ({folder_id})")
            return folder_id, folder_link

        except Exception as e:
            logger.error(f"Failed to create project folder: {e}")
            return None, None


class FileUploader:
    """Handles file upload operations to Google Drive."""

    def __init__(self, service):
        self.service = service

    def upload_image(
        self,
        image: Image.Image,
        folder_id: str,
        filename: str = "AI_Enhanced_Image.png",
    ) -> bool:
        """Upload enhanced image to Drive."""
        try:
            # Prepare image
            buffered_image = BytesIO()

            # Optimize image for web sharing
            if image.mode != "RGB":
                image = image.convert("RGB")

            image.save(buffered_image, format="PNG", optimize=True, quality=95)

            buffered_image.seek(0)

            # Create media upload
            media = MediaIoBaseUpload(
                buffered_image,
                mimetype="image/png",
                resumable=True,
                chunksize=1024 * 1024,  # 1MB chunks
            )

            # File metadata
            file_metadata = {
                "name": filename,
                "parents": [folder_id],
                "description": "AI-enhanced product image from KalaKarigar.ai",
            }

            # Upload with retry
            retry_operation(
                self.service.files().create,
                body=file_metadata,
                media_body=media,
                fields="id",
            ).execute()

            logger.info(f"Image uploaded successfully: {filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to upload image: {e}")
            return False

    def upload_text_content(
        self, content: str, folder_id: str, filename: str = "AI_Generated_Content.txt"
    ) -> bool:
        """Upload text content to Drive."""
        try:
            # Prepare text content
            content_with_header = f"""# KalaKarigar.ai Marketing Pack
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*50}

{content}

{'='*50}
Generated by KalaKarigar.ai - Empowering Indian Artisans
"""

            # Convert to bytes
            text_bytes = content_with_header.encode("utf-8")
            buffered_text = BytesIO(text_bytes)

            # Create media upload
            media = MediaIoBaseUpload(
                buffered_text, mimetype="text/plain", resumable=True
            )

            # File metadata
            file_metadata = {
                "name": filename,
                "parents": [folder_id],
                "description": "AI-generated marketing content from KalaKarigar.ai",
            }

            # Upload with retry
            retry_operation(
                self.service.files().create,
                body=file_metadata,
                media_body=media,
                fields="id",
            ).execute()

            logger.info(f"Text content uploaded successfully: {filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to upload text content: {e}")
            return False

    def upload_metadata(
        self,
        metadata: Dict[str, Any],
        folder_id: str,
        filename: str = "project_metadata.json",
    ) -> bool:
        """Upload project metadata as JSON."""
        try:
            # Prepare metadata
            metadata_content = json.dumps(metadata, indent=2, ensure_ascii=False)
            metadata_bytes = metadata_content.encode("utf-8")
            buffered_metadata = BytesIO(metadata_bytes)

            # Create media upload
            media = MediaIoBaseUpload(
                buffered_metadata, mimetype="application/json", resumable=True
            )

            # File metadata
            file_metadata = {
                "name": filename,
                "parents": [folder_id],
                "description": "Project metadata from KalaKarigar.ai",
            }

            # Upload with retry
            retry_operation(
                self.service.files().create,
                body=file_metadata,
                media_body=media,
                fields="id",
            ).execute()

            logger.info(f"Metadata uploaded successfully: {filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to upload metadata: {e}")
            return False


def export_marketing_pack(
    service: Any,
    image: Image.Image,
    text_content: str,
    folder_name: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Export complete marketing pack to Google Drive with enhanced features.

    Args:
        service: Google Drive service instance
        image: Enhanced product image
        text_content: Generated marketing content
        folder_name: Base folder name
        metadata: Additional project metadata

    Returns:
        Folder web view link or None if failed
    """
    try:
        # Initialize managers
        folder_manager = FolderManager(service)
        file_uploader = FileUploader(service)

        # Create folder structure
        with st.spinner("Creating folder structure..."):
            root_folder_id = folder_manager.find_or_create_root_folder()
            if not root_folder_id:
                st.error("Failed to create root folder")
                return None

        with st.spinner("Setting up project folder..."):
            project_folder_id, folder_link = folder_manager.create_project_folder(
                root_folder_id, folder_name
            )
            if not project_folder_id:
                st.error("Failed to create project folder")
                return None

        # Upload files
        upload_success = []

        with st.spinner("Uploading enhanced image..."):
            success = file_uploader.upload_image(image, project_folder_id)
            upload_success.append(success)

        with st.spinner("Uploading marketing content..."):
            success = file_uploader.upload_text_content(text_content, project_folder_id)
            upload_success.append(success)

        # Upload metadata if provided
        if metadata:
            with st.spinner("Uploading project metadata..."):
                success = file_uploader.upload_metadata(metadata, project_folder_id)
                upload_success.append(success)

        # Check overall success
        if all(upload_success):
            logger.info(f"Marketing pack exported successfully: {folder_link}")
            return folder_link
        else:
            failed_count = sum(1 for x in upload_success if not x)
            st.warning(f"Export completed with {failed_count} failed uploads")
            return folder_link

    except Exception as e:
        logger.error(f"Failed to export marketing pack: {e}")
        st.error(f"Export failed: {str(e)}")
        return None


def check_drive_quota(service: Any) -> Optional[Dict[str, Any]]:
    """
    Check Google Drive storage quota information.

    Args:
        service: Google Drive service instance

    Returns:
        Dictionary with quota information or None if failed
    """
    try:
        about = service.about().get(fields="storageQuota").execute()
        quota = about.get("storageQuota", {})

        total = int(quota.get("limit", 0))
        used = int(quota.get("usage", 0))
        available = total - used if total > 0 else float("inf")

        return {
            "total_gb": round(total / (1024**3), 2) if total > 0 else "Unlimited",
            "used_gb": round(used / (1024**3), 2),
            "available_gb": (
                round(available / (1024**3), 2)
                if available != float("inf")
                else "Unlimited"
            ),
            "usage_percentage": round((used / total) * 100, 1) if total > 0 else 0,
        }

    except Exception as e:
        logger.error(f"Failed to check Drive quota: {e}")
        return None


@st.cache_data(ttl=300)
def check_gdrive_health() -> Dict[str, bool]:
    """
    Check Google Drive service health.

    Returns:
        Dictionary with health status
    """
    health_status = {
        "credentials": False,
        "drive_api": False,
        "people_api": False,
        "overall": False,
    }

    try:
        # Check credentials
        if st.session_state.get("gdrive_credentials"):
            health_status["credentials"] = True

        if not health_status["credentials"]:
            return health_status

        # Check Drive API
        try:
            service = get_gdrive_service_from_session()
            if service:
                # Test with a simple API call
                service.about().get(fields="user").execute()
                health_status["drive_api"] = True
        except Exception as e:
            logger.warning(f"Drive API health check failed: {e}")

        # Check People API
        try:
            manager = get_drive_manager()
            people_service = manager.get_people_service()
            if people_service:
                # Test with a simple API call
                people_service.people().get(
                    resourceName="people/me", personFields="names"
                ).execute()
                health_status["people_api"] = True
        except Exception as e:
            logger.warning(f"People API health check failed: {e}")

        health_status["overall"] = all(
            [
                health_status["credentials"],
                health_status["drive_api"],
                health_status["people_api"],
            ]
        )

    except Exception as e:
        logger.error(f"Google Drive health check failed: {e}")

    return health_status
