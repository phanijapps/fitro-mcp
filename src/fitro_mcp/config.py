"""Environment configuration with secret redaction and fixed upstream origins."""

import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator

from fitro_mcp.errors import BridgeError


class Settings(BaseModel):
    """Validated runtime settings; credentials are excluded from representations."""

    model_config = ConfigDict(frozen=True)
    api_key: SecretStr = Field(repr=False)
    region: Literal["global", "china"] = "global"
    timeout_seconds: float = Field(default=30, ge=1, le=120)
    max_response_bytes: int = Field(default=8 * 1024 * 1024, ge=1024, le=32 * 1024 * 1024)

    @field_validator("api_key")
    @classmethod
    def validate_key(cls, value: SecretStr) -> SecretStr:
        """Reject empty keys and header control characters."""
        raw = value.get_secret_value()
        if not raw.strip() or any(ord(char) < 33 or ord(char) > 126 for char in raw):
            raise ValueError("API key must be nonempty printable ASCII without whitespace")
        return value

    @property
    def base_url(self) -> str:
        """Return only the official regional HTTPS API origin."""
        suffix = "cn" if self.region == "china" else "com"
        return f"https://personal.connectapi.garmin.{suffix}"

    @classmethod
    def from_env(cls) -> "Settings":
        """Read explicitly supported environment variables, without loading files."""
        try:
            return cls(
                api_key=SecretStr(os.environ.get("GARMIN_PERSONAL_API_KEY", "")),
                region=os.environ.get("FITRO_REGION", "global"),  # type: ignore[arg-type]
                timeout_seconds=float(os.environ.get("FITRO_TIMEOUT_SECONDS", "30")),
                max_response_bytes=int(
                    os.environ.get("FITRO_MAX_RESPONSE_BYTES", str(8 * 1024 * 1024))
                ),
            )
        except (ValidationError, ValueError):
            raise BridgeError(
                "Invalid configuration. Set GARMIN_PERSONAL_API_KEY "
                "and check the documented settings."
            ) from None
