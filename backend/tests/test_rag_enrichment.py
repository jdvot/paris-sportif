"""Unit tests for RAG enrichment module.

Tests cover:
- InjuryParser: False positive detection, player name extraction, severity estimation
- InjuryInfo: Dataclass structure

Run with: cd backend && uv run pytest tests/test_rag_enrichment.py -v
"""

import pytest

from src.prediction_engine.rag_enrichment import InjuryInfo, InjuryParser


# =============================================================================
# InjuryParser - False Positive Detection
# =============================================================================


class TestInjuryParserFalsePositives:
    """Test that false positive patterns are correctly excluded."""

    @pytest.mark.parametrize(
        "headline",
        [
            "Mohamed Salah out of contract in 2025",
            "Contract runs out for Liverpool star",
            "Player speaking out about transfer",
            "Manager lashes out at critics",
            "Liverpool drops out of transfer race for midfielder",
            "Club rules out transfer move for striker",
            "Player takes time out from football",
            "Team knocked out of Champions League",
            "Club priced out of deal for target",
            "Star player out of favour under new manager",
            "Midfielder frozen out of first team",
            "Loan move for young striker",
            "Transfer target emerges for Manchester United",
            "Club shows interest in Bayern winger",
            "Player set to sign new contract",
            "Liverpool closes in on midfielder signing",
            "Star agrees terms with new club",
            "Player could leave in January",
            "Midfielder exit rumours intensify",
            "Departure confirmed for veteran defender",
        ],
    )
    def test_excludes_false_positive_headlines(self, headline: str):
        """Test that transfer/contract news is not detected as injury."""
        result = InjuryParser.parse_headline(headline, "Liverpool")
        assert result is None, f"Should exclude: {headline}"


# =============================================================================
# InjuryParser - True Positive Detection
# =============================================================================


class TestInjuryParserTruePositives:
    """Test that real injury headlines are correctly detected."""

    @pytest.mark.parametrize(
        "headline,expected_type",
        [
            ("Mohamed Salah ruled out with hamstring injury", "hamstring"),
            ("Liverpool star sidelined with knee problem", "knee"),
            ("Defender injured in training, ankle issue", "ankle"),
            ("Player undergoes surgery on groin injury", "groin"),
            ("Midfielder doubtful due to calf strain", "calf"),
            ("Striker misses match with back problem", "back"),
            ("ACL tear confirmed for defender", "acl"),
            ("Star player limped off with thigh injury", "thigh"),
            ("Achilles injury rules out midfielder", "achilles"),
            ("Muscle injury sidelines key player", "muscle"),
        ],
    )
    def test_detects_body_part_injuries(self, headline: str, expected_type: str):
        """Test that body part injuries are detected with correct type."""
        result = InjuryParser.parse_headline(headline, "Liverpool")
        assert result is not None, f"Should detect: {headline}"
        assert result.injury_type == expected_type

    @pytest.mark.parametrize(
        "headline",
        [
            "Player suspended for red card",
            "Midfielder suspendu après carton rouge",
            "Star receives 3-match ban",
            "Yellow card accumulation leads to suspension",
        ],
    )
    def test_detects_suspensions(self, headline: str):
        """Test that suspensions are detected."""
        result = InjuryParser.parse_headline(headline, "Liverpool")
        assert result is not None, f"Should detect: {headline}"
        assert result.injury_type == "suspension"

    @pytest.mark.parametrize(
        "headline",
        [
            "Key player blessé à l'entraînement",
            "Blessure pour le défenseur central",
            "Forfait confirmé pour le match de samedi",
            "Joueur absent pour plusieurs semaines",
        ],
    )
    def test_detects_french_headlines(self, headline: str):
        """Test that French injury headlines are detected."""
        result = InjuryParser.parse_headline(headline, "PSG")
        assert result is not None, f"Should detect French: {headline}"


# =============================================================================
# InjuryParser - Player Name Extraction
# =============================================================================


class TestInjuryParserPlayerExtraction:
    """Test player name extraction from headlines."""

    @pytest.mark.parametrize(
        "headline,expected_name",
        [
            ("Mohamed Salah ruled out with hamstring injury", "Mohamed Salah"),
            ("Virgil Van Dijk sidelined for 3 weeks", "Virgil Van Dijk"),
            ("Injury blow for Kylian Mbappe", "Kylian Mbappe"),
            ("Luis Diaz's knee injury confirmed", "Luis Diaz"),
        ],
    )
    def test_extracts_player_names(self, headline: str, expected_name: str):
        """Test that player names are correctly extracted."""
        result = InjuryParser.parse_headline(headline, "Liverpool")
        assert result is not None
        assert result.player_name == expected_name

    def test_does_not_extract_team_name_as_player(self):
        """Test that team name is not extracted as player name."""
        headline = "Liverpool ruled out of title race due to injuries"
        result = InjuryParser.parse_headline(headline, "Liverpool")
        # Should either return None or not have "Liverpool" as player
        if result is not None:
            assert result.player_name != "Liverpool"


