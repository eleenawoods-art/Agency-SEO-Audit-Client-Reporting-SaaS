from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from .crawler import check_url


def audit_page(page):
    soup = BeautifulSoup(page["html"], "html.parser")

    url = page["url"]

    results = []

    # Title
    title_tag = soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else ""

    if not title:
        results.append({
            "category": "On-Page SEO",
            "issue": "Missing title tag",
            "severity": "Critical",
            "recommendation": "Add a unique and descriptive title tag."
        })
    elif len(title) < 30:
        results.append({
            "category": "On-Page SEO",
            "issue": "Title tag is too short",
            "severity": "Warning",
            "recommendation": "Consider creating a more descriptive title."
        })
    elif len(title) > 60:
        results.append({
            "category": "On-Page SEO",
            "issue": "Title tag may be too long",
            "severity": "Warning",
            "recommendation": "Keep the title concise, ideally around 30–60 characters."
        })
    else:
        results.append({
            "category": "On-Page SEO",
            "issue": "Title tag looks good",
            "severity": "Passed",
            "recommendation": "No action required."
        })

    # Meta description
    meta_desc = soup.find(
        "meta",
        attrs={"name": lambda x: x and x.lower() == "description"}
    )

    description = meta_desc.get("content", "").strip() if meta_desc else ""

    if not description:
        results.append({
            "category": "On-Page SEO",
            "issue": "Missing meta description",
            "severity": "Critical",
            "recommendation": "Add a unique meta description for this page."
        })
    elif len(description) < 70:
        results.append({
            "category": "On-Page SEO",
            "issue": "Meta description is short",
            "severity": "Warning",
            "recommendation": "Expand the description with useful page-specific information."
        })
    elif len(description) > 160:
        results.append({
            "category": "On-Page SEO",
            "issue": "Meta description may be too long",
            "severity": "Warning",
            "recommendation": "Keep the meta description around 70–160 characters."
        })
    else:
        results.append({
            "category": "On-Page SEO",
            "issue": "Meta description looks good",
            "severity": "Passed",
            "recommendation": "No action required."
        })

    # H1
    h1s = soup.find_all("h1")

    if len(h1s) == 0:
        results.append({
            "category": "Content",
            "issue": "Missing H1 heading",
            "severity": "Critical",
            "recommendation": "Add one clear primary H1 heading."
        })
    elif len(h1s) > 1:
        results.append({
            "category": "Content",
            "issue": "Multiple H1 headings",
            "severity": "Warning",
            "recommendation": "Review the page structure and consider using one primary H1."
        })
    else:
        results.append({
            "category": "Content",
            "issue": "H1 heading present",
            "severity": "Passed",
            "recommendation": "No action required."
        })

    # H2
    h2_count = len(soup.find_all("h2"))

    if h2_count == 0:
        results.append({
            "category": "Content",
            "issue": "No H2 headings found",
            "severity": "Warning",
            "recommendation": "Use relevant H2 headings where they improve content structure."
        })
    else:
        results.append({
            "category": "Content",
            "issue": f"{h2_count} H2 headings found",
            "severity": "Passed",
            "recommendation": "No action required."
        })

    # Images
    images = soup.find_all("img")
    missing_alt = 0

    for img in images:
        alt = img.get("alt")

        if alt is None or not alt.strip():
            missing_alt += 1

    if images and missing_alt:
        results.append({
            "category": "Images",
            "issue": f"{missing_alt} image(s) missing alt text",
            "severity": "Warning",
            "recommendation": "Add meaningful alt text to informative images."
        })
    elif images:
        results.append({
            "category": "Images",
            "issue": "All detected images have alt attributes",
            "severity": "Passed",
            "recommendation": "No action required."
        })

    # Canonical
    canonical = soup.find(
        "link",
        attrs={"rel": lambda x: x and "canonical" in x}
    )

    if not canonical:
        results.append({
            "category": "Technical SEO",
            "issue": "Missing canonical URL",
            "severity": "Warning",
            "recommendation": "Consider adding a canonical URL."
        })
    else:
        results.append({
            "category": "Technical SEO",
            "issue": "Canonical URL found",
            "severity": "Passed",
            "recommendation": "No action required."
        })

    # Viewport
    viewport = soup.find(
        "meta",
        attrs={"name": lambda x: x and x.lower() == "viewport"}
    )

    if not viewport:
        results.append({
            "category": "Mobile",
            "issue": "Missing viewport meta tag",
            "severity": "Critical",
            "recommendation": "Add a responsive viewport meta tag."
        })
    else:
        results.append({
            "category": "Mobile",
            "issue": "Viewport meta tag found",
            "severity": "Passed",
            "recommendation": "No action required."
        })

    # Open Graph
    og_title = soup.find(
        "meta",
        property="og:title"
    )

    og_description = soup.find(
        "meta",
        property="og:description"
    )

    if not og_title or not og_description:
        results.append({
            "category": "Social SEO",
            "issue": "Incomplete Open Graph metadata",
            "severity": "Warning",
            "recommendation": "Add og:title and og:description for better social sharing."
        })
    else:
        results.append({
            "category": "Social SEO",
            "issue": "Open Graph metadata found",
            "severity": "Passed",
            "recommendation": "No action required."
        })

    # HTTPS
    if url.lower().startswith("https://"):
        results.append({
            "category": "Security",
            "issue": "HTTPS enabled",
            "severity": "Passed",
            "recommendation": "No action required."
        })
    else:
        results.append({
            "category": "Security",
            "issue": "Website is not using HTTPS",
            "severity": "Critical",
            "recommendation": "Install an SSL certificate and redirect HTTP to HTTPS."
        })

    # Security headers
    headers = {
        k.lower(): v
        for k, v in page["headers"].items()
    }

    security_headers = [
        "x-content-type-options",
        "x-frame-options",
        "content-security-policy"
    ]

    missing_security = [
        h for h in security_headers
        if h not in headers
    ]

    if missing_security:
        results.append({
            "category": "Security",
            "issue": f"{len(missing_security)} recommended security header(s) missing",
            "severity": "Warning",
            "recommendation": "Review and configure recommended HTTP security headers."
        })
    else:
        results.append({
            "category": "Security",
            "issue": "Recommended security headers detected",
            "severity": "Passed",
            "recommendation": "No action required."
        })

    return results


def audit_links(page, max_checks=30):
    soup = BeautifulSoup(page["html"], "html.parser")

    base_url = page["url"]

    links = []

    for a in soup.find_all("a", href=True):

        href = a.get("href", "").strip()

        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        absolute = urljoin(base_url, href)

        if absolute not in links:
            links.append(absolute)

    links = links[:max_checks]

    broken = []

    for link in links:
        result = check_url(link)

        if not result["working"]:
            broken.append({
                "url": link,
                "status": result["status"]
            })

    return broken


def robots_and_sitemap(base_url):
    parsed = urlparse(base_url)

    root = f"{parsed.scheme}://{parsed.netloc}"

    robots_url = urljoin(root, "/robots.txt")
    sitemap_url = urljoin(root, "/sitemap.xml")

    robots = check_url(robots_url)
    sitemap = check_url(sitemap_url)

    return {
        "robots": robots,
        "sitemap": sitemap
    }
