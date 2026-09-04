from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class RecoveryAction(str, Enum):
    RETRY = "RETRY"
    PAYMENT_LINK = "PAYMENT_LINK"
    WAIT = "WAIT"
    STOP = "STOP"
    HUMAN_REVIEW = "HUMAN_REVIEW"

class RecoveryDecision(BaseModel):
    """
    Structured Output schema produced by the AI Decision Agent.
    CRITICAL: Agent recommends actions only; execution is handled by later components.
    """
    payment_id: str
    action: RecoveryAction
    confidence: float = Field(ge=0.0, le=1.0, description="Model decision confidence score between 0.0 and 1.0")
    rationale: str = Field(description="Concise merchant-facing explanation based on pre-decision features")
    expected_recovery_value: float = Field(ge=0.0, description="Payment amount * Recovery probability")
    priority: str = Field(description="HIGH, MEDIUM, or LOW priority tier")
    recommended_delay_minutes: int = Field(ge=0, default=0, description="Recommended delay before executing action")
    risk_level: str = Field(default="LOW", description="LOW, MEDIUM, or HIGH risk level")
    guardrail_notes: str = Field(default="Proposed recommendation pending Guardrail Engine check.", description="Notes for Phase 6 Guardrail Engine")
    
    model_config = ConfigDict(from_attributes=True)

class DecisionPreviewRequest(BaseModel):
    payment_id: Optional[str] = None
    # Optional raw feature overrides if predicting uncommitted payments
    amount: Optional[float] = None
    payment_method: Optional[str] = None
    failure_reason: Optional[str] = None

class BatchDecisionPreviewRequest(BaseModel):
    payment_ids: List[str]
