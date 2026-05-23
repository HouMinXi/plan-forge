"""Tests for parse_verdict_response in llm/client.py.

Covers the brace-counting backstop that extracts a trailing JSON object
from prose output, in addition to the existing whole-text and
markdown-fenced-JSON paths.
"""
from __future__ import annotations

from plan_forge.llm.client import parse_verdict_response


class TestWholeTextJson:
    """Pre-existing behaviour: clean whole-text JSON is unchanged."""

    def test_clean_json_object(self):
        raw = (
            '{"verdict": "VERIFIED", "reason": "ok",'
            ' "cited_instances": [], "search_evidence": []}'
        )
        verdict, reasoning, ci, se = parse_verdict_response(raw)
        assert verdict == "VERIFIED"
        assert reasoning == "ok"
        assert ci == []
        assert se == []

    def test_unverified_token(self):
        raw = (
            '{"verdict": "UNVERIFIED", "reason": "x",'
            ' "cited_instances": [], "search_evidence": []}'
        )
        verdict, _, _, _ = parse_verdict_response(raw)
        assert verdict == "UNVERIFIED"


class TestMarkdownFenced:
    """Pre-existing behaviour: fenced JSON is stripped and parsed."""

    def test_fenced_json_block(self):
        raw = (
            "```json\n"
            '{"verdict": "VERIFIED", "reason": "ok",'
            ' "cited_instances": [], "search_evidence": []}\n'
            "```"
        )
        verdict, reasoning, _, _ = parse_verdict_response(raw)
        assert verdict == "VERIFIED"
        assert reasoning == "ok"


class TestProseWithTrailingJson:
    """Backstop: extract the last balanced {...} when whole-text fails."""

    def test_prose_plus_trailing_clean_json(self):
        raw = (
            "Here is my analysis of the claim.\n"
            "Based on the evidence, I conclude:\n"
            '{"verdict": "UNVERIFIED", "reason": "x",'
            ' "cited_instances": [], "search_evidence": []}'
        )
        verdict, reasoning, ci, se = parse_verdict_response(raw)
        assert verdict == "UNVERIFIED"
        assert reasoning == "x"
        assert ci == []
        assert se == []

    def test_prose_with_leading_unrelated_braces(self):
        """Only the last {...} is used; inner braces in prose are ignored."""
        raw = (
            "Consider the set {A, B, C} of items.\n"
            "Final answer:\n"
            '{"verdict": "VERIFIED", "reason": "found",'
            ' "cited_instances": [], "search_evidence": []}'
        )
        verdict, _, _, _ = parse_verdict_response(raw)
        assert verdict == "VERIFIED"


class TestNoJsonFallback:
    """When no parsable JSON with a verdict key exists, return raw_text."""

    def test_plain_prose_no_json(self):
        raw = "The claim is probably true but I cannot verify it."
        verdict, reasoning, ci, se = parse_verdict_response(raw)
        assert verdict == raw
        assert reasoning == ""
        assert ci == []
        assert se == []

    def test_trailing_json_missing_verdict_key(self):
        """A {...} block without 'verdict' must not be mis-extracted."""
        raw = (
            "Some prose output from the model.\n"
            '{"foo": "bar", "baz": 42}'
        )
        verdict, reasoning, ci, se = parse_verdict_response(raw)
        assert verdict == raw
        assert reasoning == ""

    def test_empty_string(self):
        verdict, reasoning, ci, se = parse_verdict_response("")
        assert verdict == ""
        assert reasoning == ""
