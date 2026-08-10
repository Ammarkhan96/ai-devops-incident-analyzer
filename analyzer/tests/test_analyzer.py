import analyzer


def test_database_fallback():

    result = analyzer.fallback_analysis([
        "ERROR database connection failed postgres",
        "ERROR orders API returning HTTP 503"
    ])

    assert result["severity"] == "HIGH"

    assert "Database" in result["title"]


def test_payment_fallback():

    result = analyzer.fallback_analysis([
        "ERROR payment provider timeout",
        "ERROR checkout request failed"
    ])

    assert result["severity"] == "HIGH"

    assert "Payment" in result["title"]


def test_cache_fallback():

    result = analyzer.fallback_analysis([
        "ERROR redis connection timeout",
        "ERROR session service unavailable"
    ])

    assert result["severity"] == "MEDIUM"

    assert "Redis" in result["title"]


def test_prompt_contains_logs():

    prompt = analyzer.build_prompt([
        "ERROR database unavailable"
    ])

    assert "database unavailable" in prompt

    assert "recommended_actions" in prompt
