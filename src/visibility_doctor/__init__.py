"""
Visibility Doctor - Airbnb Listing Visibility Analyzer
=======================================================

Analyzes Airbnb listings against competitors to identify visibility gaps
and generate prioritized action plans.

Uses:
- airbnb-scraper: For fetching listing data
- listing-grader: For algorithm-aligned scoring

Quick Start:
-----------
```python
from visibility_doctor import VisibilityDoctor

async with VisibilityDoctor() as doctor:
    result = await doctor.analyze("https://airbnb.com/rooms/12345")
    
    print(f"Score: {result.overall_score}/100")
    print(f"Visibility Loss: -{result.visibility_loss_percent}%")
    
    for action in result.quick_wins:
        print(f"• {action.title} (+{action.impact_percent}%)")
```

CLI Usage:
---------
```bash
visibility-doctor analyze https://airbnb.com/rooms/12345
visibility-doctor analyze 12345 --compare-market --output report.json
```
"""

__version__ = "1.0.0"
__author__ = "Rbie - AZUZ Project"

from .doctor import VisibilityDoctor, VisibilityDoctorResult
from .analyzer import GapAnalyzer, GapAnalysis, Gap
from .actions import ActionPlanGenerator, Action

__all__ = [
    # Main class
    "VisibilityDoctor",
    "VisibilityDoctorResult",
    
    # Gap analysis
    "GapAnalyzer",
    "GapAnalysis",
    "Gap",
    
    # Action planning
    "ActionPlanGenerator",
    "Action",
]
