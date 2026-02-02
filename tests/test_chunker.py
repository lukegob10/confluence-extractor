from confluence_rag.ingest.chunker import chunk_text


def test_chunk_text_empty() -> None:
    assert chunk_text("") == []


def test_chunk_text_small() -> None:
    text = "hello world"
    assert chunk_text(text, chunk_size=2000, chunk_overlap=200) == [text]


def test_chunk_text_overlap() -> None:
    text = " ".join(["word"] * 1000)
    chunks = chunk_text(text, chunk_size=200, chunk_overlap=50)
    assert len(chunks) > 1
    assert chunks[0] != chunks[1]

