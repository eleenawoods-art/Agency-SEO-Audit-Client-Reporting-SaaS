import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque


HEADERS = {
    "User-Agent": "AgencySEOAuditor/1.0 (+SEO Audit Tool)"
}


def normalize_url(url):
    url = url.strip()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    return url.rstrip("/")


def get_page(url, timeout=15):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True
        )

        return {
            "success": True,
            "status": response.status_code,
            "url": response.url,
            "html": response.text,
            "headers": dict(response.headers)
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "status": None,
            "url": url,
            "html": "",
            "headers": {},
            "error": str(e)
        }


def crawl_website(start_url, max_pages=10):
    start_url = normalize_url(start_url)

    parsed_start = urlparse(start_url)
    domain = parsed_start.netloc.lower()

    queue = deque([start_url])
    visited = set()
    pages = []

    while queue and len(pages) < max_pages:

        current = queue.popleft()

        if current in visited:
            continue

        visited.add(current)

        result = get_page(current)

        if not result["success"]:
            continue

        soup = BeautifulSoup(result["html"], "html.parser")

        page_data = {
            "url": result["url"],
            "status": result["status"],
            "html": result["html"],
            "headers": result["headers"],
            "title": soup.title.get_text(strip=True)
            if soup.title else ""
        }

        pages.append(page_data)

        for link in soup.find_all("a", href=True):

            href = link.get("href").strip()

            if href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue

            absolute = urljoin(result["url"], href)
            parsed = urlparse(absolute)

            if parsed.scheme not in ("http", "https"):
                continue

            if parsed.netloc.lower() != domain:
                continue

            clean_url = absolute.split("#")[0].rstrip("/")

            if clean_url not in visited:
                queue.append(clean_url)

    return pages


def check_url(url, timeout=10):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True
        )

        return {
            "url": url,
            "status": response.status_code,
            "working": 200 <= response.status_code < 400
        }

    except requests.RequestException:
        return {
            "url": url,
            "status": None,
            "working": False
        }
