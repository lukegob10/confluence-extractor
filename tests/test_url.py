from confluence_rag.confluence.url import page_id_from_url


def test_page_id_from_cloud_url() -> None:
    url = "https://example.atlassian.net/wiki/spaces/ENG/pages/123456789/Some+Page"
    assert page_id_from_url(url) == "123456789"


def test_page_id_from_server_url() -> None:
    url = "https://confluence.example.com/pages/viewpage.action?pageId=987654"
    assert page_id_from_url(url) == "987654"


def test_page_id_from_invalid_url() -> None:
    assert page_id_from_url("not a url") is None

