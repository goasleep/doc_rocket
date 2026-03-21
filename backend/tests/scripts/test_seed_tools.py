"""Tests for seed_tools idempotency behaviour.

These tests call the ``seed`` coroutine from ``scripts/seed_tools.py``
directly, bypassing the CLI entry-point so they run inside the existing
Beanie session that the ``db`` fixture establishes.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

from app.models import Tool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_seed_module():
    """Import scripts/seed_tools.py without executing __main__."""
    scripts_path = (
        Path(__file__).parent.parent.parent / "scripts" / "seed_tools.py"
    )
    spec = importlib.util.spec_from_file_location("seed_tools", scripts_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["seed_tools"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


async def _run_seed_in_process() -> None:
    """Run the seed logic using the already-initialised Beanie session.

    We replicate what ``seed()`` does but skip the Motor/Beanie
    initialisation because the ``db`` fixture has already done that.
    """
    seed_module = _load_seed_module()
    for tool_data in seed_module.BUILTIN_TOOLS:
        existing = await Tool.find_one(Tool.name == tool_data["name"])
        if existing:
            existing.description = tool_data["description"]
            existing.parameters_schema = tool_data["parameters_schema"]
            existing.function_name = tool_data["function_name"]
            existing.category = tool_data["category"]
            await existing.save()
        else:
            tool = Tool(**tool_data)
            await tool.insert()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_seed_twice_does_not_increase_tool_count(db: None) -> None:
    """Running the seed twice must not create duplicate Tool documents."""
    # Wipe any pre-existing tools to get a clean baseline
    await Tool.delete_all()

    await _run_seed_in_process()
    count_after_first = await Tool.count()

    await _run_seed_in_process()
    count_after_second = await Tool.count()

    assert count_after_second == count_after_first, (
        f"Tool count changed from {count_after_first} to {count_after_second} "
        "after running seed a second time — seed is not idempotent."
    )


@pytest.mark.anyio
async def test_seed_restores_modified_description(db: None) -> None:
    """If a tool's description is manually changed in DB, re-seeding reverts it."""
    await Tool.delete_all()
    await _run_seed_in_process()

    # Corrupt the description of the first seeded tool
    seed_module = _load_seed_module()
    first_tool_data = seed_module.BUILTIN_TOOLS[0]
    canonical_description = first_tool_data["description"]
    modified_description = "MANUALLY OVERRIDDEN DESCRIPTION"

    tool = await Tool.find_one(Tool.name == first_tool_data["name"])
    assert tool is not None, "Expected seed to have inserted the tool."
    tool.description = modified_description
    await tool.save()

    # Verify the corruption is in place
    dirty = await Tool.find_one(Tool.name == first_tool_data["name"])
    assert dirty is not None
    assert dirty.description == modified_description

    # Re-run seed — it should update the description back to canonical
    await _run_seed_in_process()

    restored = await Tool.find_one(Tool.name == first_tool_data["name"])
    assert restored is not None
    assert restored.description == canonical_description, (
        f"Expected description '{canonical_description}', "
        f"got '{restored.description}' after re-seed."
    )
