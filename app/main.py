from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Click, URL
from .schemas import AnalyticsResponse, URLCreate, URLResponse
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

    return AnalyticsResponse(
        short_code=url.short_code,
        original_url=url.original_url,
        total_clicks=url.clicks,
        created_at=url.created_at,
        expires_at=url.expires_at
    )


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
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer")
    )

    db.add(click)
    db.commit()

    return RedirectResponse(
        url=url.original_url,
        status_code=307
    )
    