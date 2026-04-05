"""
Pydantic schemas for all Business Co-Founder AI data models.
These define the structured output format for every component.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


# --- Enums -------------------------------------------------------------------

class EntrepreneurStage(str, Enum):
    IDEA = "idea"
    GROWTH = "growth"
    SCALE = "scale"

class BusinessIntent(str, Enum):
    EXPLORE_IDEA = "explore_idea"
    VALIDATE_MARKET = "validate_market"
    ANALYZE_COMPETITION = "analyze_competition"
    BUILD_PLAN = "build_plan"
    FIND_OPPORTUNITIES = "find_opportunities"
    SCALE_BUSINESS = "scale_business"
    GENERAL_ADVICE = "general_advice"

class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# --- Sub-Models --------------------------------------------------------------

class MarketSizeEstimate(BaseModel):
    tam: str = Field(description="Total Addressable Market")
    tam_value: Optional[float] = Field(default=None, description="TAM numeric value in USD")
    sam: str = Field(description="Serviceable Addressable Market")
    sam_value: Optional[float] = Field(default=None, description="SAM numeric value in USD")
    som: str = Field(description="Serviceable Obtainable Market")
    som_value: Optional[float] = Field(default=None, description="SOM numeric value in USD")
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    assumptions: list[str] = Field(default_factory=list)

class CompetitorEntry(BaseModel):
    name: str
    description: str = ""
    funding: str = ""
    strength: str = ""
    weakness: str = ""
    market_share: str = ""
    url: str = ""

class RiskCategory(BaseModel):
    category: str
    score: float = Field(ge=1, le=10, description="Risk score 1-10")
    description: str = ""
    mitigation: str = ""

class RiskAssessment(BaseModel):
    categories: list[RiskCategory] = Field(default_factory=list)
    aggregate_score: float = Field(ge=1, le=10, default=5.0)
    overall_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    key_risks: list[str] = Field(default_factory=list)

class IdeaScore(BaseModel):
    feasibility: float = Field(ge=1, le=10, default=5)
    market_size: float = Field(ge=1, le=10, default=5)
    competition_gap: float = Field(ge=1, le=10, default=5)
    time_to_revenue: float = Field(ge=1, le=10, default=5)
    scalability: float = Field(ge=1, le=10, default=5)
    founder_fit: float = Field(ge=1, le=10, default=5)
    composite: float = Field(ge=0, le=10, default=5)

class RevenueEstimate(BaseModel):
    model: str = ""
    monthly_potential: str = ""
    annual_potential: str = ""
    time_to_first_revenue: str = ""
    time_to_profitability: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.LOW

class CostStructure(BaseModel):
    initial_investment: str = ""
    monthly_operating: str = ""
    key_costs: list[str] = Field(default_factory=list)
    break_even_timeline: str = ""


# --- Primary Output Models --------------------------------------------------

class BusinessIdea(BaseModel):
    """Core structured output for a single business idea."""
    idea_title: str
    problem: str
    target_customer: str
    solution: str
    revenue_model: str
    key_risk: str
    first_action_this_week: str
    scores: IdeaScore = Field(default_factory=IdeaScore)

class QuantitativeAnalysis(BaseModel):
    market_size: MarketSizeEstimate = Field(default_factory=MarketSizeEstimate)
    revenue_estimate: RevenueEstimate = Field(default_factory=RevenueEstimate)
    cost_structure: CostStructure = Field(default_factory=CostStructure)
    growth_potential: str = ""
    demand_supply_gap: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    key_variables: list[str] = Field(default_factory=list)
    validation_steps: list[str] = Field(default_factory=list)


# --- API Request / Response Models ------------------------------------------

class BusinessAnalyzeRequest(BaseModel):
    query: str
    business_mode: bool = True
    stage: Optional[EntrepreneurStage] = None
    history: list[dict] = Field(default_factory=list)
    session_id: Optional[str] = None

class BusinessDetectRequest(BaseModel):
    query: str

class BusinessDetectResponse(BaseModel):
    is_business: bool
    confidence: float = Field(ge=0, le=1)
    detected_intent: Optional[BusinessIntent] = None
    suggestion: str = ""

class BusinessAnalyzeResponse(BaseModel):
    """Complete structured response from the business pipeline."""
    ideas: list[BusinessIdea] = Field(default_factory=list)
    market_analysis: Optional[QuantitativeAnalysis] = None
    competitors: list[CompetitorEntry] = Field(default_factory=list)
    risk_assessment: Optional[RiskAssessment] = None
    this_week_actions: list[str] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    stage: EntrepreneurStage = EntrepreneurStage.IDEA
    intent: BusinessIntent = BusinessIntent.EXPLORE_IDEA
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    summary: str = ""
    reasoning_steps: list[str] = Field(default_factory=list)

class ChatRequest(BaseModel):
    prompt: str
    history: list[dict] = Field(default_factory=list)
    use_rag: bool = True
    business_mode: bool = False

class SourceMetadata(BaseModel):
    number: int
    title: str
    domain: str
    image: str = ""
    snippet: str = ""
    source: str = ""
