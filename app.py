from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import Base, SessionLocal, engine
from models import CategorySet, JevClassification, Paper
from services.arxiv_service import fetch_paper
from services.jev_service import classify_paper
from services.openrouter_service import generate_categories

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# NOTE:
# The import above is intentionally corrected below. This assignment makes
# the generated file fail fast if someone accidentally renames the service.

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Paper Manager + Jev")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ImportPaperRequest(BaseModel):
    url: str


class CategoryRequest(BaseModel):
    prompt: str = ""


class ClassifyRequest(BaseModel):
    category_set_id: int | None = None
    paper_ids: list[int] | None = None


@app.get("/papers")
def list_papers(db: Session = Depends(get_db)):
    papers = db.scalars(select(Paper).order_by(Paper.id)).all()
    return [
        {
            "id": p.id,
            "arxiv_id": p.arxiv_id,
            "title": p.title,
            "abstract": p.abstract,
            "url": p.url,
        }
        for p in papers
    ]


@app.post("/papers/import")
def import_paper(
    request: ImportPaperRequest,
    db: Session = Depends(get_db),
):
    try:
        data = fetch_paper(request.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    existing = db.scalar(
        select(Paper).where(Paper.arxiv_id == data["arxiv_id"])
    )

    if existing:
        return {"id": existing.id, "created": False, "paper": existing.title}

    paper = Paper(**data)
    db.add(paper)
    db.commit()
    db.refresh(paper)

    return {"id": paper.id, "created": True, "paper": paper.title}


@app.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(CategorySet).order_by(CategorySet.id.desc())
    ).all()

    return [
        {
            "id": row.id,
            "prompt": row.prompt,
            "categories": row.categories,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@app.post("/classify/categories")
def create_categories(
    request: CategoryRequest,
    db: Session = Depends(get_db),
):
    papers = db.scalars(select(Paper).order_by(Paper.id)).all()

    if not papers:
        raise HTTPException(status_code=400, detail="論文が登録されていません。")

    try:
        result = generate_categories(
            [paper.title for paper in papers],
            request.prompt,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    category_set = CategorySet(
        prompt=request.prompt,
        categories=result["categories"],
    )
    db.add(category_set)
    db.commit()
    db.refresh(category_set)

    return {
        "category_set_id": category_set.id,
        "categories": category_set.categories,
    }


@app.post("/classify/jev")
def classify_with_jev(
    request: ClassifyRequest,
    db: Session = Depends(get_db),
):
    if request.category_set_id is None:
        category_set = db.scalar(
            select(CategorySet).order_by(CategorySet.id.desc())
        )
    else:
        category_set = db.get(CategorySet, request.category_set_id)

    if category_set is None:
        raise HTTPException(
            status_code=400,
            detail="カテゴリセットがありません。先に /classify/categories を実行してください。",
        )

    if request.paper_ids:
        papers = db.scalars(
            select(Paper).where(Paper.id.in_(request.paper_ids))
        ).all()
    else:
        papers = db.scalars(select(Paper).order_by(Paper.id)).all()

    results = []

    for paper in papers:
        try:
            result = classify_paper(
                title=paper.title,
                abstract=paper.abstract,
                categories=category_set.categories,
            )
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"paper_id={paper.id}: {e}",
            ) from e

        classification = JevClassification(
            paper_id=paper.id,
            category_set_id=category_set.id,
            category=result["category"],
            confidence=result["confidence"],
            probabilities=result["probabilities"],
            model=result["model"],
        )
        db.add(classification)

        results.append(
            {
                "paper_id": paper.id,
                "title": paper.title,
                **result,
            }
        )

    db.commit()
    return {
        "category_set_id": category_set.id,
        "results": results,
    }
