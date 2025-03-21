import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from gamefriend.scraper import GameFAQsScraper


@pytest.fixture
def scraper():
    return GameFAQsScraper(verbose=True)


@pytest.fixture
def temp_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


def create_mock_response(content: str, status_code: int = 200):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = content
    mock_response.raise_for_status = MagicMock()
    return mock_response


def test_extract_game_info():
    scraper = GameFAQsScraper()

    # Test valid URL
    url = "https://gamefaqs.gamespot.com/gba/468548-golden-sun/faqs/31453"
    platform, game = scraper._extract_game_info(url)
    assert platform == "gba"
    assert game == "golden-sun"

    # Test URL with different format
    url = "https://gamefaqs.gamespot.com/snes/588383-illusion-of-gaia/faqs/22902"
    platform, game = scraper._extract_game_info(url)
    assert platform == "snes"
    assert game == "illusion-of-gaia"

    # Test invalid URL
    with pytest.raises(ValueError):
        scraper._extract_game_info("https://invalid-url.com")


def test_get_game_folder():
    scraper = GameFAQsScraper()

    # Test valid URL
    url = "https://gamefaqs.gamespot.com/gba/468548-golden-sun/faqs/31453"
    folder = scraper._get_game_folder(url)
    assert str(folder) == "guides/gba/golden-sun"

    # Test URL with different format
    url = "https://gamefaqs.gamespot.com/snes/588383-illusion-of-gaia/faqs/22902"
    folder = scraper._get_game_folder(url)
    assert str(folder) == "guides/snes/illusion-of-gaia"


def test_extract_content_pre_formatted():
    scraper = GameFAQsScraper()

    # Create a mock BeautifulSoup with pre-formatted content
    html = """
    <div class="faqtext">
        <pre>
        # Guide Title
        This is a guide content.
        
        ## Section 1
        Some text here.
        </pre>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")

    content = scraper._extract_content(soup)
    assert "# Guide Title" in content
    assert "## Section 1" in content
    assert "Some text here" in content


def test_extract_content_html():
    scraper = GameFAQsScraper(verbose=True)
    
    # Create a mock BeautifulSoup with HTML content
    html = """
    <div class="faqtext">
        <h1>Guide Title</h1>
        <p>This is a guide content.</p>
        <h2>Section 1</h2>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <pre><code>Some code here</code></pre>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    
    content = scraper._extract_content(soup)
    print("\nExtracted content:")
    print(content)
    
    # Check each part of the content
    expected_parts = [
        "# Guide Title",
        "This is a guide content",
        "## Section 1",
        "* Item 1",
        "* Item 2",
        "```",
        "Some code here",
        "```"
    ]
    
    for part in expected_parts:
        assert part in content, f"Expected '{part}' to be in content"
        
    # Check the order of elements
    title_pos = content.find("# Guide Title")
    content_pos = content.find("This is a guide content")
    section_pos = content.find("## Section 1")
    item1_pos = content.find("* Item 1")
    
    assert title_pos < content_pos < section_pos < item1_pos, "Content is not in the expected order"


def test_get_pagination_info():
    scraper = GameFAQsScraper()

    # Test with pagination info
    html = """
    <ul class="paginate">
        <li>Page 1 of 5</li>
    </ul>
    """
    soup = BeautifulSoup(html, "html.parser")
    current_page, total_pages = scraper._get_pagination_info(soup)
    assert current_page == 1
    assert total_pages == 5

    # Test without pagination info
    html = "<div>No pagination</div>"
    soup = BeautifulSoup(html, "html.parser")
    current_page, total_pages = scraper._get_pagination_info(soup)
    assert current_page == 1
    assert total_pages == 1


@patch("requests.Session")
def test_download_guide(mock_session, temp_dir):
    scraper = GameFAQsScraper()

    # Create mock response for the guide page
    guide_html = """
    <div class="faqtext">
        <h1>Guide Title</h1>
        <p>This is a guide content.</p>
    </div>
    """
    mock_response = create_mock_response(guide_html)
    mock_session.return_value.get.return_value = mock_response

    # Test guide download
    url = "https://gamefaqs.gamespot.com/gba/468548-golden-sun/faqs/31453"
    content, output_path = scraper.download_guide(url)

    assert "# Guide Title" in content
    assert "This is a guide content" in content
    assert output_path.parts[-1].startswith("guide_")
    assert output_path.parts[-1].endswith(".md")


@patch("requests.Session")
def test_download_guide_error_handling(mock_session):
    scraper = GameFAQsScraper()

    # Test with failed request
    mock_response = create_mock_response("", status_code=404)
    mock_session.return_value.get.return_value = mock_response

    url = "https://gamefaqs.gamespot.com/invalid/url"
    with pytest.raises(Exception):
        scraper.download_guide(url)


def test_content_cleaning():
    scraper = GameFAQsScraper()

    # Test cleaning of whitespace and formatting
    html = """
    <div class="faqtext">
        <h1>  Guide Title  </h1>
        <p>  This is a guide content.  </p>
        <h2>  Section 1  </h2>
        <ul>
            <li>  Item 1  </li>
            <li>  Item 2  </li>
        </ul>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")

    content = scraper._extract_content(soup)
    assert "# Guide Title" in content
    assert "This is a guide content" in content
    assert "## Section 1" in content
    assert "* Item 1" in content
    assert "* Item 2" in content
    assert "  " not in content  # No double spaces
