from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class URLCreate(BaseModel):
    original_url: HttpUrl
    custom_code: str | None = None
    expires_at: datetime | None = None


class URLResponse(BaseModel):
    original_url: str
    short_code: str
    short_url: str
    created_at: datetime
    expires_at: datetime | None
    clicks: int


class ClickResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    clicked_at: datetime
    ip_address: str | None
    user_agent: str | None
    referrer: str | None


class AnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    short_code: str
    original_url: str
    total_clicks: int
    created_at: datetime
    expires_at: datetime | None
    clicks: list[ClickResponse]