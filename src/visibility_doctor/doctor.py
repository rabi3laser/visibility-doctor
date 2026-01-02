"""
Visibility Doctor - Main Orchestrator

Combines:
- airbnb_scraper: For fetching listing and competitor data
- listing_grader: For algorithm-aligned scoring
- GapAnalyzer: For identifying visibility gaps
- ActionPlanGenerator: For creating prioritized action plans
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Import from YOUR existing packages
from airbnb_scraper import AirbnbScraper, ListingDetails, ListingBasic
from listing_grader import ListingGraderV2, GradeResultV2, ListingData

# Import from this package
from .analyzer import GapAnalyzer, GapAnalysis
from .actions import ActionPlanGenerator, ActionPlan

logger = logging.getLogger(__name__)


@dataclass
class VisibilityDoctorResult:
    """Complete analysis result"""
    listing_id: str
    listing_name: str
    listing_url: str
    analyzed_at: str
    
    # Scores
    overall_score: int
    grade: str
    
    # From ListingGraderV2
    grade_result: Dict
    
    # Gap analysis
    gap_analysis: Dict
    
    # Action plan
    action_plan: Dict
    
    # Summary metrics
    visibility_loss_percent: float = 0.0
    potential_gain_percent: float = 0.0
    total_time_hours: float = 0.0
    total_cost_eur: float = 0.0
    competitors_count: int = 0
    critical_gaps_count: int = 0
    quick_wins_count: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "listing_id": self.listing_id,
            "listing_name": self.listing_name,
            "listing_url": self.listing_url,
            "analyzed_at": self.analyzed_at,
            "overall_score": self.overall_score,
            "grade": self.grade,
            "summary": {
                "visibility_loss_percent": round(self.visibility_loss_percent, 1),
                "potential_gain_percent": round(self.potential_gain_percent, 1),
                "total_time_hours": round(self.total_time_hours, 1),
                "total_cost_eur": round(self.total_cost_eur, 0),
                "competitors_count": self.competitors_count,
                "critical_gaps_count": self.critical_gaps_count,
                "quick_wins_count": self.quick_wins_count,
            },
            "grade_result": self.grade_result,
            "gap_analysis": self.gap_analysis,
            "action_plan": self.action_plan,
        }
    
    def print_summary(self):
        """Print a human-readable summary"""
        print(f"""
{'=' * 60}
🏥 VISIBILITY DOCTOR - DIAGNOSTIC
{'=' * 60}

📊 ANNONCE ANALYSÉE
{'─' * 40}
  ID:       {self.listing_id}
  Nom:      {self.listing_name}
  Score:    {self.overall_score}/100 (Grade: {self.grade})

🔍 ANALYSE CONCURRENTIELLE
{'─' * 40}
  Concurrents analysés:    {self.competitors_count}
  Perte de visibilité:     -{self.visibility_loss_percent:.0f}%
  Gaps critiques:          {self.critical_gaps_count}

✅ PLAN D'ACTION
{'─' * 40}
  Quick wins:              {self.quick_wins_count}
  Temps total:             {self.total_time_hours:.1f}h
  Coût total:              €{self.total_cost_eur:.0f}
  Gain potentiel:          +{self.potential_gain_percent:.0f}%
