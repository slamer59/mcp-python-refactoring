#!/usr/bin/env python3
"""
Vulture-based dead code analyzer
"""

import ast
from typing import List

import vulture

from ..models import RefactoringGuidance
from .base import BaseAnalyzer


class VultureAnalyzer(BaseAnalyzer):
    """Analyzer using Vulture for dead code detection"""

    def analyze(self, content: str, file_path: str, tree: ast.AST = None) -> List[RefactoringGuidance]:
        """Use Vulture to find dead code"""
        guidance_list = []

        try:
            v = vulture.Vulture()
            v.scan(content, filename=file_path)

            unused_items = list(v.get_unused_code())

            if unused_items:
                # Consolidate all dead code into single guidance
                items_list = []
                locations = []

                for unused_item in unused_items:
                    items_list.append(
                        f"Line {unused_item.first_lineno}: Unused {unused_item.typ} '{unused_item.name}'"
                    )
                    locations.append(f"Line {unused_item.first_lineno}")

                guidance_list.append(
                    RefactoringGuidance(
                        issue_type="dead_code",
                        severity="low",
                        location=f"Multiple locations ({len(unused_items)} items)",
                        description=f"{len(unused_items)} unused items found",
                        benefits=[
                            "Cleaner codebase",
                            "Reduced complexity",
                            "Better maintainability",
                        ],
                        precise_steps=[
                            "1. Review all unused items listed below:",
                            *[f"   • {item}" for item in items_list],
                            "2. Verify each item is truly unused",
                            "3. Check if any are part of a public API",
                            "4. Remove confirmed unused code",
                            "5. Run tests to ensure nothing breaks",
                        ],
                        metrics={
                            "total_items": len(unused_items),
                            "confidence": sum(item.confidence for item in unused_items)
                            / len(unused_items),
                        },
                    )
                )

        except Exception as e:
            print(f"Warning: Vulture analysis failed: {e}")

        return guidance_list