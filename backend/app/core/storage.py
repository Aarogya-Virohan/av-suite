import logging
from typing import BinaryIO
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger(__name__)

class SupabaseStorageClient:
    """Wrapper for Supabase Storage API using the service role key for private bucket access."""

    def __init__(self) -> None:
        # Initialize the Supabase client with the secret key to bypass RLS
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SECRET_KEY
        )
        self.bucket_name = settings.SUPABASE_BUCKET_NAME

    def upload_file(self, path: str, file_data: bytes, content_type: str) -> str:
        """
        Uploads a file to the private Supabase bucket.
        Returns the internal path of the uploaded file.
        """
        try:
            # Upsert ensures we overwrite if a file with the same name exists
            res = self.client.storage.from_(self.bucket_name).upload(
                path,
                file_data,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            logger.info(f"Successfully uploaded file to {self.bucket_name}/{path}")
            return path
        except Exception as e:
            logger.error(f"Failed to upload file to Supabase: {e}")
            raise e

    def download_file(self, path: str) -> bytes:
        """
        Downloads a file directly from the private Supabase bucket.
        Returns the raw bytes of the file.
        """
        try:
            res = self.client.storage.from_(self.bucket_name).download(path)
            return res
        except Exception as e:
            logger.error(f"Failed to download file from Supabase: {e}")
            raise e

    def create_signed_download_url(self, path: str, expires_in: int = 60) -> str:
        """
        Generates a signed URL for a file in the private bucket.
        expires_in is the number of seconds the URL remains valid.
        """
        try:
            res = self.client.storage.from_(self.bucket_name).create_signed_url(path, expires_in)
            # Depending on supabase-py version, res is either a string or dict
            if isinstance(res, dict) and "signedURL" in res:
                return res["signedURL"]
            elif hasattr(res, "get") and res.get("signedURL"):
                return res.get("signedURL")
            elif isinstance(res, str):
                return res
            raise Exception("No signedURL found in Supabase response.")
        except Exception as e:
            logger.error(f"Failed to generate signed URL for {path}: {e}")
            raise e

# Create a global instance
storage_client = SupabaseStorageClient()
