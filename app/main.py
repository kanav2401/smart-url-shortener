from collections import defaultdict
from datetime import datetime
from io import BytesIO

import qrcode

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
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


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Smart URL Shortener",
    description="A URL shortening and analytics platform",
    version="1.0.0"
)


app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.get("/login")
def login_page():
    return FileResponse("static/login.html")


@app.get("/register")
def register_page():
    return FileResponse("static/register.html")


@app.get("/analytics/{short_code}")
def analytics_page(short_code: str):
    return FileResponse("static/analytics.html")


@app.post(
    "/api/auth/register",
    response_model=UserResponse,
    status_code=201
)
def register_user(
    data: UserRegister,
    db: Session = Depends(get_db)
):
    existing_user = (
        db.query(User)
        .filter(User.email == data.email.lower().strip())
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

    new_user = User(
        name=data.name.strip(),
        email=data.email.lower().strip(),
        hashed_password=hash_password(data.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        name=new_user.name,
        email=new_user.email,
        created_at=new_user.created_at
    )


@app.post("/api/auth/login")
def login_user(
    data: UserLogin,
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.email == data.email.lower().strip())
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


@app.get("/api/auth/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user)
):
    return UserResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        created_at=current_user.created_at
    )


@app.post("/api/urls", response_model=URLResponse)
def create_url(
    data: URLCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if data.custom_code:
        existing = (
            db.query(URL)
            .filter(URL.short_code == data.custom_code)
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Custom code already exists"
            )

        short_code = data.custom_code

    else:
        short_code = generate_short_code()

        while (
            db.query(URL)
            .filter(URL.short_code == short_code)
            .first()
        ):
            short_code = generate_short_code()

    new_url = URL(
        user_id=current_user.id,
        original_url=str(data.original_url),
        short_code=short_code,
        expires_at=data.expires_at
    )

    db.add(new_url)
    db.commit()
    db.refresh(new_url)

    short_url = f"{request.base_url}{short_code}"

    return URLResponse(
        original_url=new_url.original_url,
        short_code=new_url.short_code,
        short_url=short_url,
        created_at=new_url.created_at,
        expires_at=new_url.expires_at,
        clicks=new_url.clicks
    )


@app.get("/api/urls")
def get_urls(
    request: Request,
    page: int = 1,
    limit: int = 10,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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

    query = (
        db.query(URL)
        .filter(URL.user_id == current_user.id)
    )

    if search:
        search_term = f"%{search.strip()}%"

        query = query.filter(
            URL.original_url.ilike(search_term)
            | URL.short_code.ilike(search_term)
        )

    total = query.count()

    total_pages = (total + limit - 1) // limit

    offset = (page - 1) * limit

    urls = (
        query
        .order_by(URL.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "results": [
            {
                "original_url": url.original_url,
                "short_code": url.short_code,
                "short_url": f"{request.base_url}{url.short_code}",
                "created_at": url.created_at,
                "expires_at": url.expires_at,
                "clicks": url.clicks
            }
            for url in urls
        ]
    }


@app.get(
    "/api/urls/{short_code}/analytics",
    response_model=AnalyticsResponse
)
def get_analytics(
    short_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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

    clicks = (
        db.query(Click)
        .filter(Click.url_id == url.id)
        .order_by(Click.clicked_at.desc())
        .all()
    )

    browser_counts = {}

    for click in clicks:
        user_agent = click.user_agent or "Unknown"

        if "Edg" in user_agent:
            browser = "Microsoft Edge"
        elif "OPR" in user_agent or "Opera" in user_agent:
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
            browser_counts.get(browser, 0) + 1
        )

    referrer_counts = {}

    for click in clicks:
        referrer = click.referrer or "Direct"

        referrer_counts[referrer] = (
            referrer_counts.get(referrer, 0) + 1
        )

    daily_counts = defaultdict(int)

    for click in clicks:
        date = click.clicked_at.strftime("%Y-%m-%d")
        daily_counts[date] += 1

    browsers = [
        BrowserStats(
            browser=browser,
            clicks=count
        )
        for browser, count in browser_counts.items()
    ]

    referrers = [
        ReferrerStats(
            referrer=referrer,
            clicks=count
        )
        for referrer, count in referrer_counts.items()
    ]

    daily_clicks = [
        DailyClickStats(
            date=date,
            clicks=count
        )
        for date, count in sorted(daily_counts.items())
    ]

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


@app.get("/api/qr/{short_code}")
def generate_qr_code(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    url = (
        db.query(URL)
        .filter(URL.short_code == short_code)
        .first()
    )

    if not url:
        raise HTTPException(
            status_code=404,
            detail="Short URL not found"
        )

    short_url = f"{request.base_url}{short_code}"

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )

    qr.add_data(short_url)
    qr.make(fit=True)

    image = qr.make_image()

    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    image_bytes.seek(0)

    return StreamingResponse(
        image_bytes,
        media_type="image/png"
    )


@app.delete("/api/urls/{short_code}")
def delete_url(
    short_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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

    db.query(Click).filter(
        Click.url_id == url.id
    ).delete()

    db.delete(url)
    db.commit()

    return {
        "message": "Short URL deleted successfully",
        "short_code": short_code
    }


@app.get("/{short_code}")
def redirect_url(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    url = (
        db.query(URL)
        .filter(URL.short_code == short_code)
        .first()
    )

    if not url:
        raise HTTPException(
            status_code=404,
            detail="Short URL not found"
        )

    if url.expires_at and datetime.utcnow() > url.expires_at:
        raise HTTPException(
            status_code=410,
            detail="This short URL has expired"
        )

    url.clicks += 1

    click = Click(
        url_id=url.id,
        ip_address=request.client.host
        if request.client
        else None,
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer")
    )

    db.add(click)
    db.commit()

    return RedirectResponse(
        url=url.original_url,
        status_code=307
    )