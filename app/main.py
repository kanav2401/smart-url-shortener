from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO

import qrcode

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password
)
from .database import Base, engine, get_db
from .models import Click, URL, User
from .schemas import (
    AnalyticsResponse,
    BrowserStats,
    ClickResponse,
    DailyClickStats,
    ReferrerStats,
    URLCreate,
    URLResponse,
    UserLogin,
    UserRegister,
    UserResponse
)
from .utils import generate_short_code


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------

app = FastAPI(
    title="Smart URL Shortener",
    description="A URL shortening and analytics platform",
    version="1.0.0"
)


# ---------------------------------------------------------
# STATIC FILES
# ---------------------------------------------------------

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def get_utc_now():
    """
    Return the current UTC time as a timezone-aware datetime.
    """
    return datetime.now(timezone.utc)


def normalize_datetime(value):
    """
    Convert a datetime to a timezone-naive UTC datetime.

    SQLite is commonly used with naive datetime values in this
    project, so this keeps stored/comparison values consistent.
    """

    if value is None:
        return None

    if value.tzinfo is not None:
        return value.astimezone(
            timezone.utc
        ).replace(tzinfo=None)

    return value


def validate_expiration(expires_at):
    """
    Make sure an expiration date is in the future.
    """

    if expires_at is None:
        return None

    normalized_expiration = normalize_datetime(
        expires_at
    )

    current_time = datetime.utcnow()

    if normalized_expiration <= current_time:
        raise HTTPException(
            status_code=400,
            detail="Expiration date must be in the future"
        )

    return normalized_expiration


# ---------------------------------------------------------
# FRONTEND PAGES
# ---------------------------------------------------------

@app.get("/")
def home():
    return FileResponse(
        "static/index.html"
    )


@app.get("/login")
def login_page():
    return FileResponse(
        "static/login.html"
    )


@app.get("/register")
def register_page():
    return FileResponse(
        "static/register.html"
    )


@app.get("/analytics/{short_code}")
def analytics_page(short_code: str):
    return FileResponse(
        "static/analytics.html"
    )


# ---------------------------------------------------------
# AUTHENTICATION - REGISTER
# ---------------------------------------------------------

@app.post(
    "/api/auth/register",
    response_model=UserResponse,
    status_code=201
)
def register_user(
    data: UserRegister,
    db: Session = Depends(get_db)
):

    name = data.name.strip()
    email = data.email.lower().strip()

    # Extra backend validation
    if not name:
        raise HTTPException(
            status_code=400,
            detail="Name cannot be empty"
        )

    if len(name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Name must be at least 2 characters long"
        )

    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email is already registered"
        )

    if len(data.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters long"
        )

    try:

        new_user = User(
            name=name,
            email=email,
            hashed_password=hash_password(
                data.password
            )
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    except IntegrityError:

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Email is already registered"
        )

    return UserResponse(
        id=new_user.id,
        name=new_user.name,
        email=new_user.email,
        created_at=new_user.created_at
    )


# ---------------------------------------------------------
# AUTHENTICATION - LOGIN
# ---------------------------------------------------------

@app.post("/api/auth/login")
def login_user(
    data: UserLogin,
    db: Session = Depends(get_db)
):

    email = data.email.lower().strip()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email
        }
    )

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }


# ---------------------------------------------------------
# AUTHENTICATION - CURRENT USER
# ---------------------------------------------------------

@app.get(
    "/api/auth/me",
    response_model=UserResponse
)
def get_me(
    current_user: User = Depends(
        get_current_user
    )
):

    return UserResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        created_at=current_user.created_at
    )


# ---------------------------------------------------------
# CREATE SHORT URL
# ---------------------------------------------------------

@app.post(
    "/api/urls",
    response_model=URLResponse
)
def create_url(
    data: URLCreate,
    request: Request,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Validate expiration
    # -----------------------------------------------------

    expires_at = validate_expiration(
        data.expires_at
    )

    # -----------------------------------------------------
    # Validate custom short code
    # -----------------------------------------------------

    custom_code = None

    if data.custom_code:

        custom_code = data.custom_code.strip()

        if custom_code:

            if len(custom_code) < 3:
                raise HTTPException(
                    status_code=400,
                    detail="Custom code must be at least 3 characters long"
                )

            if len(custom_code) > 50:
                raise HTTPException(
                    status_code=400,
                    detail="Custom code must not exceed 50 characters"
                )

            existing = (
                db.query(URL)
                .filter(
                    URL.short_code == custom_code
                )
                .first()
            )

            if existing:
                raise HTTPException(
                    status_code=409,
                    detail="Custom code already exists"
                )

    # -----------------------------------------------------
    # Generate short code
    # -----------------------------------------------------

    if custom_code:

        short_code = custom_code

    else:

        short_code = generate_short_code()

        # Make sure generated code is unique
        while (
            db.query(URL)
            .filter(
                URL.short_code == short_code
            )
            .first()
        ):
            short_code = generate_short_code()

    # -----------------------------------------------------
    # Create URL
    # -----------------------------------------------------

    new_url = URL(
        user_id=current_user.id,
        original_url=str(data.original_url),
        short_code=short_code,
        expires_at=expires_at
    )

    try:

        db.add(new_url)
        db.commit()
        db.refresh(new_url)

    except IntegrityError:

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Short code already exists. Please choose another custom code."
        )

    # -----------------------------------------------------
    # Generate response URL
    # -----------------------------------------------------

    short_url = (
        f"{request.base_url}{short_code}"
    )

    return URLResponse(
        original_url=new_url.original_url,
        short_code=new_url.short_code,
        short_url=short_url,
        created_at=new_url.created_at,
        expires_at=new_url.expires_at,
        clicks=new_url.clicks
    )


