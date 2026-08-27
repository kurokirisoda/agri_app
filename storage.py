import os
import uuid
from werkzeug.utils import secure_filename
import requests

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")


def _local_save(file_storage):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(secure_filename(file_storage.filename))[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    file_storage.save(os.path.join(UPLOAD_DIR, filename))
    return f"/static/uploads/{filename}"


def _supabase_save(file_storage, supabase_url, supabase_key, bucket):
    ext = os.path.splitext(secure_filename(file_storage.filename))[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    data = file_storage.read()
    upload_url = f"{supabase_url}/storage/v1/object/{bucket}/{filename}"
    res = requests.post(
        upload_url,
        headers={
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": file_storage.content_type or "application/octet-stream",
        },
        data=data,
        timeout=15,
    )
    res.raise_for_status()
    return f"{supabase_url}/storage/v1/object/public/{bucket}/{filename}"


def save_photo(file_storage, supabase_url=None, supabase_key=None, supabase_bucket=None):
    if not file_storage or not file_storage.filename:
        return None
    if supabase_url and supabase_key and supabase_bucket:
        return _supabase_save(file_storage, supabase_url, supabase_key, supabase_bucket)
    return _local_save(file_storage)
