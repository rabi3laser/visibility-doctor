"""
Action Plan Generator - Creates prioritized actions from gaps

Generates actionable steps to fix visibility gaps,
sorted by ROI (impact / effort).
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
    priority: str  # critical, high, medium, low
    time_minutes: int
    cost_eur: float
    impact_percent: float
    steps: List[str]
    gap_title: str
    roi_score: float = 0.0
    
    def calculate_roi(self) -> float:
        """Calculate ROI score (higher = better)"""
        effort = (self.time_minutes / 60) + (self.cost_eur / 100)
        if effort <= 0:
            effort = 0.1
        self.roi_score = abs(self.impact_percent) / effort
        return self.roi_score
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @property
    def is_quick_win(self) -> bool:
        """A quick win is < 30 min and free"""
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
    """
    Generates prioritized action plans from gap analysis.
    
    Actions are sorted by ROI (impact / effort).
    Quick wins are actions that take < 30 min and cost nothing.
    
    Example:
        generator = ActionPlanGenerator()
        plan = generator.generate(gap_analysis)
        
        for action in plan.quick_wins:
            print(f"⚡ {action.title} - {action.time_minutes} min")
    """
    
    # Action templates with time/cost estimates
    ACTION_TEMPLATES: Dict[str, Dict] = {
        # Instant Book
        "instant book": {
            "title": "Activer Instant Book",
            "category": "settings",
            "time_minutes": 5,
            "cost_eur": 0,
            "steps": [
                "Aller dans Annonce > Paramètres de réservation",
                "Activer 'Réservation instantanée'",
                "Choisir les conditions (vérification ID, etc.)",
                "Sauvegarder les modifications"
            ]
        },
        
        # Photos
        "photos": {
            "title": "Ajouter des photos de qualité",
            "category": "content",
            "time_minutes": 180,
            "cost_eur": 0,
            "steps": [
                "Prendre des photos en journée (lumière naturelle)",
                "Ranger et nettoyer chaque pièce avant",
                "Photographier chaque espace (chambre, salon, cuisine, salle de bain, extérieur)",
                "Prendre des photos des détails (déco, équipements, vue)",
                "Éditer les photos (luminosité, cadrage)",
                "Uploader dans l'ordre logique (extérieur → pièces principales → détails)"
            ]
        },
        
        # Response time
        "temps de réponse": {
            "title": "Améliorer le temps de réponse",
            "category": "response",
            "time_minutes": 15,
            "cost_eur": 0,
            "steps": [
                "Activer les notifications push sur l'app Airbnb",
                "Créer 3-5 réponses rapides préenregistrées",
                "Configurer des alertes email/SMS",
                "Bloquer 10 min matin et soir pour répondre"
            ]
        },
        
        # Rating / Reviews
        "rating": {
            "title": "Améliorer le rating",
            "category": "reviews",
            "time_minutes": 120,
            "cost_eur": 50,
            "steps": [
                "Analyser les 10 derniers commentaires négatifs",
                "Identifier les problèmes récurrents",
                "Améliorer la propreté (checklist détaillée)",
                "Ajouter des petites attentions (café, snacks, guide local)",
                "Communication proactive avant/pendant/après séjour",
                "Demander un feedback privé avant le checkout"
            ]
        },
        
        # Reviews count
        "avis": {
            "title": "Obtenir plus d'avis",
            "category": "reviews",
            "time_minutes": 30,
            "cost_eur": 0,
            "steps": [
                "Envoyer un message personnalisé après le checkout",
                "Rappeler gentiment l'importance des avis",
                "Laisser un avis pour le voyageur (déclenche souvent un avis en retour)",
                "Offrir une réduction pour le prochain séjour",
                "Proposer un prix attractif pour les premiers guests"
            ]
        },
        
        # Pricing
        "prix": {
            "title": "Ajuster le prix",
            "category": "pricing",
            "time_minutes": 20,
            "cost_eur": 0,
            "steps": [
                "Analyser les prix des 10 concurrents les plus proches",
                "Activer le prix dynamique (Smart Pricing) ou utiliser PriceLabs",
                "Mettre des réductions semaine (-10%) et mois (-20%)",
                "Créer une promotion pour les 3 prochains mois",
                "Ajuster selon la saison et les événements locaux"
            ]
        },
        
        # Amenities
        "équipements": {
            "title": "Ajouter des équipements essentiels",
            "category": "amenities",
            "time_minutes": 60,
            "cost_eur": 150,
            "steps": [
                "Lister les équipements manquants vs concurrents",
                "Prioriser: Wifi rapide, climatisation, cuisine équipée",
                "Acheter les équipements manquants",
                "Installer et tester",
                "Mettre à jour l'annonce avec les nouveaux équipements",
                "Prendre des photos des nouveaux équipements"
            ]
        },
        
        # Superhost
        "superhost": {
            "title": "Atteindre le statut Superhost",
            "category": "badges",
            "time_minutes": 0,  # Ongoing effort
            "cost_eur": 0,
            "steps": [
                "Maintenir un rating de 4.8+ (vérifier chaque avis)",
                "Répondre à 90%+ des messages dans les 24h",
                "Compléter au moins 10 séjours/an",
                "Ne jamais annuler (0% taux d'annulation)",
                "Vérifier ta progression dans le dashboard Airbnb"
            ]
        },
        
        # Guest Favorite
        "guest favorite": {
            "title": "Viser le badge Guest Favorite",
            "category": "badges",
            "time_minutes": 0,
            "cost_eur": 0,
            "steps": [
                "Atteindre un rating de 4.9+ (priorité absolue)",
                "Avoir au moins 5 avis",
                "Maintenir un taux d'annulation < 1%",
                "Exceller dans les 6 sous-catégories (propreté, précision, etc.)",
                "Être dans le top 10% de ta zone"
            ]
        },
    }
    
    def generate(self, gap_analysis: GapAnalysis) -> ActionPlan:
        """
        Generate action plan from gap analysis.
        
        Args:
            gap_analysis: GapAnalysis from GapAnalyzer
            
        Returns:
            ActionPlan with prioritized actions
        """
        plan = ActionPlan(listing_id=gap_analysis.listing_id)
        
        # Process all gaps
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
        
        # Sort by ROI (highest first)
        plan.actions.sort(key=lambda a: a.roi_score, reverse=True)
        
        # Extract quick wins
        plan.quick_wins = [a for a in plan.actions if a.is_quick_win]
        
        # Calculate totals
        plan.total_time_hours = sum(a.time_minutes for a in plan.actions) / 60
        plan.total_cost_eur = sum(a.cost_eur for a in plan.actions)
        plan.potential_gain_percent = sum(a.impact_percent for a in plan.actions)
        
        return plan
    
    def _create_action(self, gap: Gap, priority: str, index: int) -> Optional[Action]:
        """Create an action from a gap using templates"""
        
        # Find matching template
        template = None
        gap_title_lower = gap.title.lower()
        
        for key, tmpl in self.ACTION_TEMPLATES.items():
            if key in gap_title_lower:
                template = tmpl
                break
        
        # Default template if no match
        if not template:
            template = {
                "title": f"Corriger: {gap.title}",
                "category": gap.category,
                "time_minutes": 60,
                "cost_eur": 0,
                "steps": [
                    "Analyser le problème en détail",
                    "Rechercher les solutions possibles",
                    "Implémenter la solution choisie",
                    "Vérifier le résultat",
                    "Mettre à jour l'annonce si nécessaire"
                ]
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
    
    def generate_summary(self, plan: ActionPlan) -> str:
        """Generate a human-readable summary of the action plan"""
        lines = [
            "=" * 50,
            "📋 PLAN D'ACTION",
            "=" * 50,
            f"Actions totales: {len(plan.actions)}",
            f"Quick wins: {len(plan.quick_wins)}",
            f"Temps total: {plan.total_time_hours:.1f}h",
            f"Coût total: €{plan.total_cost_eur:.0f}",
            f"Gain potentiel: +{plan.potential_gain_percent:.0f}% visibilité",
            "",
        ]
        
        if plan.quick_wins:
            lines.append("⚡ QUICK WINS (< 30 min, gratuits)")
            lines.append("-" * 40)
            for qw in plan.quick_wins[:5]:
                lines.append(f"  • {qw.title} (+{qw.impact_percent:.0f}%)")
            lines.append("")
        
        lines.append("🎯 TOUTES LES ACTIONS (par ROI)")
        lines.append("-" * 40)
        for action in plan.actions[:10]:
            emoji = "🔴" if action.priority == "critical" else "🟡" if action.priority == "high" else "🟢"
            lines.append(f"  {emoji} {action.title}")
            lines.append(f"     Impact: +{action.impact_percent:.0f}% | Temps: {action.time_minutes} min | Coût: €{action.cost_eur:.0f}")
        
        return "\n".join(lines)
