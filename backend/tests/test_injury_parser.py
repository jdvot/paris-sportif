"""Tests for InjuryParser player name extraction and headline cleaning.

Covers Unicode names, hyphenated names, Google News source suffixes,
French/English patterns, and false positive rejection.
"""

from src.prediction_engine.rag_enrichment import InjuryParser


class TestCleanHeadline:
    """Test Google News source suffix removal."""

    def test_strips_english_source(self) -> None:
        raw = "Salah ruled out with hamstring injury - BBC Sport"
        assert InjuryParser._clean_headline(raw) == "Salah ruled out with hamstring injury"

    def test_strips_french_source(self) -> None:
        raw = "Mbappé blessé à l'épaule - L'Équipe"
        assert InjuryParser._clean_headline(raw) == "Mbappé blessé à l'épaule"

    def test_preserves_headline_without_source(self) -> None:
        raw = "Salah ruled out with hamstring injury"
        assert InjuryParser._clean_headline(raw) == raw

    def test_preserves_internal_hyphens(self) -> None:
        raw = "Jean-Pierre Nsame blessé - RMC Sport"
        assert InjuryParser._clean_headline(raw) == "Jean-Pierre Nsame blessé"

    def test_strips_multiword_source(self) -> None:
        raw = "Injury update: Müller out for weeks - The Guardian Football"
        assert InjuryParser._clean_headline(raw) == "Injury update: Müller out for weeks"


class TestExtractPlayerNameEnglish:
    """English headline patterns."""

    def test_player_ruled_out(self) -> None:
        result = InjuryParser._extract_player_name(
            "Mohamed Salah ruled out of Liverpool clash", "Liverpool"
        )
        assert result == "Mohamed Salah"

    def test_player_injured(self) -> None:
        result = InjuryParser._extract_player_name("Angel Gomes injured in training", "Lille")
        assert result == "Angel Gomes"

    def test_player_sidelined(self) -> None:
        result = InjuryParser._extract_player_name(
            "Kevin de Bruyne sidelined for three weeks", "Manchester City"
        )
        assert result == "Kevin de Bruyne"

    def test_injury_blow_for(self) -> None:
        result = InjuryParser._extract_player_name(
            "Injury blow for Virgil van Dijk ahead of final", "Liverpool"
        )
        assert result == "Virgil van Dijk"

    def test_possessive_injury(self) -> None:
        result = InjuryParser._extract_player_name("Mbappé's knee injury could sideline him", "PSG")
        assert result == "Mbappé"

    def test_without_player(self) -> None:
        result = InjuryParser._extract_player_name("Liverpool without Salah for derby", "Liverpool")
        assert result == "Salah"

    def test_player_with_parentheses(self) -> None:
        result = InjuryParser._extract_player_name(
            "Mikautadze (Metz) ruled out with injury", "Metz"
        )
        assert result == "Mikautadze"

    def test_player_out_with(self) -> None:
        result = InjuryParser._extract_player_name(
            "Thomas Müller out with hamstring strain", "Bayern Munich"
        )
        assert result == "Thomas Müller"

    def test_player_suffers(self) -> None:
        result = InjuryParser._extract_player_name(
            "Julián Álvarez suffers ankle injury", "Atlético Madrid"
        )
        assert result == "Julián Álvarez"


class TestExtractPlayerNameFrench:
    """French headline patterns."""

    def test_blessure_de(self) -> None:
        result = InjuryParser._extract_player_name("Blessure de Kylian Mbappé au quadriceps", "PSG")
        assert result == "Kylian Mbappé"

    def test_player_blesse(self) -> None:
        result = InjuryParser._extract_player_name(
            "Georges Mikautadze blessé à l'entraînement", "FC Metz"
        )
        assert result == "Georges Mikautadze"

    def test_player_forfait(self) -> None:
        result = InjuryParser._extract_player_name("Angel Gomes forfait pour le match", "Lille OSC")
        assert result == "Angel Gomes"

    def test_sans_player(self) -> None:
        result = InjuryParser._extract_player_name("Lille sans Jonathan David ce week-end", "Lille")
        assert result == "Jonathan David"

    def test_prive_de(self) -> None:
        result = InjuryParser._extract_player_name(
            "Metz privé de Mikautadze pour le derby", "FC Metz"
        )
        assert result == "Mikautadze"

    def test_forfait_colon(self) -> None:
        result = InjuryParser._extract_player_name("Forfait: N'Golo Kanté", "Al Ittihad")
        assert result == "N'Golo Kanté"

    def test_absent_colon(self) -> None:
        result = InjuryParser._extract_player_name("Absent: Jean-Pierre Nsame", "Venezia")
        assert result == "Jean-Pierre Nsame"


class TestExtractPlayerNameEdgeCases:
    """Edge cases and special name formats."""

    def test_rejects_team_name_as_player(self) -> None:
        result = InjuryParser._extract_player_name("Liverpool injured in title race", "Liverpool")
        assert result is None

    def test_rejects_short_names(self) -> None:
        result = InjuryParser._extract_player_name("Al injured in training", "Team")
        assert result is None

    def test_hyphenated_name(self) -> None:
        result = InjuryParser._extract_player_name("Pierre-Emerick Aubameyang injured", "Marseille")
        assert result == "Pierre-Emerick Aubameyang"

    def test_apostrophe_name(self) -> None:
        result = InjuryParser._extract_player_name(
            "N'Golo Kanté ruled out with thigh issue", "Chelsea"
        )
        assert result == "N'Golo Kanté"


class TestParseHeadlineIntegration:
    """Full parse_headline integration tests."""

    def test_english_injury_with_source_suffix(self) -> None:
        info = InjuryParser.parse_headline(
            "Mohamed Salah ruled out with hamstring injury - BBC Sport",
            "Liverpool",
        )
        assert info is not None
        assert info.player_name == "Mohamed Salah"
        assert info.injury_type == "hamstring"
        assert info.confidence >= 0.7

    def test_french_injury_with_source_suffix(self) -> None:
        info = InjuryParser.parse_headline(
            "Kylian Mbappé blessé au quadriceps - L'Équipe",
            "Real Madrid",
        )
        assert info is not None
        assert info.player_name == "Kylian Mbappé"
        assert info.injury_type == "quadriceps"

    def test_suspension_detected(self) -> None:
        info = InjuryParser.parse_headline(
            "Angel Gomes suspendu pour carton rouge - RMC Sport",
            "Lille",
        )
        assert info is not None
        assert info.player_name == "Angel Gomes"
        assert info.injury_type == "suspension"

    def test_false_positive_transfer(self) -> None:
        info = InjuryParser.parse_headline(
            "Salah set to sign new contract with Liverpool", "Liverpool"
        )
        assert info is None

    def test_false_positive_out_of_contract(self) -> None:
        info = InjuryParser.parse_headline("Mbappé out of contract at PSG", "PSG")
        assert info is None

    def test_no_injury_indicators(self) -> None:
        info = InjuryParser.parse_headline("Liverpool beat Arsenal 3-1 in thriller", "Liverpool")
        assert info is None
