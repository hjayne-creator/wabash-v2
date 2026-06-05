from app.research.prompts import (
    build_brave_research_message,
    build_openai_research_instructions,
    build_parallel_instructions,
    build_research_input,
    build_research_instructions,
)


def test_structured_research_instructions_match_openai_format():
    instructions = build_research_instructions()
    assert "# Role and Objective" in instructions
    assert "# Instructions" in instructions
    assert "# Output Format" in instructions
    assert "`product_found`" in instructions
    assert '"product_found": boolean' in instructions
    assert build_openai_research_instructions() == instructions


def test_research_input_is_search_focused():
    user_input = build_research_input(
        manufacturer_name="PEWAG",
        manufacturer_product_number="H4247SC",
    )
    assert "PEWAG" in user_input
    assert "H4247SC" in user_input
    assert "Search manufacturer websites" in user_input


def test_parallel_instructions_skip_redundant_schema():
    instructions = build_parallel_instructions()
    assert "# Role and Objective" in instructions
    assert "output schema" in instructions.lower()
    assert "```json" not in instructions


def test_brave_message_leads_with_user_query():
    message = build_brave_research_message(
        manufacturer_name="PEWAG",
        manufacturer_product_number="H4247SC",
    )
    assert message.startswith("Find specifications and datasheets for PEWAG part H4247SC")
    assert message.index("PEWAG") < message.index("# Role and Objective")
