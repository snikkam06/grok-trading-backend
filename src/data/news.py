from duckduckgo_search import DDGS
from datetime import datetime

class NewsData:
    def __init__(self):
        self.ddgs = DDGS()

    def get_news(self, date: datetime) -> str:
        """Fetch general market news headlines for a specific date using duckduckgo."""
        query = f"stock market news {date.strftime('%Y-%m-%d')}"
        try:
            results = self.ddgs.text(query, max_results=5)
            news_items = [f"- {r['title']}: {r['body']}" for r in results]
            return "\n".join(news_items) if news_items else "No news found for this date."
        except Exception as e:
            return f"Error fetching news: {e}"

    def search_web(self, query: str) -> str:
        """Perform a general web search."""
        try:
            print(f"  > Searching web for: '{query}'...")
            results = self.ddgs.text(query, max_results=5)
            search_items = [f"- {r['title']}: {r['body']}" for r in results]
            return "\n".join(search_items) if search_items else "No results found."
        except Exception as e:
            return f"Error during search: {e}"
