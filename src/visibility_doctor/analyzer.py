"""
Gap Analyzer - Identifies visibility gaps vs competitors

Uses data models from:
- airbnb_scraper.ListingBasic (competitor data)
- listing_grader.ListingData (target listing)
- listing_grader.GradeResultV2 (scoring result)
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

# Import from YOUR existing packages
from airbnb_scraper import ListingBasic
from listing_grader import ListingData, GradeResultV2, ESSENTIAL_AMENITIES


@dataclass
class Gap:
    """A gap between your listing and competitors"""
    category: str
    severity: str  # critical, important, minor, advantage
    title: str
    description: str
    your_value: str
    market_value: str
    impact_percent: float
    fix_effort: str  # easy, medium, hard
    fix_cost: str  # free, low, medium, high
    
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
    """
    Analyzes gaps between a listing and its competitors.
    
    Uses real data from AirbnbScraper and ListingGraderV2.
    
    Example:
        analyzer = GapAnalyzer()
        gaps = analyzer.analyze(listing_data, competitors, grade_result)
        
        for gap in gaps.critical_gaps:
            print(f"🔴 {gap.title}: {gap.description}")
    """
    
    def analyze(
        self, 
        target: ListingData, 
        competitors: List[ListingBasic],
        target_grade: GradeResultV2
    ) -> GapAnalysis:
        """
        Analyze gaps between target listing and competitors.
        
        Args:
            target: ListingData from listing_grader
            competitors: List of ListingBasic from airbnb_scraper
            target_grade: GradeResultV2 from listing_grader
            
        Returns:
            GapAnalysis with categorized gaps and advantages
        """
        result = GapAnalysis(
            listing_id=target.listing_id,
            competitors_count=len(competitors)
        )
        
        if not competitors:
            return result
        
        # Calculate market averages from real competitor data
        market = self._calculate_market_stats(competitors)
        
        # Analyze each category
        self._analyze_instant_book(target, market, result)
        self._analyze_photos(target, market, result)
        self._analyze_rating(target, target_grade, market, result)
        self._analyze_response(target, target_grade, market, result)
        self._analyze_pricing(target, market, result)
        self._analyze_amenities(target, competitors, result)
        self._analyze_superhost(target, market, result)
        self._analyze_guest_favorite(target, market, result)
        self._analyze_reviews_count(target, market, result)
        
        # Calculate total visibility loss
        result.estimated_visibility_loss = sum(
            abs(gap.impact_percent) 
            for gap in result.critical_gaps + result.important_gaps + result.minor_gaps
        )
        
        return result
    
    def _calculate_market_stats(self, competitors: List[ListingBasic]) -> Dict:
        """Calculate market averages from competitor ListingBasic objects"""
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
            "median_price": sorted([c.price_per_night for c in competitors if c.price_per_night > 0])[n//2] if n > 0 else 0,
        }
    
    def _analyze_instant_book(self, target: ListingData, market: Dict, result: GapAnalysis):
        """Analyze Instant Book gap"""
        if not target.instant_bookable and market.get("instant_book_pct", 0) >= 70:
            result.critical_gaps.append(Gap(
                category="settings",
                severity="critical",
                title="Instant Book désactivé",
                description=f"{market['instant_book_pct']:.0f}% des concurrents ont Instant Book activé. C'est un facteur majeur de ranking Airbnb.",
                your_value="Désactivé",
                market_value=f"{market['instant_book_pct']:.0f}% des concurrents",
                impact_percent=-15.0,
                fix_effort="easy",
                fix_cost="free"
            ))
        elif not target.instant_bookable and market.get("instant_book_pct", 0) >= 50:
            result.important_gaps.append(Gap(
                category="settings",
                severity="important",
                title="Instant Book désactivé",
                description=f"{market['instant_book_pct']:.0f}% des concurrents ont Instant Book. Considère l'activer.",
                your_value="Désactivé",
                market_value=f"{market['instant_book_pct']:.0f}% des concurrents",
                impact_percent=-10.0,
                fix_effort="easy",
                fix_cost="free"
            ))
        elif target.instant_bookable:
            result.advantages.append(Gap(
                category="settings",
                severity="advantage",
                title="Instant Book activé",
                description="Instant Book améliore ton ranking et facilite les réservations.",
                your_value="Activé ✓",
                market_value=f"{market.get('instant_book_pct', 0):.0f}% des concurrents",
                impact_percent=5.0,
                fix_effort="none",
                fix_cost="free"
            ))
    
    def _analyze_photos(self, target: ListingData, market: Dict, result: GapAnalysis):
        """Analyze photos gap"""
        photo_count = len(target.images)
        avg = market.get("avg_photos", 15)
        diff = photo_count - avg
        
        if diff < -10:
            result.critical_gaps.append(Gap(
                category="photos",
                severity="critical",
                title="Nombre de photos insuffisant",
                description=f"Tu as {photo_count} photos vs {avg:.0f} en moyenne chez les concurrents. Les photos sont le facteur #1 de conversion.",
                your_value=f"{photo_count} photos",
                market_value=f"{avg:.0f} (moy), {market.get('max_photos', 0)} (max)",
                impact_percent=-15.0,
                fix_effort="medium",
                fix_cost="low"
            ))
        elif diff < -5:
            result.important_gaps.append(Gap(
                category="photos",
                severity="important",
                title="Photos en dessous de la moyenne",
                description=f"Ajoute {abs(diff):.0f} photos pour atteindre la moyenne du marché.",
                your_value=f"{photo_count} photos",
                market_value=f"{avg:.0f} en moyenne",
                impact_percent=-8.0,
                fix_effort="easy",
                fix_cost="free"
            ))
        elif diff > 5:
            result.advantages.append(Gap(
                category="photos",
                severity="advantage",
                title="Excellent nombre de photos",
                description="Tu as plus de photos que la moyenne, c'est un avantage pour la conversion.",
                your_value=f"{photo_count} photos",
                market_value=f"{avg:.0f} en moyenne",
                impact_percent=5.0,
                fix_effort="none",
                fix_cost="free"
            ))
    
    def _analyze_rating(self, target: ListingData, grade: GradeResultV2, market: Dict, result: GapAnalysis):
        """Analyze rating gap"""
        rating = target.rating
        avg_rating = market.get("avg_rating", 4.7)
        rating_diff = rating - avg_rating
        
        if rating < 4.5:
            result.critical_gaps.append(Gap(
                category="reviews",
                severity="critical",
                title="Rating critique",
                description="Un rating sous 4.5 réduit drastiquement ta visibilité dans les recherches Airbnb.",
                your_value=f"{rating:.2f}★",
                market_value=f"{avg_rating:.2f}★ (moy)",
                impact_percent=-25.0,
                fix_effort="hard",
                fix_cost="free"
            ))
        elif rating < 4.8 and rating_diff < -0.2:
            result.important_gaps.append(Gap(
                category="reviews",
                severity="important",
                title="Rating en dessous du marché",
                description=f"Ton rating est {abs(rating_diff):.2f} points en dessous de la moyenne. Vise 4.8+ pour Guest Favorites.",
                your_value=f"{rating:.2f}★",
                market_value=f"{avg_rating:.2f}★",
                impact_percent=-12.0,
                fix_effort="hard",
                fix_cost="free"
            ))
        elif rating >= 4.9:
            result.advantages.append(Gap(
                category="reviews",
                severity="advantage",
                title="Excellent rating",
                description="Ton rating de 4.9+ te qualifie potentiellement pour Guest Favorites!",
                your_value=f"{rating:.2f}★",
                market_value=f"{avg_rating:.2f}★",
                impact_percent=10.0,
                fix_effort="none",
                fix_cost="free"
            ))
        elif rating_diff > 0.1:
            result.advantages.append(Gap(
                category="reviews",
                severity="advantage",
                title="Rating supérieur au marché",
                description="Ton rating est au-dessus de la moyenne locale.",
                your_value=f"{rating:.2f}★",
                market_value=f"{avg_rating:.2f}★",
                impact_percent=5.0,
                fix_effort="none",
                fix_cost="free"
            ))
    
    def _analyze_response(self, target: ListingData, grade: GradeResultV2, market: Dict, result: GapAnalysis):
        """Analyze response time gap"""
        if grade.response_score < 50:
            result.critical_gaps.append(Gap(
                category="response",
                severity="critical",
                title="Temps de réponse trop long",
                description="Un temps de réponse > 12h pénalise fortement ton ranking. Airbnb privilégie les hôtes réactifs.",
                your_value=f"{target.response_time_hours:.0f}h",
                market_value="< 1h recommandé",
                impact_percent=-15.0,
                fix_effort="easy",
                fix_cost="free"
            ))
        elif grade.response_score < 70:
            result.important_gaps.append(Gap(
                category="response",
                severity="important",
                title="Temps de réponse à améliorer",
                description="Vise un temps de réponse < 1h pour maximiser ton ranking.",
                your_value=f"{target.response_time_hours:.0f}h",
                market_value="< 1h recommandé",
                impact_percent=-8.0,
                fix_effort="easy",
                fix_cost="free"
            ))
        elif target.response_rate >= 98 and target.response_time_hours <= 1:
            result.advantages.append(Gap(
                category="response",
                severity="advantage",
                title="Excellent temps de réponse",
                description="Ta réactivité est un atout majeur pour le ranking.",
                your_value=f"{target.response_time_hours:.0f}h, {target.response_rate}%",
                market_value="< 1h recommandé",
                impact_percent=5.0,
                fix_effort="none",
                fix_cost="free"
            ))
    
    def _analyze_pricing(self, target: ListingData, market: Dict, result: GapAnalysis):
        """Analyze pricing gap"""
        avg_price = market.get("avg_price", 0)
        if avg_price <= 0 or target.price_per_night <= 0:
            return
            
        price_diff_pct = (target.price_per_night - avg_price) / avg_price
        
        if price_diff_pct > 0.35:
            result.critical_gaps.append(Gap(
                category="pricing",
                severity="critical",
                title="Prix très au-dessus du marché",
                description=f"Ton prix est {price_diff_pct*100:.0f}% au-dessus de la moyenne. Cela peut drastiquement réduire tes réservations.",
                your_value=f"€{target.price_per_night:.0f}/nuit",
                market_value=f"€{avg_price:.0f}/nuit (moy)",
                impact_percent=-20.0,
                fix_effort="easy",
                fix_cost="free"
            ))
        elif price_diff_pct > 0.20:
            result.important_gaps.append(Gap(
                category="pricing",
                severity="important",
                title="Prix au-dessus du marché",
                description=f"Ton prix est {price_diff_pct*100:.0f}% au-dessus. Assure-toi que ta qualité justifie ce premium.",
                your_value=f"€{target.price_per_night:.0f}/nuit",
                market_value=f"€{avg_price:.0f}/nuit",
                impact_percent=-12.0,
                fix_effort="easy",
                fix_cost="free"
            ))
        elif -0.10 <= price_diff_pct <= 0.05:
            result.advantages.append(Gap(
                category="pricing",
                severity="advantage",
                title="Prix compétitif",
                description="Ton prix est bien positionné par rapport au marché.",
                your_value=f"€{target.price_per_night:.0f}/nuit",
                market_value=f"€{avg_price:.0f}/nuit",
                impact_percent=5.0,
                fix_effort="none",
                fix_cost="free"
            ))
        elif price_diff_pct < -0.25:
            result.minor_gaps.append(Gap(
                category="pricing",
                severity="minor",
                title="Prix potentiellement trop bas",
                description=f"Ton prix est {abs(price_diff_pct)*100:.0f}% en dessous du marché. Tu pourrais augmenter tes revenus.",
                your_value=f"€{target.price_per_night:.0f}/nuit",
                market_value=f"€{avg_price:.0f}/nuit",
                impact_percent=0.0,  # Not a visibility issue
                fix_effort="easy",
                fix_cost="free"
            ))
    
    def _analyze_amenities(self, target: ListingData, competitors: List[ListingBasic], result: GapAnalysis):
        """Analyze amenities gap"""
        # Count amenity frequency across competitors
        amenity_freq = {}
        for comp in competitors:
            for amenity in comp.amenities:
                amenity_lower = amenity.lower()
                amenity_freq[amenity_lower] = amenity_freq.get(amenity_lower, 0) + 1
        
        n = len(competitors)
        target_amenities = [a.lower() for a in target.amenities]
        
        # Find missing common amenities (present in 70%+ of competitors)
        missing_critical = []
        for amenity, count in amenity_freq.items():
            pct = count / n * 100
            if pct >= 70 and amenity not in target_amenities:
                # Check if it's an essential amenity
                if any(ea in amenity for ea in ESSENTIAL_AMENITIES):
                    missing_critical.append((amenity.title(), pct))
        
        if len(missing_critical) >= 3:
            amenities_list = ", ".join([f"{a[0]} ({a[1]:.0f}%)" for a in missing_critical[:5]])
            result.critical_gaps.append(Gap(
                category="amenities",
                severity="critical",
                title="Équipements essentiels manquants",
                description=f"Ces équipements sont présents chez 70%+ des concurrents: {amenities_list}",
                your_value=f"{len(target.amenities)} équipements",
                market_value=f"{len(missing_critical)} manquants critiques",
                impact_percent=-12.0,
                fix_effort="medium",
                fix_cost="medium"
            ))
        elif len(missing_critical) > 0:
            amenities_list = ", ".join([a[0] for a in missing_critical])
            result.important_gaps.append(Gap(
                category="amenities",
                severity="important",
                title="Équipements courants manquants",
                description=f"Considère ajouter: {amenities_list}",
                your_value=f"{len(target.amenities)} équipements",
                market_value=f"{len(missing_critical)} manquants",
                impact_percent=-6.0,
                fix_effort="medium",
                fix_cost="low"
            ))
    
    def _analyze_superhost(self, target: ListingData, market: Dict, result: GapAnalysis):
        """Analyze Superhost status gap"""
        superhost_pct = market.get("superhost_pct", 0)
        
        if target.is_superhost:
            result.advantages.append(Gap(
                category="badges",
                severity="advantage",
                title="Statut Superhost",
                description="Le badge Superhost booste ta visibilité et la confiance des voyageurs.",
                your_value="Superhost ✓",
                market_value=f"{superhost_pct:.0f}% des concurrents",
                impact_percent=8.0,
                fix_effort="none",
                fix_cost="free"
            ))
        elif superhost_pct >= 50:
            result.important_gaps.append(Gap(
                category="badges",
                severity="important",
                title="Pas de statut Superhost",
                description=f"{superhost_pct:.0f}% des concurrents sont Superhosts. Ce badge améliore significativement le ranking.",
                your_value="Non Superhost",
                market_value=f"{superhost_pct:.0f}% des concurrents",
                impact_percent=-8.0,
                fix_effort="hard",
                fix_cost="free"
            ))
    
    def _analyze_guest_favorite(self, target: ListingData, market: Dict, result: GapAnalysis):
        """Analyze Guest Favorite status gap"""
        gf_pct = market.get("guest_favorite_pct", 0)
        
        if target.is_guest_favorite:
            result.advantages.append(Gap(
                category="badges",
                severity="advantage",
                title="Badge Guest Favorite",
                description="Tu fais partie des annonces les mieux notées! C'est un boost majeur de visibilité.",
                your_value="Guest Favorite ✓",
                market_value=f"{gf_pct:.0f}% des concurrents",
                impact_percent=12.0,
                fix_effort="none",
                fix_cost="free"
            ))
        elif gf_pct >= 20 and target.rating >= 4.8:
            result.minor_gaps.append(Gap(
                category="badges",
                severity="minor",
                title="Guest Favorite atteignable",
                description="Avec ton rating de 4.8+, tu es proche du badge Guest Favorite. Continue tes efforts!",
                your_value=f"{target.rating:.2f}★",
                market_value="4.9★ + 5 avis + <1% annulations",
                impact_percent=-5.0,
                fix_effort="medium",
                fix_cost="free"
            ))
    
    def _analyze_reviews_count(self, target: ListingData, market: Dict, result: GapAnalysis):
        """Analyze reviews count gap"""
        avg_reviews = market.get("avg_reviews", 20)
        max_reviews = market.get("max_reviews", 100)
        
        if target.reviews_count < 5:
            result.critical_gaps.append(Gap(
                category="reviews",
                severity="critical",
                title="Trop peu d'avis",
                description="Moins de 5 avis = pas éligible Guest Favorites et faible confiance des voyageurs.",
                your_value=f"{target.reviews_count} avis",
                market_value=f"{avg_reviews:.0f} (moy), {max_reviews} (max)",
                impact_percent=-20.0,
                fix_effort="hard",
                fix_cost="free"
            ))
        elif target.reviews_count < avg_reviews * 0.5:
            result.important_gaps.append(Gap(
                category="reviews",
                severity="important",
                title="Nombre d'avis en dessous du marché",
                description="Plus d'avis = plus de confiance = meilleur ranking.",
                your_value=f"{target.reviews_count} avis",
                market_value=f"{avg_reviews:.0f} en moyenne",
                impact_percent=-10.0,
                fix_effort="hard",
                fix_cost="free"
            ))
        elif target.reviews_count > avg_reviews * 1.5:
            result.advantages.append(Gap(
                category="reviews",
                severity="advantage",
                title="Excellent nombre d'avis",
                description="Ton nombre d'avis inspire confiance aux voyageurs.",
                your_value=f"{target.reviews_count} avis",
                market_value=f"{avg_reviews:.0f} en moyenne",
                impact_percent=5.0,
                fix_effort="none",
                fix_cost="free"
            ))
