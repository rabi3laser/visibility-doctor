# 🏥 Visibility Doctor

**Airbnb listing visibility analyzer** - Identifies gaps vs competitors and generates prioritized action plans.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 What it does

Visibility Doctor analyzes your Airbnb listing against competitors to:

1. **Grade** your listing using Airbnb's 2025 ranking algorithm
2. **Identify gaps** vs local competitors (photos, pricing, amenities, etc.)
3. **Generate action plans** sorted by ROI (impact / effort)
4. **Find quick wins** - actions that take < 30 min and cost nothing

## 📦 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    visibility-doctor                         │
│                                                              │
│   Uses these packages (not duplicates them):                │
│   ├── airbnb-scraper   → Fetches listing & competitor data │
│   └── listing-grader   → Algorithm-aligned scoring          │
│                                                              │
│   Adds:                                                      │
│   ├── GapAnalyzer      → Compares you vs competitors        │
│   └── ActionPlanner    → Creates prioritized action plans   │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Installation

```bash
pip install git+https://github.com/rabi3laser/visibility-doctor.git
```

This automatically installs dependencies:
- `airbnb-scraper` from github.com/rabi3laser/airbnb-scraper
- `listing-grader` from github.com/rabi3laser/hosttools

## 💻 Usage

### Python API

```python
from visibility_doctor import VisibilityDoctor

async with VisibilityDoctor() as doctor:
    result = await doctor.analyze("https://airbnb.com/rooms/12345678")
    
    # Print summary
    result.print_summary()
    
    # Access data
    print(f"Score: {result.overall_score}/100")
    print(f"Visibility Loss: -{result.visibility_loss_percent}%")
    
    # Critical gaps
    for gap in result.gap_analysis["critical_gaps"]:
        print(f"🔴 {gap['title']}: {gap['description']}")
    
    # Quick wins
    for action in result.action_plan["quick_wins"]:
        print(f"⚡ {action['title']} (+{action['impact_percent']}%)")
```

### CLI

```bash
# Basic analysis
visibility-doctor analyze https://airbnb.com/rooms/12345678

# Short alias
vdoc analyze 12345678

# Save report to file
vdoc analyze 12345678 --output report.json

# JSON output to stdout
vdoc analyze 12345678 --json

# Skip market comparison (faster)
vdoc analyze 12345678 --no-market

# Custom settings
vdoc analyze 12345678 --currency USD --radius 10 --max-competitors 30
```

### Quick function

```python
from visibility_doctor import analyze_listing

# One-liner analysis
result = await analyze_listing("https://airbnb.com/rooms/12345678")
```

## 📊 Output Example

```
============================================================
🏥 VISIBILITY DOCTOR - DIAGNOSTIC
============================================================

📊 ANNONCE ANALYSÉE
────────────────────────────────────────
  ID:       12345678
  Nom:      Lovely Apartment in Paris
  Score:    72/100 (Grade: B-)

🔍 ANALYSE CONCURRENTIELLE
────────────────────────────────────────
  Concurrents analysés:    20
  Perte de visibilité:     -28%
  Gaps critiques:          2

✅ PLAN D'ACTION
────────────────────────────────────────
  Quick wins:              3
  Temps total:             4.5h
  Coût total:              €150
  Gain potentiel:          +35%

⚡ QUICK WINS RECOMMANDÉS
────────────────────────────────────────
  • Activer Instant Book (+15%)
  • Améliorer le temps de réponse (+8%)
  • Ajuster le prix (+5%)
```

## 🔍 Gap Categories

| Category | Description | Weight |
|----------|-------------|--------|
| `reviews` | Rating & review count | 25% |
| `response` | Response rate & time | 15% |
| `pricing` | Price vs market | 15% |
| `photos` | Photo count & quality | 12% |
| `settings` | Instant Book, etc. | 10% |
| `amenities` | Missing amenities | 8% |
| `badges` | Superhost, Guest Favorite | 7% |

## 🎬 Action Templates

The generator includes templates for common fixes:

- **Instant Book** - 5 min, free
- **Response time** - 15 min, free
- **Photos** - 3h, €0-100
- **Pricing** - 20 min, free
- **Amenities** - 1h, €50-200
- **Rating improvement** - ongoing, €50

## 🛠 Development

```bash
# Clone
git clone https://github.com/rabi3laser/visibility-doctor.git
cd visibility-doctor

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
ruff check src/
```

## 📁 Project Structure

```
visibility-doctor/
├── src/
│   └── visibility_doctor/
│       ├── __init__.py      # Package exports
│       ├── doctor.py        # Main VisibilityDoctor class
│       ├── analyzer.py      # GapAnalyzer
│       ├── actions.py       # ActionPlanGenerator
│       └── cli.py           # Command line interface
├── tests/
│   └── test_analyzer.py
├── pyproject.toml           # Package config
└── README.md
```

## 🔗 Related Packages

- [airbnb-scraper](https://github.com/rabi3laser/airbnb-scraper) - High-performance Airbnb scraping
- [listing-grader](https://github.com/rabi3laser/hosttools) - Algorithm-aligned listing scoring

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

**Made with ❤️ by Rbie - AZUZ Project**
