"""Tests for rate limiting configuration."""

from src.core.rate_limit import parse_redis_url


class TestParseRedisUrl:
    """Tests for parse_redis_url function."""

    def test_empty_url(self):
        """Should return empty string for empty input."""
        assert parse_redis_url("") == ""

    def test_simple_redis_url(self):
        """Should pass through simple redis:// URL."""
        url = "redis://localhost:6379"
        assert parse_redis_url(url) == url

    def test_simple_rediss_url(self):
        """Should pass through simple rediss:// URL (TLS)."""
        url = "rediss://localhost:6379"
        assert parse_redis_url(url) == url

    def test_redis_url_with_auth(self):
        """Should pass through URL with authentication."""
        url = "redis://user:password@localhost:6379"
        assert parse_redis_url(url) == url

    def test_upstash_url(self):
        """Should handle Upstash-style URLs."""
        url = "rediss://default:token@host.upstash.io:6379"
        assert parse_redis_url(url) == url

    def test_redis_cli_command_extraction(self):
        """Should extract URL from redis-cli command."""
        cmd = "redis-cli --tls -u redis://default:token@host.upstash.io:6379"
        expected = "rediss://default:token@host.upstash.io:6379"
        assert parse_redis_url(cmd) == expected

    def test_redis_cli_without_tls_flag(self):
        """Should extract URL without converting scheme if no --tls flag."""
        cmd = "redis-cli -u redis://localhost:6379"
        expected = "redis://localhost:6379"
        assert parse_redis_url(cmd) == expected

    def test_redis_cli_with_rediss_scheme(self):
        """Should preserve rediss:// scheme from command."""
        cmd = "redis-cli --tls -u rediss://default:token@host.upstash.io:6379"
        expected = "rediss://default:token@host.upstash.io:6379"
        assert parse_redis_url(cmd) == expected

    def test_tls_flag_converts_scheme(self):
        """Should convert redis:// to rediss:// when --tls flag present."""
        cmd = "redis-cli --tls -u redis://default:token@host:6379"
        expected = "rediss://default:token@host:6379"
        assert parse_redis_url(cmd) == expected

    def test_complex_upstash_url(self):
        """Should handle real Upstash connection string."""
        cmd = "redis-cli --tls -u redis://default:AZd_AAIncDJlNjQwMTRhMDFiYWE0YjE3OTNlMDVlNjlkOTJmOGQwZHAyMzg3ODM@splendid-muskrat-38783.upstash.io:6379"
        expected = "rediss://default:AZd_AAIncDJlNjQwMTRhMDFiYWE0YjE3OTNlMDVlNjlkOTJmOGQwZHAyMzg3ODM@splendid-muskrat-38783.upstash.io:6379"
        assert parse_redis_url(cmd) == expected

    def test_invalid_string(self):
        """Should return original string if no valid URL found."""
        invalid = "some random string"
        assert parse_redis_url(invalid) == invalid
