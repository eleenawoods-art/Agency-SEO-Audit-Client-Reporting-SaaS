from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag
import requests

UA = "Agency-SEO-Auditor/6.0 (+https://streamlit.io)"


def normalize_url(url):
    url = str(url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _same_site(a, b):
    return urlparse(a).netloc.lower().split(":")[0] == urlparse(b).netloc.lower().split(":")[0]


def _fetch(url, timeout=15):
    return requests.get(
        url,
        headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"},
        timeout=timeout,
        allow_redirects=True,
    )


def crawl_website(start_url, max_pages=10, timeout=15):
    start_url = normalize_url(start_url)
    if not start_url:
        return []

    queue = deque([start_url])
    queued = {start_url}
    visited = set()
    pages = []

    while queue and len(pages) < max(1, int(max_pages)):
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)

        try:
            response = _fetch(current, timeout)
            final_url = urldefrag(response.url)[0]
            if not _same_site(start_url, final_url):
                continue

            content_type = response.headers.get("content-type", "").lower()
            html = response.text if ("html" in content_type or "xhtml" in content_type or not content_type) else ""

            page = {
                "url": final_url,
                "html": html,
                "status": response.status_code,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_type": content_type,
            }
            pages.append(page)

            if not html:
                continue

            # Lightweight link extraction without making crawler dependent on BeautifulSoup.
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup.find_all("a", href=True):
                href = str(tag.get("href") or "").strip()
                if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                    continue
                target = urldefrag(urljoin(final_url, href))[0]
                parsed = urlparse(target)
                if parsed.scheme in ("http", "https") and _same_site(start_url, target) and target not in queued:
                    if len(queued) < max_pages * 4:
                        queued.add(target)
                        queue.append(target)
        except requests.RequestException:
            # Keep a page record so the UI can show that the URL was unreachable.
            pages.append({"url": current, "html": "", "status": None, "status_code": None, "headers": {}, "error": "Request failed"})
        except Exception as exc:
            pages.append({"url": current, "html": "", "status": None, "status_code": None, "headers": {}, "error": str(exc)})

    return pages[:max_pages]
