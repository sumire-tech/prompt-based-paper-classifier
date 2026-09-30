from typesafe_sdk import Choice, TypeSafeClient

from db import settings


def classify_paper(
    title: str,
    abstract: str,
    categories: dict[str, dict[str, str]],
) -> dict:
    if not settings.typesafe_api_key:
        raise RuntimeError("TYPESAFE_API_KEY が設定されていません。")

    if not categories:
        raise ValueError("分類カテゴリがありません。")

    if len(categories) > 255:
        raise ValueError("JevのChoiceカテゴリ上限255を超えています。")

    criteria = {
        category_id: f"{data['name']}: {data['description']}"
        for category_id, data in categories.items()
    }

    state = {
        "title": title,
        "abstract": abstract,
    }

    with TypeSafeClient(api_key=settings.typesafe_api_key) as client:
        response = client.system_one(
            state=state,
            questions={
                "category": Choice(
                    instructions=(
                        "この論文が最も該当する研究カテゴリを1つ選択してください。"
                        "タイトルだけでなくabstract全体を考慮してください。"
                        "カテゴリの説明に明示的に合致する研究内容を優先してください。"
                    ),
                    criteria=criteria,
                )
            },
        )

    answer = response.choices["category"]

    return {
        "category": answer.choice,
        "confidence": answer.confidence,
        "probabilities": answer.probabilities,
        "model": getattr(response, "model", "jev-latest"),
    }
