import csv
import io
import zipfile

from app.api.pricing import EstimateRequest, post_estimate
from app.pricing import estimate_cost
from app.services.parse_xlsx import parse_xlsx_bytes


def _xlsx_bytes(headers: list[str], rows: list[list[str]]) -> bytes:
    # Build sheet XML cleanly (helper above is intentionally simple; rebuild here).
    rows_xml = ""
    for row_index, values in enumerate([headers, *rows], start=1):
        cells = "".join(
            f'<c r="{chr(64 + col_index)}{row_index}" t="inlineStr"><is><t>{value}</t></is></c>'
            for col_index, value in enumerate(values, start=1)
        )
        rows_xml += f"<row>{cells}</row>"
    sheet = (
        '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{rows_xml}</sheetData></worksheet>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        bundle.writestr("xl/worksheets/sheet1.xml", sheet)
    return buffer.getvalue()


def test_parse_xlsx_inline_strings() -> None:
    result = parse_xlsx_bytes(
        _xlsx_bytes(
            ["company", "website"],
            [["Acme", "https://acme.com"], ["Northstar", "https://northstar.example"]],
        )
    )
    assert result["columns"] == ["company", "website"]
    assert result["totalRows"] == 2
    assert result["rows"][0] == {"company": "Acme", "website": "https://acme.com"}
    csv_text = io.StringIO(str(result["csvText"]))
    assert list(csv.DictReader(csv_text)) == [
        {"company": "Acme", "website": "https://acme.com"},
        {"company": "Northstar", "website": "https://northstar.example"},
    ]


def test_parse_xlsx_rejects_non_zip() -> None:
    try:
        parse_xlsx_bytes(b"not a zip file")
    except ValueError as exc:
        assert "xlsx" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_estimate_cost_uses_list_price() -> None:
    estimate = estimate_cost(
        rows=100, input_tokens_per_row=100, output_tokens_per_row=50, model="gpt-5.4-mini"
    )
    # (100*100*0.75 + 100*50*4.50) / 1M
    assert estimate["estimated_cost"] == 0.03
    assert estimate["provider"] == "openai"


def test_estimate_unknown_model_returns_none_cost() -> None:
    estimate = estimate_cost(
        rows=10, input_tokens_per_row=10, output_tokens_per_row=10, model="unknown-model"
    )
    assert estimate["estimated_cost"] is None


def test_post_estimate_endpoint() -> None:
    result = post_estimate(
        EstimateRequest(
            rows=5,
            model="gemini-2.5-flash-lite",
            input_tokens_per_row=200,
            output_tokens_per_row=100,
        )
    )
    assert result["rows"] == 5
    assert result["provider"] == "gemini"
