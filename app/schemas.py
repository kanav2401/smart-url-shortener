from datetime import datetime

from pydantic import BaseModel, HttpUrl


class URLCreate(BaseModel):
    original_url: HttpUrl
    custom_code: str | None = None
    expires_at: datetime | None = None


class ClickResponse(BaseModel):
    id: int
    ip_address: str | None
    user_agent: str | None
    referrer: str | None
    clicked_at: datetime


class BrowserStats(BaseModel):
    browser: str
    clicks: int


class ReferrerStats(BaseModel):
    referrer: str
    clicks: int


class DailyClickStats(BaseModel):
    date: str
    clicks: int


class URLResponse(BaseModel):
    original_url: str
    short_code: str
    short_url: str
    created_at: datetime
    expires_at: datetime | None
    clicks: int


class AnalyticsResponse(BaseModel):
    short_code: str
    original_url: str
    total_clicks: int
    created_at: datetime
    expires_at: datetime | None
    clicks: list[ClickResponse]
    browsers: list[BrowserStats]
    referrers: list[ReferrerStats]
    daily_clicks: list[DailyClickStats]