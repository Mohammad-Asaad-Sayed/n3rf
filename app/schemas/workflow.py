from typing import Any

import httpx
from pydantic import BaseModel, Field, field_validator


class RunRequest(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]] = Field(default_factory=list)
    input_override: list[dict[str, Any]] | None = None
    target_node_id: str | None = None
    test_rows: int | None = None


class WorkflowRequest(BaseModel):
    name: str = "Untitled workflow"
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


class ModelProfileRequest(BaseModel):
    id: str | None = None
    name: str = Field(min_length=1, max_length=80)
    base_url: str = Field(min_length=1, max_length=500)
    model: str = Field(min_length=1, max_length=160)
    api_key_env: str = Field(default="OPENAI_API_KEY", max_length=120)
    # Ephemeral BYOK: accepted so a connection test can use a pasted key for
    # that one request. It is never stored (see store.save_model_profile) and
    # never echoed — profiles only persist the env-var name above.
    api_key: str = Field(default="", max_length=1000)

    @field_validator("name", "base_url", "model", "api_key_env", "api_key")
    @classmethod
    def strip_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("name", "base_url", "model")
    @classmethod
    def reject_blank_fields(cls, value: str) -> str:
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        try:
            url = httpx.URL(value)
        except httpx.InvalidURL as exc:
            raise ValueError("Base URL must be an absolute HTTP or HTTPS URL.") from exc
        if (
            url.scheme not in {"http", "https"}
            or not url.host
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError(
                "Base URL must be HTTP or HTTPS without embedded credentials or query values."
            )
        return value
