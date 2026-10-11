"""Report photos in S3: `reports/{run_id}/{report_id}.jpg` (contracts/storage.md).

The app uploads straight to S3 with a presigned PUT, so photos never pass through a Lambda.
"""

import os
from typing import Any, Protocol

BUCKET_ENV = "NIMBUS_BUCKET_PHOTOS"
UPLOAD_SECONDS = 300
CONTENT_TYPE = "image/jpeg"


def photo_key(run_id: str, report_id: str) -> str:
    return f"reports/{run_id}/{report_id}.jpg"


class Photos(Protocol):
    def upload_url(self, key: str) -> str: ...
    def exists(self, key: str) -> bool: ...


class MemoryPhotos:
    def __init__(self) -> None:
        self.uploaded: set[str] = set()

    def upload_url(self, key: str) -> str:
        return f"https://photos.example/{key}?signature=test"

    def exists(self, key: str) -> bool:
        return key in self.uploaded


class S3Photos:
    """`client` is a boto3 "s3" client; the bucket name comes from NIMBUS_BUCKET_PHOTOS."""

    def __init__(self, bucket: str | None = None, client: Any = None) -> None:
        self.bucket = bucket or os.environ[BUCKET_ENV]
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            import boto3

            self._client = boto3.client("s3")
        return self._client

    def upload_url(self, key: str) -> str:
        # ContentType is part of the signature, so only a JPEG upload with that header is accepted.
        return self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": key, "ContentType": CONTENT_TYPE},
            ExpiresIn=UPLOAD_SECONDS,
        )

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise
