from app.ingestion.ingest import chunk_body, parse_document


def test_front_matter_and_sections():
    meta, body = parse_document("---\ndoc_id: x\nstatus: active\n---\n# T\n## A\nfoo\n\n## B\nbar")
    assert meta["doc_id"] == "x"
    assert [h for h, _ in chunk_body(body)] == ["T", "A", "B"]


def test_long_section_is_split():
    body = "## Big\n" + "\n\n".join("word " * 60 for _ in range(10))
    chunks = chunk_body(body, max_chars=500)
    assert len(chunks) > 1 and all(len(t) < 800 for _, t in chunks)