""")


class VisibilityDoctor:
    """
    Main orchestrator for visibility analysis.
    
    Uses YOUR existing packages:
    - airbnb_scraper (github.com/rabi3laser/airbnb-scraper)
    - listing_grader (github.com/rabi3laser/hosttools)
    
    Example:
        async with VisibilityDoctor() as doctor:
            result = await doctor.analyze("https://airbnb.com/rooms/12345")
            result.print_summary()
            
            # Access detailed data
            for gap in result.gap_analysis["critical_gaps"]:
                print(f"🔴 {gap['title']}")
            
            for action in result.action_plan["quick_wins"]:
                print(f"⚡ {action['title']}")
    """
    
    def __init__(
        self,
        currency: str = "EUR",
        locale: str = "en",
        market_radius_km: float = 5.0,
        max_competitors: int = 20,
    ):
        """
        Initialize Visibility Doctor.
        
        Args:
            currency: Currency for prices (EUR, USD, etc.)
            locale: Language for content (en, fr, etc.)
            market_radius_km: Radius for competitor search
            max_competitors: Maximum number of competitors to analyze
        """
        self.currency = currency
        self.locale = locale
        self.market_radius_km = market_radius_km
        self.max_competitors = max_competitors
        
        self._scraper: Optional[AirbnbScraper] = None
        self._grader: Optional[ListingGraderV2] = None
        self._gap_analyzer = GapAnalyzer()
        self._action_generator = ActionPlanGenerator()
    
    async def __aenter__(self):
        """Async context manager entry"""
        self._scraper = AirbnbScraper(currency=self.currency, locale=self.locale)
        self._grader = ListingGraderV2(currency=self.currency, locale=self.locale)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._scraper:
            await self._scraper.close()
        if self._grader:
            await self._grader.close()
    
    def _extract_listing_id(self, url_or_id: str) -> str:
        """Extract listing ID from URL or return as-is if already an ID"""
        if url_or_id.isdigit():
            return url_or_id
        
        patterns = [
            r'/rooms/(\d+)',
            r'airbnb\.[^/]+/rooms/(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)
        
        raise ValueError(f"Invalid Airbnb URL or ID: {url_or_id}")
    
    async def analyze(
        self,
        url_or_id: str,
        compare_market: bool = True,
        verbose: bool = True,
    ) -> VisibilityDoctorResult:
        """
        Analyze a listing's visibility.
        
        Args:
            url_or_id: Airbnb listing URL or ID
            compare_market: Whether to analyze competitors
            verbose: Whether to print progress
            
        Returns:
            VisibilityDoctorResult with complete analysis
        """
        listing_id = self._extract_listing_id(url_or_id)
        
        if verbose:
            print(f"\n{'=' * 60}")
            print("🏥 VISIBILITY DOCTOR - Analysis in progress...")
            print(f"{'=' * 60}")
        
        # Step 1: Grade the listing using ListingGraderV2
        if verbose:
            print("\n📊 Step 1: Grading listing...")
        
        grade_result = await self._grader.grade(
            listing_id,
            compare_market=compare_market,
            market_radius_km=self.market_radius_km,
        )
        
        if verbose:
            print(f"   ✅ Score: {grade_result.overall_score}/100 (Grade: {grade_result.grade})")
        
        # Step 2: Get listing details
        if verbose:
            print("\n🔍 Step 2: Fetching listing details...")
        
        details = await self._scraper.get_listing_details(listing_id)
        if not details:
            raise ValueError(f"Could not fetch listing: {listing_id}")
        
        if verbose:
            print(f"   ✅ Listing: {details.name}")
        
        # Step 3: Find competitors
        competitors = []
        if compare_market and details.latitude and details.longitude:
            if verbose:
                print("\n🏆 Step 3: Finding competitors...")
            
            delta = self.market_radius_km / 111  # km to degrees
            competitors = await self._scraper.search_by_bounds(
                ne_lat=details.latitude + delta,
                ne_lng=details.longitude + delta,
                sw_lat=details.latitude - delta,
                sw_lng=details.longitude - delta,
                max_listings=self.max_competitors,
            )
            
            # Filter out the target listing
            competitors = [c for c in competitors if c.airbnb_id != listing_id]
            
            if verbose:
                print(f"   ✅ Found {len(competitors)} competitors")
        
        # Step 4: Gap analysis
        if verbose:
            print("\n🎯 Step 4: Analyzing gaps...")
        
        listing_data = self._convert_to_listing_data(details, grade_result)
        gap_analysis = self._gap_analyzer.analyze(listing_data, competitors, grade_result)
        
        if verbose:
            print(f"   ✅ {len(gap_analysis.critical_gaps)} critical gaps")
            print(f"   ✅ {len(gap_analysis.important_gaps)} important gaps")
            print(f"   ✅ {len(gap_analysis.advantages)} advantages")
        
        # Step 5: Generate action plan
        if verbose:
            print("\n📋 Step 5: Generating action plan...")
        
        action_plan = self._action_generator.generate(gap_analysis)
        
        if verbose:
            print(f"   ✅ {len(action_plan.actions)} actions total")
            print(f"   ✅ {len(action_plan.quick_wins)} quick wins")
        
        # Build result
        result = VisibilityDoctorResult(
            listing_id=listing_id,
            listing_name=details.name,
            listing_url=f"https://www.airbnb.com/rooms/{listing_id}",
            analyzed_at=datetime.now(timezone.utc).isoformat(),
            
            overall_score=grade_result.overall_score,
            grade=grade_result.grade,
            
            grade_result=grade_result.to_dict(),
            gap_analysis=gap_analysis.to_dict(),
            action_plan=action_plan.to_dict(),
            
            visibility_loss_percent=gap_analysis.estimated_visibility_loss,
            potential_gain_percent=action_plan.potential_gain_percent,
            total_time_hours=action_plan.total_time_hours,
            total_cost_eur=action_plan.total_cost_eur,
            competitors_count=len(competitors),
            critical_gaps_count=len(gap_analysis.critical_gaps),
            quick_wins_count=len(action_plan.quick_wins),
        )
        
        if verbose:
            result.print_summary()
        
        return result
    
    def _convert_to_listing_data(
        self,
        details: ListingDetails,
        grade: GradeResultV2
    ) -> ListingData:
        """Convert ListingDetails to ListingData for gap analysis"""
        return ListingData(
            listing_id=details.airbnb_id,
            name=details.name,
            description=details.description,
            url=details.url,
            
            price_per_night=details.price_per_night,
            cleaning_fee=details.cleaning_fee,
            currency=details.currency,
            
            bedrooms=details.bedrooms,
            beds=details.beds,
            bathrooms=details.bathrooms,
            max_guests=details.max_guests,
            
            city=details.city,
            latitude=details.latitude,
            longitude=details.longitude,
            
            rating=details.rating,
            reviews_count=details.reviews_count,
            
            rating_cleanliness=details.rating_cleanliness,
            rating_accuracy=details.rating_accuracy,
            rating_checkin=details.rating_checkin,
            rating_communication=details.rating_communication,
            rating_location=details.rating_location,
            rating_value=details.rating_value,
            
            host_id=details.host_id,
            host_name=details.host_name,
            is_superhost=details.host_is_superhost,
            is_guest_favorite=details.is_guest_favorite,
            
            response_rate=grade.response_rate,
            response_time_hours=grade.response_time_hours,
            
            instant_bookable=details.instant_bookable,
            cancellation_rate=grade.cancellation_rate,
            
            min_nights=details.min_nights,
            max_nights=details.max_nights,
            
            images=details.images,
            amenities=details.amenities,
            
            scraped_at=details.scraped_at,
        )
    
    def analyze_sync(
        self,
        url_or_id: str,
        compare_market: bool = True,
        verbose: bool = True,
    ) -> VisibilityDoctorResult:
        """
        Synchronous wrapper for analyze().
        
        Use this if you're not in an async context.
        """
        async def _run():
            async with VisibilityDoctor(
                currency=self.currency,
                locale=self.locale,
                market_radius_km=self.market_radius_km,
                max_competitors=self.max_competitors,
            ) as doctor:
                return await doctor.analyze(url_or_id, compare_market, verbose)
        
        return asyncio.run(_run())


# Convenience function for quick analysis
async def analyze_listing(
    url_or_id: str,
    currency: str = "EUR",
    compare_market: bool = True,
) -> VisibilityDoctorResult:
    """
    Quick function to analyze a listing.
    
    Example:
        from visibility_doctor import analyze_listing
        
        result = await analyze_listing("https://airbnb.com/rooms/12345")
        print(f"Score: {result.overall_score}")
    """
    async with VisibilityDoctor(currency=currency) as doctor:
        return await doctor.analyze(url_or_id, compare_market=compare_market)
