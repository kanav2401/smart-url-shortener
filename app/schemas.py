from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator


class URLCreate(BaseModel):

    original_url: HttpUrl

    custom_code: str | None = Field(
        default=None,
        min_length=3,
        max_length=50
    )

    expires_at: datetime | None = None

    @field_validator("custom_code")
    @classmethod
    def validate_custom_code(cls, value):
        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        if not value.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Custom code can only contain letters, numbers, hyphens, and underscores"
            )

        return value

    @field_validator("expires_at")
    @classmethod
    def validate_expiration(cls, value):
        if value is None:
            return None

        if value <= datetime.now(value.tzinfo):
            raise ValueError(
                "Expiration date must be in the future"
            )

        return value


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


class UserRegister(BaseModel):

    name: str = Field(
        min_length=2,
        max_length=100
    )

    email: EmailStr

    password: str = Field(
        min_length=6,
        max_length=100
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        value = value.strip()

        if not value:
            raise ValueError(
                "Name cannot be empty"
            )

        return value


class UserLogin(BaseModel):

    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=100
    )


class UserResponse(BaseModel):

    id: int

    name: str

    email: str

    created_at: datetime