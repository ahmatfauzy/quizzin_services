import cloudinary.uploader
import cloudinary
from config.settings import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)


def upload_pdf(file_bytes, user_id: int, filename: str) -> dict:
    result = cloudinary.uploader.upload(
        file_bytes,
        resource_type="raw",
        folder="quizzin/documents",
        public_id=f"doc_{user_id}",
        filename=filename,
    )
    return {
        "secure_url": result.get("secure_url"),
        "public_id": result.get("public_id"),
    }


def upload_avatar(file_bytes) -> str:
    result = cloudinary.uploader.upload(
        file_bytes,
        resource_type="image",
        folder="quizzin/avatars",
        transformation=[{"width": 256, "height": 256, "crop": "fill"}],
    )
    return result.get("secure_url")


def delete_file(public_id: str, resource_type: str = "raw"):
    try:
        cloudinary.uploader.destroy(public_id, resource_type=resource_type)
    except Exception:
        pass
