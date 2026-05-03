import json
import logging

from profitist.config import settings

logger = logging.getLogger(__name__)


async def search(query: str, max_results: int = 5) -> str:
    if not settings.tavily_api_key:
        return "Web search недоступен: TAVILY_API_KEY не настроен."

    from tavily import AsyncTavilyClient

    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    response = await client.search(query, max_results=max_results)

    results = []
    for item in response.get("results", []):
        results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
            }
        )

    if not results:
        return f"По запросу '{query}' ничего не найдено."

    return json.dumps(results, ensure_ascii=False, indent=2)
