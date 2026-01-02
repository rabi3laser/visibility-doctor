"""
Gap Analyzer - Identifies visibility gaps vs competitors

Uses data models from:
- airbnb_scraper.ListingBasic (competitor data)
- listing_grader.ListingData (target listing)
- listing_grader.GradeResultV2 (scoring result)
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

from airbnb_scraper import ListingBasic
from listing_grader import ListingData, GradeResultV2, ESSENTIAL_AMENITIES


@dataclass
class Gap:
    """A gap between your listing and competitors"""
    category: str
    severity: str
    title: str
    description: str
    your_value: str
    market_value: str
    impact_percent: float
    fix_effort: str
    fix_cost: str
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GapAnalysis:
    """Complete gap analysis result"""
    listing_id: str
    competitors_count: int
    critical_gaps: List[Gap] = field(default_factory=list)
    important_gaps: List[Gap] = field(default_factory=list)
    minor_gaps: List[Gap] = field(default_factory=list)
    advantages: List[Gap] = field(default_factory=list)
    estimated_visibility_loss: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "listing_id": self.listing_id,
            "competitors_count": self.competitors_count,
            "critical_gaps": [g.to_dict() for g in self.critical_gaps],
            "important_gaps": [g.to_dict() for g in self.important_gaps],
            "minor_gaps": [g.to_dict() for g in self.minor_gaps],
            "advantages": [g.to_dict() for g in self.advantages],
            "estimated_visibility_loss": self.estimated_visibility_loss,
            "total_gaps": len(self.critical_gaps) + len(self.important_gaps) + len(self.minor_gaps),
            "total_advantages": len(self.advantages),
        }


class GapAnalyzer:
    """Analyzes gaps between a listing and its competitors."""
    
    def analyze(
        self, 
        target: ListingData, 
        competitors: List[ListingBasic],
        target_grade: GradeResultV2
    ) -> GapAnalysis:
        result = GapAnalysis(
            listing_id=target.listing_id,
            competitors_count=len(competitors)
        )
        
        if not competitors:
            return result
        
        market = self._calculate_market_stats(competitors)
        
        self._analyze_instant_book(target, market, result)
        self._analyze_photos(target, market, result)
        self._analyze_rating(target, target_grade, market, result)
        self._analyze_response(target, target_grade, market, result)
        self._analyze_pricing(target, market, result)
        self._analyze_amenities(target, competitors, result)
        self._analyze_superhost(target, market, result)
        self._analyze_guest_favorite(target, market, result)
        self._analyze_reviews_count(target, market, result)
        
        result.estimated_visibility_loss = sum(
            abs(gap.impact_percent) 
            for gap in result.critical_gaps + result.important_gaps + result.minor_gaps
        )
        
        return result
    
    def _calculate_market_stats(self, competitors: List[ListingBasic]) -> Dict:
        n = len(competitors)
        if n == 0:
            return {}
            
        return {
            "avg_photos": sum(len(c.images) for c in competitors) / n,
            "avg_rating": sum(c.rating for c in competitors if c.rating > 0) / max(1, sum(1 for c in competitors if c.rating > 0)),
            "avg_reviews": sum(c.reviews_count for c in competitors) / n,
            "avg_price": sum(c.price_per_night for c in competitors if c.price_per_night > 0) / max(1, sum(1 for c in competitors if c.price_per_night > 0)),
            "instant_book_pct": sum(1 for c in competitors if c.instant_bookable) / n * 100,
            "superhost_pct": sum(1 for c in competitors if c.is_superhost) / n * 100,
            "guest_favorite_pct": sum(1 for c in competitors if c.is_guest_favorite) / n * 100,
            "max_photos": max((len(c.images) for c in competitors), default=0),
            "max_reviews": max((c.reviews_count for c in competitors), default=0),
        }
    
    def _analyze_instant_book(self, target: ListingData, market: Dict, result: GapAnalysis):
        if not target.instant_bookable and market.get("instant_book_pct", 0) >= 70:
            result.critical_gaps.append(Gap(
                category="settings", severity="critical",
                title="Instant Book desactive",
                description=f"{market['instant_book_pct']:.0f}% des concurrents ont Instant Book active.",
                your_value="Desactive", market_value=f"{market['instant_book_pct']:.0f}%",
                impact_percent=-15.0, fix_effort="easy", fix_cost="free"
            ))
        elif target.instant_bookable:
            result.advantages.append(Gap(
                category="settings", severity="advantage",
                title="Instant Book active",
                description="Instant Book ameliore ton ranking.",
                your_value="Active", market_value=f"{market.get('instant_book_pct', 0):.0f}%",
                impact_percent=5.0, fix_effort="none", fix_cost="free"
            ))
    
    def _analyze_photos(self, target: ListingData, market: Dict, result: GapAnalysis):
        photo_count = len(target.images)
        avg = market.get("avg_photos", 15)
        diff = photo_count - avg
        
        if diff < -10:
            result.critical_gaps.append(Gap(
                category="photos", severity="critical",
                title="Nombre de photos insuffisant",
                description=f"Tu as {photo_count} photos vs {avg:.0f} en moyenne.",
                your_value=f"{photo_count} photos", market_value=f"{avg:.0f} (moy)",
                impact_percent=-15.0, fix_effort="medium", fix_cost="low"
            ))
        elif diff > 5:
            result.advantages.append(Gap(
                category="photos", severity="advantage",
                title="Excellent nombre de photos",
                description="Tu as plus de photos que la moyenne.",
                your_value=f"{photo_count} photos", market_value=f"{avg:.0f} en moyenne",
                impact_percent=5.0, fix_effort="none", fix_cost="free"
            ))
    
    def _analyze_rating(self, target: ListingData, grade: GradeResultV2, market: Dict, result: GapAnalysis):
        rating = target.rating
        avg_rating = market.get("avg_rating", 4.7)
        
        if rating < 4.5:
            result.critical_gaps.append(Gap(
                category="reviews", severity="critical",
                title="Rating critique",
                description="Un rating sous 4.5 reduit ta visibilite.",
                your_value=f"{rating:.2f}", market_value=f"{avg_rating:.2f} (moy)",
                impact_percent=-25.0, fix_effort="hard", fix_cost="free"
            ))
        elif rating >= 4.9:
            result.advantages.append(Gap(
                category="reviews", severity="advantage",
                title="Excellent rating",
                description="Ton rating de 4.9+ te qualifie pour Guest Favorites!",
                your_value=f"{rating:.2f}", market_value=f"{avg_rating:.2f}",
                impact_percent=10.0, fix_effort="none", fix_cost="free"
            ))
    
    def _analyze_response(self, target: ListingData, grade: GradeResultV2, market: Dict, result: GapAnalysis):
        if grade.response_score < 50:
            result.critical_gaps.append(Gap(
                category="response", severity="critical",
                title="Temps de reponse trop long",
                description="Un temps de reponse > 12h penalise ton ranking.",
                your_value=f"{target.response_time_hours:.0f}h", market_value="< 1h recommande",
                impact_percent=-15.0, fix_effort="easy", fix_cost="free"
            ))
    
    def _analyze_pricing(self, target: ListingData, market: Dict, result: GapAnalysis):
        avg_price = market.get("avg_price", 0)
        if avg_price <= 0 or target.price_per_night <= 0:
            return
            
        price_diff_pct = (target.price_per_night - avg_price) / avg_price
        
        if price_diff_pct > 0.35:
            result.critical_gaps.append(Gap(
                category="pricing", severity="critical",
                title="Prix tres au-dessus du marche",
                description=f"Ton prix est {price_diff_pct*100:.0f}% au-dessus de la moyenne.",
                your_value=f"{target.price_per_night:.0f}/nuit", market_value=f"{avg_price:.0f}/nuit",
                impact_percent=-20.0, fix_effort="easy", fix_cost="free"
            ))
    
    def _analyze_amenities(self, target: ListingData, competitors: List[ListingBasic], result: GapAnalysis):
        amenity_freq = {}
        for comp in competitors:
            for amenity in comp.amenities:
                amenity_lower = amenity.lower()
                amenity_freq[amenity_lower] = amenity_freq.get(amenity_lower, 0) + 1
        
        n = len(competitors)
        target_amenities = [a.lower() for a in target.amenities]
        
        missing_critical = []
        for amenity, count in amenity_freq.items():
            pct = count / n * 100
            if pct >= 70 and amenity not in target_amenities:
                if any(ea in amenity for ea in ESSENTIAL_AMENITIES):
                    missing_critical.append((amenity.title(), pct))
        
        if len(missing_critical) >= 3:
            amenities_list = ", ".join([a[0] for a in missing_critical[:5]])
            result.critical_gaps.append(Gap(
                category="amenities", severity="critical",
                title="Equipements essentiels manquants",
                description=f"Manquants: {amenities_list}",
                your_value=f"{len(target.amenities)} equipements", market_value=f"{len(missing_critical)} manquants",
                impact_percent=-12.0, fix_effort="medium", fix_cost="medium"
            ))
    
    def _analyze_superhost(self, target: ListingData, market: Dict, result: GapAnalysis):
        superhost_pct = market.get("superhost_pct", 0)
        
        if target.is_superhost:
            result.advantages.append(Gap(
                category="badges", severity="advantage",
                title="Statut Superhost",
                description="Le badge Superhost booste ta visibilite.",
                your_value="Superhost", market_value=f"{superhost_pct:.0f}%",
                impact_percent=8.0, fix_effort="none", fix_cost="free"
            ))
        elif superhost_pct >= 50:
            result.important_gaps.append(Gap(
                category="badges", severity="important",
                title="Pas de statut Superhost",
                description=f"{superhost_pct:.0f}% des concurrents sont Superhosts.",
                your_value="Non Superhost", market_value=f"{superhost_pct:.0f}%",
                impact_percent=-8.0, fix_effort="hard", fix_cost="free"
            ))
    
    def _analyze_guest_favorite(self, target: ListingData, market: Dict, result: GapAnalysis):
        gf_pct = market.get("guest_favorite_pct", 0)
        
        if target.is_guest_favorite:
            result.advantages.append(Gap(
                category="badges", severity="advantage",
                title="Badge Guest Favorite",
                description="Tu fais partie des annonces les mieux notees!",
                your_value="Guest Favorite", market_value=f"{gf_pct:.0f}%",
                impact_percent=12.0, fix_effort="none", fix_cost="free"
            ))
    
    def _analyze_reviews_count(self, target: ListingData, market: Dict, result: GapAnalysis):
        avg_reviews = market.get("avg_reviews", 20)
        
        if target.reviews_count < 5:
            result.critical_gaps.append(Gap(
                category="reviews", severity="critical",
                title="Trop peu d'avis",
                description="Moins de 5 avis = pas eligible Guest Favorites.",
                your_value=f"{target.reviews_count} avis", market_value=f"{avg_reviews:.0f} (moy)",
                impact_percent=-20.0, fix_effort="hard", fix_cost="free"
            ))
        elif target.reviews_count > avg_reviews * 1.5:
            result.advantages.append(Gap(
                category="reviews", severity="advantage",
                title="Excellent nombre d'avis",
                description="Ton nombre d'avis inspire confiance.",
                your_value=f"{target.reviews_count} avis", market_value=f"{avg_reviews:.0f} en moyenne",
                impact_percent=5.0, fix_effort="none", fix_cost="free"
            ))