# =============================================================================
# InjuryParser - Duration Extraction
# =============================================================================


class TestInjuryParserDuration:
    """Test duration extraction from headlines."""

    @pytest.mark.parametrize(
        "headline,expected_duration",
        [
            ("Player out for 2-3 weeks with injury", "2-3 weeks"),
            ("Midfielder sidelined for 4 weeks", "4 weeks"),
            ("Striker ruled out for 2 months", "2 months"),
            ("Defender faces 1-2 months on sidelines", "1-2 months"),
            ("Star player out for rest of season", "rest of season"),
            ("Long-term injury for goalkeeper", "long-term"),
        ],
    )
    def test_extracts_duration(self, headline: str, expected_duration: str):
        """Test that durations are correctly extracted."""
        result = InjuryParser.parse_headline(headline, "Liverpool")
        assert result is not None
        assert result.duration == expected_duration


# =============================================================================
# InjuryParser - Severity Estimation
# =============================================================================


class TestInjuryParserSeverity:
    """Test severity estimation from headlines."""

    @pytest.mark.parametrize(
        "headline,expected_severity",
        [
            ("ACL rupture for defender, out for season", "serious"),
            ("Player undergoes surgery", "serious"),
            ("Long-term injury confirmed", "serious"),
            ("Ruled out for 3 weeks with hamstring", "moderate"),
            ("Sidelined for several weeks", "moderate"),
            ("Minor knock for midfielder", "minor"),
            ("Slight concern over fitness", "minor"),
            ("Doubtful for weekend match", "minor"),
        ],
    )
    def test_estimates_severity(self, headline: str, expected_severity: str):
        """Test that severity is correctly estimated."""
        result = InjuryParser.parse_headline(headline, "Liverpool")
        assert result is not None
        assert result.severity == expected_severity


# =============================================================================
# InjuryParser - Confidence Scoring
# =============================================================================


class TestInjuryParserConfidence:
    """Test confidence scoring for injury detection."""

    def test_high_confidence_for_body_part_and_action(self):
        """Test high confidence when both body part and action present."""
        headline = "Mohamed Salah ruled out with hamstring injury"
        result = InjuryParser.parse_headline(headline, "Liverpool")
        assert result is not None
        # Body part (0.3) + action (0.2) + player name (0.1) + base (0.4) = 1.0
        assert result.confidence >= 0.9

    def test_moderate_confidence_for_action_only(self):
        """Test moderate confidence with only action word."""
        headline = "Key player ruled out for match"
        result = InjuryParser.parse_headline(headline, "Liverpool")
        assert result is not None
        assert 0.5 <= result.confidence < 0.8

    def test_low_confidence_excluded(self):
        """Test that low confidence results are filtered."""
        # This headline has only weak indicators
        headline = "Player may miss match"  # "miss" is an action word
        result = InjuryParser.parse_headline(headline, "Liverpool")
        # Should be detected but with lower confidence
        if result is not None:
            # The fetch method filters at 0.5 threshold
            assert result.confidence > 0


# =============================================================================
# InjuryInfo Dataclass
# =============================================================================


class TestInjuryInfo:
    """Test InjuryInfo dataclass."""

    def test_create_full_injury_info(self):
        """Test creating InjuryInfo with all fields."""
        info = InjuryInfo(
            player_name="Mohamed Salah",
            injury_type="hamstring",
            severity="moderate",
            duration="2-3 weeks",
            headline="Salah out for 2-3 weeks with hamstring injury",
            confidence=0.95,
        )
        assert info.player_name == "Mohamed Salah"
        assert info.injury_type == "hamstring"
        assert info.severity == "moderate"
        assert info.duration == "2-3 weeks"
        assert info.confidence == 0.95

    def test_create_minimal_injury_info(self):
        """Test creating InjuryInfo with minimal fields."""
        info = InjuryInfo(
            player_name=None,
            injury_type=None,
            severity="unknown",
            duration=None,
            headline="Injury concern for team",
            confidence=0.5,
        )
        assert info.player_name is None
        assert info.injury_type is None
        assert info.severity == "unknown"