# ---------------------------------------------------------
# GET USER URLS
# ---------------------------------------------------------

@app.get("/api/urls")
def get_urls(
    request: Request,
    page: int = 1,
    limit: int = 10,
    search: str | None = None,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Pagination validation
    # -----------------------------------------------------

    if page < 1:

        raise HTTPException(
            status_code=400,
            detail="Page must be greater than 0"
        )

    if limit < 1 or limit > 100:

        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100"
        )

    # -----------------------------------------------------
    # User-specific query
    # -----------------------------------------------------

    query = (
        db.query(URL)
        .filter(
            URL.user_id == current_user.id
        )
    )

    # -----------------------------------------------------
    # Search
    # -----------------------------------------------------

    if search:

        search_value = search.strip()

        if search_value:

            search_term = (
                f"%{search_value}%"
            )

            query = query.filter(
                URL.original_url.ilike(
                    search_term
                )
                |
                URL.short_code.ilike(
                    search_term
                )
            )

    # -----------------------------------------------------
    # Count
    # -----------------------------------------------------

    total = query.count()

    total_pages = (
        (total + limit - 1) // limit
    )

    # -----------------------------------------------------
    # Pagination
    # -----------------------------------------------------

    offset = (
        (page - 1) * limit
    )

    urls = (
        query
        .order_by(
            URL.created_at.desc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "results": [
            {
                "original_url": url.original_url,
                "short_code": url.short_code,
                "short_url": (
                    f"{request.base_url}"
                    f"{url.short_code}"
                ),
                "created_at": url.created_at,
                "expires_at": url.expires_at,
                "clicks": url.clicks
            }
            for url in urls
        ]
    }


# ---------------------------------------------------------
# ANALYTICS
# ---------------------------------------------------------

@app.get(
    "/api/urls/{short_code}/analytics",
    response_model=AnalyticsResponse
)
def get_analytics(
    short_code: str,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Find URL belonging to current user
    # -----------------------------------------------------

    url = (
        db.query(URL)
        .filter(
            URL.short_code == short_code,
            URL.user_id == current_user.id
        )
        .first()
    )

    if not url:

        raise HTTPException(
            status_code=404,
            detail="Short URL not found"
        )

    # -----------------------------------------------------
    # Get clicks
    # -----------------------------------------------------

    clicks = (
        db.query(Click)
        .filter(
            Click.url_id == url.id
        )
        .order_by(
            Click.clicked_at.desc()
        )
        .all()
    )

    # -----------------------------------------------------
    # Browser statistics
    # -----------------------------------------------------

    browser_counts = {}

    for click in clicks:

        user_agent = (
            click.user_agent
            or "Unknown"
        )

        if "Edg" in user_agent:

            browser = "Microsoft Edge"

        elif (
            "OPR" in user_agent
            or "Opera" in user_agent
        ):

            browser = "Opera"

        elif "Chrome" in user_agent:

            browser = "Google Chrome"

        elif "Firefox" in user_agent:

            browser = "Mozilla Firefox"

        elif "Safari" in user_agent:

            browser = "Safari"

        else:

            browser = "Other"

        browser_counts[browser] = (
            browser_counts.get(
                browser,
                0
            ) + 1
        )

    # -----------------------------------------------------
    # Referrer statistics
    # -----------------------------------------------------

    referrer_counts = {}

    for click in clicks:

        referrer = (
            click.referrer
            or "Direct"
        )

        referrer_counts[referrer] = (
            referrer_counts.get(
                referrer,
                0
            ) + 1
        )

    # -----------------------------------------------------
    # Daily click statistics
    # -----------------------------------------------------

    daily_counts = defaultdict(int)

    for click in clicks:

        date = click.clicked_at.strftime(
            "%Y-%m-%d"
        )

        daily_counts[date] += 1

    # -----------------------------------------------------
    # Browser response
    # -----------------------------------------------------

    browsers = [
        BrowserStats(
            browser=browser,
            clicks=count
        )
        for browser, count
        in browser_counts.items()
    ]

    # -----------------------------------------------------
    # Referrer response
    # -----------------------------------------------------

    referrers = [
        ReferrerStats(
            referrer=referrer,
            clicks=count
        )
        for referrer, count
        in referrer_counts.items()
    ]

    # -----------------------------------------------------
    # Daily clicks response
    # -----------------------------------------------------

    daily_clicks = [
        DailyClickStats(
            date=date,
            clicks=count
        )
        for date, count
        in sorted(
            daily_counts.items()
        )
    ]

    # -----------------------------------------------------
    # Final analytics response
    # -----------------------------------------------------

    return AnalyticsResponse(
        short_code=url.short_code,
        original_url=url.original_url,
        total_clicks=url.clicks,
        created_at=url.created_at,
        expires_at=url.expires_at,

        clicks=[
            ClickResponse(
                id=click.id,
                ip_address=click.ip_address,
                user_agent=click.user_agent,
                referrer=click.referrer,
                clicked_at=click.clicked_at
            )
            for click in clicks
        ],

        browsers=browsers,

        referrers=referrers,

        daily_clicks=daily_clicks
    )


# ---------------------------------------------------------
# QR CODE
# ---------------------------------------------------------

@app.get("/api/qr/{short_code}")
def generate_qr_code(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db)
):

    url = (
        db.query(URL)
        .filter(
            URL.short_code == short_code
        )
        .first()
    )

    if not url:

        raise HTTPException(
            status_code=404,
            detail="Short URL not found"
        )

    # -----------------------------------------------------
    # Check expiration
    # -----------------------------------------------------

    if url.expires_at:

        expiration = normalize_datetime(
            url.expires_at
        )

        if datetime.utcnow() > expiration:

            raise HTTPException(
                status_code=410,
                detail="This short URL has expired"
            )

    # -----------------------------------------------------
    # Create QR
    # -----------------------------------------------------

    short_url = (
        f"{request.base_url}{short_code}"
    )

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )

    qr.add_data(short_url)
    qr.make(fit=True)

    image = qr.make_image()

    image_bytes = BytesIO()

    image.save(
        image_bytes,
        format="PNG"
    )

    image_bytes.seek(0)

    return StreamingResponse(
        image_bytes,
        media_type="image/png"
    )


