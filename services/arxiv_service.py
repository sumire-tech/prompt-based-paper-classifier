import re
from datetime import datetime

import arxiv


ARXIV_ID_RE = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf)/)([^/?#]+)",
    re.IGNORECASE,
)


def extract_arxiv_id(url: str) -> str:
    match = ARXIV_ID_RE.search(url.strip())
    if not match:
        raise ValueError("有効なarXiv URLではありません。")
    arxiv_id = match.group(1)
    if arxiv_id.endswith(".pdf"):
        arxiv_id = arxiv_id[:-4]
    return arxiv_id


def fetch_paper(url: str) -> dict:
    arxiv_id = extract_arxiv_id(url)

    client = arxiv.Client(
        page_size=1,
        delay_seconds=3.0,
        num_retries=3,
    )

    search = arxiv.Search(id_list=[arxiv_id])
    result = next(client.results(search), None)

    if result is None:
        raise ValueError(f"arXiv論文が見つかりません: {arxiv_id}")

    return {
        "arxiv_id": arxiv_id,
        "title": " ".join(result.title.split()),
        "abstract": " ".join(result.summary.split()),
        "authors": ", ".join(a.name for a in result.authors),
        "published_at": result.published,
        "updated_at": result.updated,
        "url": result.entry_id,
    }
