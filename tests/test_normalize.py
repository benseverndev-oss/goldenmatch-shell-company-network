from shellnet.normalize import (
    normalize_address_text,
    normalize_company_name,
    normalize_identifier,
    normalize_jurisdiction,
    tokenize_name,
)


class TestNormalizeCompanyName:
    def test_strips_basic_suffixes(self) -> None:
        assert normalize_company_name("Acme Holdings Limited") == "acme holdings"
        assert normalize_company_name("ACME HOLDINGS LTD.") == "acme holdings"
        assert normalize_company_name("Sunrise Trading S.A.") == "sunrise trading"

    def test_handles_unicode_and_punctuation(self) -> None:
        # Diacritics fold, punctuation drops, dotted initials collapse,
        # and the trailing legal-form suffix gets stripped.
        assert normalize_company_name("Café Société Anonyme") == "cafe"
        assert normalize_company_name("U.S. Acme Corp") == "us acme"

    def test_does_not_destroy_to_empty(self) -> None:
        # If everything looks like a suffix, keep the original tokens.
        out = normalize_company_name("Trust Foundation")
        assert out  # non-empty
        # one-token names with a suffix-like word stay intact
        assert normalize_company_name("Limited") == "limited"

    def test_empty_inputs(self) -> None:
        assert normalize_company_name(None) == ""
        assert normalize_company_name("") == ""
        assert normalize_company_name("   ") == ""

    def test_does_not_strip_middle(self) -> None:
        # "Limited" in the middle must survive — only trailing suffixes go.
        assert "limited" in normalize_company_name("The Limited Edition Records Co")

    def test_collapses_whitespace(self) -> None:
        assert normalize_company_name("  Foo   Bar    Inc  ") == "foo bar"


class TestTokenizeName:
    def test_simple(self) -> None:
        assert tokenize_name("Foo, Bar & Baz!") == ["foo", "bar", "baz"]

    def test_empty(self) -> None:
        assert tokenize_name("") == []
        assert tokenize_name(None) == []  # type: ignore[arg-type]


class TestNormalizeJurisdiction:
    def test_iso_code_passthrough(self) -> None:
        assert normalize_jurisdiction("GB") == "gb"
        assert normalize_jurisdiction("us") == "us"

    def test_aliases(self) -> None:
        assert normalize_jurisdiction("United Kingdom") == "gb"
        assert normalize_jurisdiction("USA") == "us"
        assert normalize_jurisdiction("British Virgin Islands") == "vg"
        assert normalize_jurisdiction("Cayman Islands") == "ky"

    def test_state_qualified(self) -> None:
        # OpenCorporates form: "us_de" → "us"
        assert normalize_jurisdiction("us_de") == "us"

    def test_unknown_returns_none(self) -> None:
        assert normalize_jurisdiction("Atlantis") is None
        assert normalize_jurisdiction(None) is None
        assert normalize_jurisdiction("") is None


class TestNormalizeAddressText:
    def test_basic(self) -> None:
        out = normalize_address_text("10 Downing St., London, EC1A 1AA")
        assert "downing" in out
        assert "ec1a" in out
        assert "," not in out

    def test_empty(self) -> None:
        assert normalize_address_text(None) == ""
        assert normalize_address_text("") == ""


class TestNormalizeIdentifier:
    def test_strips_punctuation_and_uppercases(self) -> None:
        assert normalize_identifier("529900T8BM49-AURSDO55") == "529900T8BM49AURSDO55"
        assert normalize_identifier("gb 12345 67") == "GB1234567"

    def test_empty(self) -> None:
        assert normalize_identifier(None) == ""
        assert normalize_identifier("") == ""
