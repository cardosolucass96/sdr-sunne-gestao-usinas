from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent.state import IntentType, JourneyState, LeadProfile, LeadScore


class IntentClassification(BaseModel):
    intent: IntentType
    reason: str = Field(min_length=1)
    requires_specialist: bool = False
    specialist_name: str | None = None
    specialist_reason: str | None = None
    profile: LeadProfile | None = None
    journey_state: JourneyState | None = None
    score: LeadScore | None = None
    disposition: str | None = None
    out_of_scope_reason: str | None = None
    handoff_reason: str | None = None
    compliance_violation: str | None = None
    lead_contact_gap: int = 0
    lead_name: str | None = None
    lead_origin: str | None = None
    journey_status: str | None = None
    motivacao: str | None = None
    estagio_decisao: str | None = None
    capital_faixa: str | None = None
    origem_recurso: str | None = None
    horizonte: str | None = None
    horizonte_decisao: str | None = None
    pf_pj: str | None = None
    homologada: bool | None = None
    exclusividade: bool | None = None
    concessionaria: str | None = None
    cidade_uf: str | None = None
    potencia_kwp: float | int | None = None
    data_operacao: str | None = None
    capacidade_ociosa_pct: float | int | None = None


class OutboundMediaChoice(BaseModel):
    media_id: str = Field(min_length=1)
    caption: str | None = None
    reason: str = Field(min_length=1)


class GeneratedAudioChoice(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=1600,
        description=("Spoken explanation only. Exact or copyable facts belong in response_text."),
    )
    reason: str = Field(
        min_length=1,
        description="Why spoken audio is more useful than text for this part of the reply.",
    )


class AgentResponsePlan(BaseModel):
    response_text: str = Field(
        min_length=1,
        description=(
            "WhatsApp text reply, including all exact, scannable, or copyable information."
        ),
    )
    media_choices: list[OutboundMediaChoice] = Field(default_factory=list)
    generated_audio: GeneratedAudioChoice | None = Field(
        default=None,
        description=(
            "Optional spoken explanation. Leave empty for text-only replies; combine with "
            "response_text for hybrid replies."
        ),
    )
