"""
Action Plan Generator - Creates prioritized actions from gaps
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

from .analyzer import Gap, GapAnalysis


@dataclass
class Action:
    """An action to take to fix a gap"""
    id: str
    title: str
    description: str
    category: str
    priority: str
    time_minutes: int
    cost_eur: float
    impact_percent: float
    steps: List[str]
    gap_title: str
    roi_score: float = 0.0
    
    def calculate_roi(self) -> float:
        effort = (self.time_minutes / 60) + (self.cost_eur / 100)
        if effort <= 0:
            effort = 0.1
        self.roi_score = abs(self.impact_percent) / effort
        return self.roi_score
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @property
    def is_quick_win(self) -> bool:
        return self.time_minutes <= 30 and self.cost_eur == 0


@dataclass
class ActionPlan:
    """Complete action plan"""
    listing_id: str
    actions: List[Action] = field(default_factory=list)
    quick_wins: List[Action] = field(default_factory=list)
    total_time_hours: float = 0.0
    total_cost_eur: float = 0.0
    potential_gain_percent: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "listing_id": self.listing_id,
            "actions": [a.to_dict() for a in self.actions],
            "quick_wins": [a.to_dict() for a in self.quick_wins],
            "total_time_hours": round(self.total_time_hours, 1),
            "total_cost_eur": round(self.total_cost_eur, 0),
            "potential_gain_percent": round(self.potential_gain_percent, 0),
            "actions_count": len(self.actions),
            "quick_wins_count": len(self.quick_wins),
        }


class ActionPlanGenerator:
    """Generates prioritized action plans from gap analysis."""
    
    ACTION_TEMPLATES: Dict[str, Dict] = {
        "instant book": {
            "title": "Activer Instant Book",
            "category": "settings",
            "time_minutes": 5,
            "cost_eur": 0,
            "steps": ["Aller dans Annonce > Parametres", "Activer Reservation instantanee", "Sauvegarder"]
        },
        "photos": {
            "title": "Ajouter des photos de qualite",
            "category": "content",
            "time_minutes": 180,
            "cost_eur": 0,
            "steps": ["Prendre des photos en journee", "Ranger chaque piece", "Uploader dans l'ordre logique"]
        },
        "temps de reponse": {
            "title": "Ameliorer le temps de reponse",
            "category": "response",
            "time_minutes": 15,
            "cost_eur": 0,
            "steps": ["Activer notifications push", "Creer reponses rapides", "Bloquer 10 min matin/soir"]
        },
        "rating": {
            "title": "Ameliorer le rating",
            "category": "reviews",
            "time_minutes": 120,
            "cost_eur": 50,
            "steps": ["Analyser commentaires negatifs", "Ameliorer proprete", "Ajouter petites attentions"]
        },
        "avis": {
            "title": "Obtenir plus d'avis",
            "category": "reviews",
            "time_minutes": 30,
            "cost_eur": 0,
            "steps": ["Message personnalise apres checkout", "Laisser avis pour le voyageur", "Prix attractif debut"]
        },
        "prix": {
            "title": "Ajuster le prix",
            "category": "pricing",
            "time_minutes": 20,
            "cost_eur": 0,
            "steps": ["Analyser prix concurrents", "Activer prix dynamique", "Mettre reductions semaine/mois"]
        },
        "equipements": {
            "title": "Ajouter des equipements essentiels",
            "category": "amenities",
            "time_minutes": 60,
            "cost_eur": 150,
            "steps": ["Lister equipements manquants", "Acheter et installer", "Mettre a jour l'annonce"]
        },
        "superhost": {
            "title": "Atteindre le statut Superhost",
            "category": "badges",
            "time_minutes": 0,
            "cost_eur": 0,
            "steps": ["Maintenir rating 4.8+", "Repondre a 90%+ messages", "Ne jamais annuler"]
        },
    }
    
    def generate(self, gap_analysis: GapAnalysis) -> ActionPlan:
        plan = ActionPlan(listing_id=gap_analysis.listing_id)
        
        all_gaps = (
            [(g, "critical") for g in gap_analysis.critical_gaps] +
            [(g, "high") for g in gap_analysis.important_gaps] +
            [(g, "medium") for g in gap_analysis.minor_gaps]
        )
        
        for i, (gap, priority) in enumerate(all_gaps):
            action = self._create_action(gap, priority, i)
            if action:
                action.calculate_roi()
                plan.actions.append(action)
        
        plan.actions.sort(key=lambda a: a.roi_score, reverse=True)
        plan.quick_wins = [a for a in plan.actions if a.is_quick_win]
        
        plan.total_time_hours = sum(a.time_minutes for a in plan.actions) / 60
        plan.total_cost_eur = sum(a.cost_eur for a in plan.actions)
        plan.potential_gain_percent = sum(a.impact_percent for a in plan.actions)
        
        return plan
    
    def _create_action(self, gap: Gap, priority: str, index: int) -> Optional[Action]:
        template = None
        gap_title_lower = gap.title.lower()
        
        for key, tmpl in self.ACTION_TEMPLATES.items():
            if key in gap_title_lower:
                template = tmpl
                break
        
        if not template:
            template = {
                "title": f"Corriger: {gap.title}",
                "category": gap.category,
                "time_minutes": 60,
                "cost_eur": 0,
                "steps": ["Analyser le probleme", "Implementer la solution", "Verifier le resultat"]
            }
        
        return Action(
            id=f"action_{index + 1:02d}",
            title=template["title"],
            description=gap.description,
            category=template.get("category", gap.category),
            priority=priority,
            time_minutes=template["time_minutes"],
            cost_eur=template["cost_eur"],
            impact_percent=abs(gap.impact_percent),
            steps=template["steps"],
            gap_title=gap.title
        )