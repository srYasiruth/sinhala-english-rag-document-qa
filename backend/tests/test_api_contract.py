from app.schemas import QueryIn


def test_query_contract_accepts_document_filter() -> None:
    payload = QueryIn(question="What is this document about?", document_ids=[1, 2], summarize=True)
    assert payload.document_ids == [1, 2]
    assert payload.summarize is True
