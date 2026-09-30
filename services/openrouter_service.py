import json

from openai import OpenAI

from db import settings


def _client() -> OpenAI:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY が設定されていません。")

    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )


def generate_categories(titles: list[str], user_prompt: str = "") -> dict:
    if not titles:
        raise ValueError("論文タイトルがありません。")

    prompt = f"""あなたは論文管理システムの分類体系設計者です。

以下の論文タイトルだけを使って、これらを分類するためのカテゴリ体系を作成してください。

要件:
- 論文タイトルから読み取れる研究内容の違いをカテゴリにする
- カテゴリ数は論文数と内容の多様性に応じて決める
- カテゴリ名は短くする
- 各カテゴリに、そのカテゴリに含める論文の条件を日本語で説明する
- カテゴリ同士の重複をできるだけ避ける
- 著者名や単なる固有名詞をカテゴリそのものにしない
- すべての論文を少なくとも1カテゴリに割り当てられる体系にする

ユーザーからの追加指示:
{user_prompt or "なし"}

論文タイトル:
""" + "\n".join(
        f"{i + 1}. {title}" for i, title in enumerate(titles)
    )

    response = _client().chat.completions.create(
        model=settings.openrouter_model,
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "category_set",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "categories": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                },
                                "required": ["id", "name", "description"],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["categories"],
                    "additionalProperties": False,
                },
            },
        },
        messages=[
            {
                "role": "system",
                "content": "出力は指定されたJSON Schemaだけに従ってください。",
            },
            {"role": "user", "content": prompt},
        ],
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenRouterからカテゴリが返されませんでした。")

    data = json.loads(content)
    categories = data.get("categories", [])

    if not categories:
        raise RuntimeError("カテゴリが1つも生成されませんでした。")

    if len(categories) > 255:
        raise RuntimeError(
            f"カテゴリ数がJevの上限255を超えています: {len(categories)}"
        )

    # Jevのcriteriaは「ID -> 説明」なので、DBには表示名も残す。
    return {
        "categories": {
            item["id"]: {
                "name": item["name"],
                "description": item["description"],
            }
            for item in categories
        }
    }
