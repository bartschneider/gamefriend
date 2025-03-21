"""
Core functionality for scraping GameFAQs guides.
"""

import re
import time
from pathlib import Path
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)


class GameFAQsScraper:
    """Handles scraping of GameFAQs guides."""

    BASE_URL = "https://gamefaqs.gamespot.com"
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    def __init__(self, verbose: bool = False):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        self.verbose = verbose
        self.last_request_time = 0

    def _get_page(self, url: str) -> BeautifulSoup:
        """Fetch and parse a page from GameFAQs."""
        # Add delay between requests
        elapsed = time.time() - self.last_request_time
        if elapsed < 2:  # Ensure at least 2 seconds between requests
            time.sleep(2 - elapsed)

        if self.verbose:
            print(f"Requesting URL: {url}")

        # First try to get the page normally
        response = self.session.get(url)
        self.last_request_time = time.time()
        response.raise_for_status()

        if self.verbose:
            print(f"Response status: {response.status_code}")
            print(f"Final URL: {response.url}")
            print("Response headers:", response.headers)

        # Parse the initial HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Look for the guide content in various places
        content = None

        # Try to find the pre-formatted text content first
        content_div = soup.find("div", class_="faqtext")
        if content_div:
            pre_content = content_div.find("pre")
            if pre_content:
                if self.verbose:
                    print("Found pre-formatted text content")
                return soup

        # Try to find the guide ID from the page
        guide_id = None
        meta_data = soup.find("meta", {"id": "utag-data"})
        if meta_data and "content" in meta_data.attrs:
            try:
                import json

                data = json.loads(meta_data["content"])
                if "articleId" in data:
                    guide_id = data["articleId"]
            except:
                pass

        if not guide_id:
            # Try to get guide ID from URL
            guide_id = url.split("/")[-1]
            if not guide_id.isdigit():
                guide_id = None

        if guide_id:
            # Try different API endpoints
            api_endpoints = [
                f"{self.BASE_URL}/api/faqs/{guide_id}/content",
                f"{self.BASE_URL}/api/v1/faqs/{guide_id}",
                f"{self.BASE_URL}/api/guides/{guide_id}/text",
            ]

            for api_url in api_endpoints:
                if self.verbose:
                    print(f"Trying API endpoint: {api_url}")

                try:
                    api_response = self.session.get(api_url)
                    if api_response.status_code == 200:
                        if self.verbose:
                            print("Successfully got content from API")
                        return BeautifulSoup(api_response.text, "html.parser")
                except:
                    continue

        # If we still haven't found the content, try to find it in the original HTML
        if not content:
            # Look for any div that might contain the guide text
            for div in soup.find_all(
                "div", class_=["faqtext", "ffaqbody", "faq_text", "guide_text"]
            ):
                text = div.get_text(strip=True)
                if (
                    len(text) > 1000
                ):  # Assume this is the main content if it's long enough
                    if self.verbose:
                        print("Found guide content in HTML")
                    return soup

        if self.verbose:
            print("Warning: Could not find guide content")

        # If we got here, we'll return the original soup and let _extract_content handle any errors
        return soup

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract the main content from a guide page."""
        if self.verbose:
            print("Looking for content div...")

        # Try all possible content div classes
        content = None
        for class_name in ["faqtext", "ffaqbody", "faq_text", "guide_text"]:
            content = soup.find("div", class_=class_name)
            if content:
                if self.verbose:
                    print(f"Found content div with class '{class_name}'")
                break

        if not content:
            raise ValueError("Could not find guide content")

        if self.verbose:
            print("Content div structure:")
            print(content.prettify())

        # Check if this is a pre-formatted guide (text-only guide)
        # We only treat it as pre-formatted if:
        # 1. The pre tag is a direct child of the content div
        # 2. It's not part of a code block (<pre><code>)
        # 3. It contains significant content
        # 4. There are no other significant content elements
        pre_content = None
        has_other_content = False
        
        for child in content.children:
            if isinstance(child, str) and child.strip():
                has_other_content = True
                continue
                
            if not getattr(child, 'name', None):
                continue
                
            if child.name == 'pre':
                # Skip if it's part of a code block
                if child.find('code'):
                    has_other_content = True
                    continue
                    
                # Found a potential pre-formatted content
                if child.get_text(strip=True):
                    pre_content = child
            elif child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'table']:
                has_other_content = True

        if pre_content and not has_other_content:  # Only use pre if it's the main content
            if self.verbose:
                print("Found pre-formatted content")
                text = pre_content.get_text()
                print(f"Content length: {len(text)}")
                print("First 1000 chars:")
                print(text[:1000])
                print("Content type:", type(text))
                print("Content encoding:", text.encode("utf-8")[:100])

            # Get the text and ensure it's properly formatted
            text = pre_content.get_text()
            if not text:
                raise ValueError("Empty guide content")

            # Normalize line endings
            text = text.replace("\r\n", "\n").replace("\r", "\n")

            # Ensure the text ends with a newline
            if not text.endswith("\n"):
                text += "\n"

            return text

        if self.verbose:
            print("Handling as HTML guide...")

        # Remove unwanted elements
        for element in content.find_all(["script", "style", "iframe", "ins"]):
            element.decompose()
            
        # Remove navigation elements but keep content divs
        for element in content.find_all("div"):
            if element.get("class") and any(c in ["ftoc", "nav", "menu"] for c in element.get("class")):
                element.decompose()

        def process_element(element) -> str:
            """Process a single element and its children."""
            if self.verbose:
                print(f"Processing element: {element.name if hasattr(element, 'name') else 'text'}")
                if hasattr(element, 'prettify'):
                    print(element.prettify())
                else:
                    print(str(element))

            if isinstance(element, str):
                return element.strip() + " " if element.strip() else ""
                
            if not element.name:
                return element.string.strip() + " " if element.string and element.string.strip() else ""

            # Skip empty elements
            if not element.get_text(strip=True):
                return ""

            # Handle different HTML elements
            if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                level = int(element.name[1])
                return "\n" + "#" * level + " " + element.get_text(strip=True) + "\n"
            elif element.name == "p":
                return element.get_text(strip=True) + "\n"
            elif element.name == "br":
                return "\n"
            elif element.name == "hr":
                return "\n---\n"
            elif element.name == "ul":
                result = "\n"
                for li in element.find_all("li", recursive=False):
                    result += "* " + li.get_text(strip=True) + "\n"
                return result
            elif element.name == "ol":
                result = "\n"
                for i, li in enumerate(element.find_all("li", recursive=False), 1):
                    result += f"{i}. " + li.get_text(strip=True) + "\n"
                return result
            elif element.name == "pre":
                if element.find("code"):
                    code_content = element.find("code").get_text()
                    return "```\n" + code_content + "\n```\n"
                return "```\n" + element.get_text() + "\n```\n"
            elif element.name == "code" and not element.parent.name == "pre":
                return "`" + element.get_text(strip=True) + "`"
            elif element.name == "strong" or element.name == "b":
                return "**" + element.get_text(strip=True) + "**"
            elif element.name == "em" or element.name == "i":
                return "*" + element.get_text(strip=True) + "*"
            elif element.name == "a" and element.get("href"):
                return "[" + element.get_text(strip=True) + "](" + element["href"] + ")"
            elif element.name == "table":
                result = "\n"
                for tr in element.find_all("tr"):
                    result += "| " + " | ".join(td.get_text(strip=True) for td in tr.find_all(["td", "th"])) + " |\n"
                    if tr.find("th"):  # Add separator after header row
                        result += "|" + "|".join("---" for _ in tr.find_all("th")) + "|\n"
                return result
            else:
                # Process children recursively for other elements
                return "".join(process_element(child) for child in element.children)

        # Process all content
        result = "".join(process_element(child) for child in content.children if child.name or (isinstance(child, str) and child.strip()))
        
        if self.verbose:
            print("Final processed content:")
            print(result)
        
        # Clean up the text
        result = re.sub(r'\n\s+\n', '\n\n', result)  # Remove excess whitespace
        result = re.sub(r' +', ' ', result)  # Remove multiple spaces
        result = result.strip()
        
        if not result:
            raise ValueError("Empty guide content")
            
        return result

    def _get_pagination_info(self, soup: BeautifulSoup) -> tuple[int, int]:
        """Get current page number and total pages from pagination info."""
        pagination = soup.find("ul", class_="paginate")
        if not pagination:
            return 1, 1

        # Try to find "Page X of Y" text in any li element
        for li in pagination.find_all("li"):
            if not li.text:
                continue
            match = re.search(r"Page \d+ of (\d+)", li.text)
            if match:
                total_pages = int(match.group(1))
                return 1, total_pages

        # Fallback: Count page links excluding "Last Page" and "Next Page"
        page_links = pagination.find_all("a", href=re.compile(r"\?page=\d+"))
        if page_links:
            max_page = 1
            for link in page_links:
                if link.text in ["Last Page", "Next Page"]:
                    continue
                match = re.search(r"\?page=(\d+)", link["href"])
                if match:
                    page_num = int(match.group(1))
                    max_page = max(max_page, page_num)
            return 1, max_page

        return 1, 1

    def _get_page_url(self, base_url: str, page: int) -> str:
        """Construct URL for a specific page number."""
        # Remove any existing page parameter
        url = re.sub(r"\?page=\d+", "", base_url)
        # Add new page parameter if not page 1
        if page > 1:
            url = f"{url}?page={page}"
        return url

    def _extract_game_info(self, url: str) -> tuple[str, str]:
        """Extract game name and platform from a GameFAQs URL."""
        # URL format: https://gamefaqs.gamespot.com/platform/id-game-name/...
        parts = url.split("/")
        try:
            platform = parts[3]
            game_id_name = parts[4]
            # Extract game name from ID-name format (e.g., "588673-soul-blazer")
            game_name = "-".join(game_id_name.split("-")[1:])
            if not game_name:
                game_name = game_id_name
            return platform, game_name
        except (IndexError, AttributeError):
            raise ValueError(f"Could not extract game info from URL: {url}")

    def _get_game_folder(self, url: str) -> Path:
        """Get the folder path for a game's guides."""
        platform, game_name = self._extract_game_info(url)
        # Create folder structure: guides/platform/game-name
        base_folder = Path("guides")
        platform_folder = base_folder / platform
        game_folder = platform_folder / game_name

        # Create folders if they don't exist
        base_folder.mkdir(exist_ok=True)
        platform_folder.mkdir(exist_ok=True)
        game_folder.mkdir(exist_ok=True)

        return game_folder

    def download_guide(self, url: str, output: str = None) -> tuple[str, Path]:
        """Download a complete guide, handling multiple pages.

        Returns:
            tuple: (guide content, output path)
        """
        all_content = []
        base_url = url

        # Get the game folder and determine output path
        game_folder = self._get_game_folder(url)
        if output is None:
            # Use the guide ID as filename if no output specified
            guide_id = url.split("/")[-1]
            output = f"guide_{guide_id}.md"
        output_path = game_folder / output

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            transient=True,
        ) as progress:
            # Get first page to determine total pages
            soup = self._get_page(base_url)
            _, total_pages = self._get_pagination_info(soup)

            # Adjust total pages to avoid the problematic last page
            actual_pages = total_pages - 1 if total_pages > 1 else 1

            task = progress.add_task("Downloading guide...", total=actual_pages)

            # Download each page
            for page in range(1, actual_pages + 1):
                page_url = self._get_page_url(base_url, page)

                if self.verbose:
                    print(f"Fetching page {page} of {actual_pages}: {page_url}")

                if page > 1:  # Already have first page
                    soup = self._get_page(page_url)

                content = self._extract_content(soup)
                if content:
                    all_content.append(content)
                progress.update(task, completed=page)

        if not all_content:
            raise ValueError("No content found in guide")

        # Join all content and write to file
        final_content = "\n\n".join(all_content)
        output_path.write_text(final_content, encoding="utf-8")

        return final_content, output_path
