import pytest

from app.schemas import QueryIn
from app.errors import IndexingError
from app.main import upload_document


def test_query_contract_accepts_document_filter() -> None:
    payload = QueryIn(question="What is this document about?", document_ids=[1, 2], summarize=True, debug=True)
    assert payload.document_ids == [1, 2]
    assert payload.summarize is True
    assert payload.debug is True


async def _raise_indexing_error(*_: object) -> None:
    raise IndexingError("Reindex required", status_code=409)


@pytest.mark.asyncio
async def test_upload_document_maps_indexing_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException

    monkeypatch.setattr("app.main.ingest_document", _raise_indexing_error)

    try:
        await upload_document(file=object(), db=object())
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail == "Reindex required"
