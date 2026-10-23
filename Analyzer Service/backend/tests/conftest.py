"""Unit tests must never export to the developer's real Langfuse project."""
import os

os.environ["OBSERVABILITY_ENABLED"] = "false"
