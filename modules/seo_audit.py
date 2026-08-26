from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urldefrag, urlparse
import re
import requests
from bs4 import BeautifulSoup

UA = "Agency-SEO-Auditor/6.0"


def _request(url, method="GET", timeout=10):
    return requests.request(method, url, headers={"User-Agent": UA}, timeout=timeout, allow_redirects=True)


def _result(category, severity, issue, recommendation, url=""):
    return {"category": category, "severity": severity, "issue": issue, "recommendation": recommendation, "url": url}


def audit_page(page):
    if isinstance(page, str):
        return []
    if not isinstance(page, dict):
        return []

    url = str(page.get("url") or page.get("URL") or "")
    html = page.get("html") or ""
    if not html:
        return [_result("Technical SEO", "Critical", "Page could not be fetched", "Check that the page is publicly reachable and returns valid HTML.", url)]

    soup = BeautifulSoup(html, "html.parser")
    results = []

    # On-page
    title_tag = soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else ""
    if not title:
        results.append(_result("On-Page SEO", "Critical", "Missing title tag", "Add a unique, descriptive title tag, ideally around 30–60 characters.", url))
    elif len(title) < 30:
        results.append(_result("On-Page SEO", "Warning", "Title tag is too short", "Consider creating a more descriptive title.", url))
    elif len(title) > 60:
        results.append(_result("On-Page SEO", "Warning", "Title tag may be too long", "Keep the title concise, ideally around 30–60 characters.", url))
    else:
        results.append(_result("On-Page SEO", "Passed", "Title tag length is good", "No action needed.", url))

    desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    description = str(desc.get("content") or "").strip() if desc else ""
    if not description:
        results.append(_result("On-Page SEO", "Critical", "Missing meta description", "Add a unique meta description for this page.", url))
    elif len(description) > 160:
        results.append(_result("On-Page SEO", "Warning", "Meta description may be too long", "Keep the meta description around 70–160 characters.", url))
    elif len(description) < 70:
        results.append(_result("On-Page SEO", "Warning", "Meta description may be too short", "Expand the meta description so it clearly explains the page value.", url))
    else:
        results.append(_result("On-Page SEO", "Passed", "Meta description length is good", "No action needed.", url))

    h1s = soup.find_all("h1")
    if len(h1s) == 0:
        results.append(_result("Content", "Warning", "Missing H1 heading", "Add one clear primary H1 heading describing the page.", url))
    elif len(h1s) > 1:
        results.append(_result("Content", "Warning", "Multiple H1 headings", "Review the page structure and consider using one primary H1.", url))
    else:
        results.append(_result("Content", "Passed", "H1 structure is good", "No action needed.", url))

    # Images
    images = soup.find_all("img")
    missing_alt = [img.get("src", "") for img in images if not str(img.get("alt") or "").strip()]
    if images and missing_alt:
        results.append(_result("Image SEO", "Warning", f"{len(missing_alt)} images missing alt text", "Add meaningful alt text to informative images.", url))
    elif images:
        results.append(_result("Image SEO", "Passed", "Image alt text is present", "No action needed.", url))
    else:
        results.append(_result("Image SEO", "Passed", "No images found on this page", "No image ALT action is required for this page.", url))

    # Technical/mobile
    canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
    viewport = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
    if url.startswith("https://"):
        results.append(_result("Technical SEO", "Passed", "HTTPS is enabled", "No action needed.", url))
    else:
        results.append(_result("Technical SEO", "Critical", "HTTPS is not enabled", "Serve the website over HTTPS and redirect HTTP to HTTPS.", url))
    results.append(_result("Technical SEO", "Passed" if canonical else "Warning", "Canonical tag found" if canonical else "Canonical tag missing", "No action needed." if canonical else "Add a self-referencing canonical URL where appropriate.", url))
    results.append(_result("Mobile SEO", "Passed" if viewport else "Warning", "Viewport meta tag found" if viewport else "Viewport meta tag missing", "No action needed." if viewport else "Add a responsive viewport meta tag.", url))

    # Social
    og_title = soup.find("meta", property="og:title")
    og_desc = soup.find("meta", property="og:description")
    if og_title and og_desc:
        results.append(_result("Social SEO", "Passed", "Open Graph metadata is complete", "No action needed.", url))
    else:
        results.append(_result("Social SEO", "Warning", "Incomplete Open Graph metadata", "Add og:title and og:description for better social sharing.", url))

    # Security headers from the fetched page.
    headers = {str(k).lower(): str(v) for k, v in (page.get("headers") or {}).items()}
    security_headers = ["content-security-policy", "strict-transport-security", "x-content-type-options", "x-frame-options", "referrer-policy"]
    missing = [h for h in security_headers if h not in headers]
    if missing:
        results.append(_result("Security", "Warning", f"{len(missing)} recommended security headers missing", "Review and configure recommended HTTP security headers.", url))
    else:
        results.append(_result("Security", "Passed", "Recommended security headers are present", "No action needed.", url))

    return results


def _check_link(url, source_url, timeout=10):
    try:
        r = _request(url, "HEAD", timeout)
        if r.status_code in (403, 405) or r.status_code >= 500:
            r = _request(url, "GET", timeout)
        state = "Working" if 200 <= r.status_code < 300 else "Redirect" if 300 <= r.status_code < 400 else f"Broken ({r.status_code})" if r.status_code >= 400 else "Unknown"
        return {"Source URL": source_url, "URL": url, "Status": r.status_code, "State": state, "Redirects": len(r.history), "Final URL": r.url, "Error": ""}
    except requests.RequestException as exc:
        return {"Source URL": source_url, "URL": url, "Status": None, "State": "Unreachable", "Redirects": 0, "Final URL": "", "Error": str(exc)}


def audit_links(pages, timeout=10):
    """Robustly accepts crawler pages as dicts or strings and never indexes a list with a string."""
    targets = []
    seen = set()
    for page in pages or []:
        if isinstance(page, str):
            source_url, html = page, ""
        elif isinstance(page, dict):
            source_url, html = page.get("url") or page.get("URL") or "", page.get("html") or ""
        else:
            continue
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = str(a.get("href") or "").strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            target = urldefrag(urljoin(source_url, href))[0]
            if urlparse(target).scheme not in ("http", "https") or target in seen:
                continue
            seen.add(target)
            targets.append((target, source_url))

    results = []
    if not targets:
        return results
    with ThreadPoolExecutor(max_workers=min(12, len(targets))) as executor:
        futures = [executor.submit(_check_link, url, source, timeout) for url, source in targets]
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                results.append({"URL": "", "State": "Unreachable", "Status": None, "Error": str(exc)})
    return results


def robots_and_sitemap(base_url, timeout=10):
    base_url = base_url.rstrip("/")
    data = {"robots.txt": {}, "sitemap.xml": {}}
    for name, path in (("robots.txt", "/robots.txt"), ("sitemap.xml", "/sitemap.xml")):
        url = base_url + path
        try:
            r = _request(url, "GET", timeout)
            data[name] = {"url": url, "status": r.status_code, "available": 200 <= r.status_code < 300, "final_url": r.url}
        except requests.RequestException as exc:
            data[name] = {"url": url, "status": None, "available": False, "error": str(exc)}
    return data
