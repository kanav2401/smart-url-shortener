from datetime import datetime
from io import BytesIO

import qrcode

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Click, URL
from .schemas import (
    AnalyticsResponse,
    BrowserStats,
    ClickResponse,
    ReferrerStats,
    URLCreate,
    URLResponse
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


@app.get("/analytics/{short_code}")
def analytics_page(short_code: str):
    return FileResponse("static/analytics.html")


@app.post("/api/urls", response_model=URLResponse)
def create_url(
    data: URLCreate,
    request: Request,
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

    query = db.query(URL)

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
        elif "Chrome" in user_agent:
            browser = "Google Chrome"
        elif "Firefox" in user_agent:
            browser = "Mozilla Firefox"
        elif "Safari" in user_agent:
            browser = "Safari"
        elif "Opera" in user_agent:
            browser = "Opera"
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
        referrers=referrers
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