# ---------------------------------------------------------
# DELETE URL
# ---------------------------------------------------------

@app.delete(
    "/api/urls/{short_code}"
)
def delete_url(
    short_code: str,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Find URL belonging to current user
    # -----------------------------------------------------

    url = (
        db.query(URL)
        .filter(
            URL.short_code == short_code,
            URL.user_id == current_user.id
        )
        .first()
    )

    if not url:

        raise HTTPException(
            status_code=404,
            detail="Short URL not found"
        )

    # -----------------------------------------------------
    # Delete click records
    # -----------------------------------------------------

    db.query(Click).filter(
        Click.url_id == url.id
    ).delete()

    # -----------------------------------------------------
    # Delete URL
    # -----------------------------------------------------

    db.delete(url)

    db.commit()

    return {
        "message": "Short URL deleted successfully",
        "short_code": short_code
    }


# ---------------------------------------------------------
# PUBLIC SHORT URL REDIRECT
# ---------------------------------------------------------

@app.get("/{short_code}")
def redirect_url(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Find URL
    # -----------------------------------------------------

    url = (
        db.query(URL)
        .filter(
            URL.short_code == short_code
        )
        .first()
    )

    if not url:

        raise HTTPException(
            status_code=404,
            detail="Short URL not found"
        )

    # -----------------------------------------------------
    # Check expiration
    # -----------------------------------------------------

    if url.expires_at:

        expiration = normalize_datetime(
            url.expires_at
        )

        if datetime.utcnow() > expiration:

            raise HTTPException(
                status_code=410,
                detail="This short URL has expired"
            )

    # -----------------------------------------------------
    # Increment click count
    # -----------------------------------------------------

    url.clicks += 1

    # -----------------------------------------------------
    # Record click
    # -----------------------------------------------------

    click = Click(
        url_id=url.id,

        ip_address=(
            request.client.host
            if request.client
            else None
        ),

        user_agent=request.headers.get(
            "user-agent"
        ),

        referrer=request.headers.get(
            "referer"
        )
    )

    db.add(click)

    db.commit()

    # -----------------------------------------------------
    # Redirect
    # -----------------------------------------------------

    return RedirectResponse(
        url=url.original_url,
        status_code=307
    )