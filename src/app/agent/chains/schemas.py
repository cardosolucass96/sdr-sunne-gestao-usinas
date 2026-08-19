from __future__ import annotations

from pydantic import BaseModel, Field

from app.agent.state import IntentType, JourneyState, LeadProfile, LeadScore


class IntentClassification(BaseModel):
    intent: IntentType
    reason: str = Field(min_length=1)
    requires_specialist: bool = False
    specialist_name: str | None = None
    specialist_reason: str | None = None
    profile: LeadProfile | None = Field(
        default=None,
        description=(
            "investidor if evaluating buying/building a plant; proprietario if they already "
            "own a plant; fora_de_escopo for bill discount or rooftop install. Hybrid "
            "(land/capital to build for Sunne to manage) is investidor. Leave null if unclear."
        ),
    )
    journey_state: JourneyState | None = None
    score: LeadScore | None = Field(
        default=None,
        description=(
            "Investor score only when profile is investidor. A: clear motivation + capital "
            "compatible with a plant + horizon up to 90 days. B: fit but missing value or "
            "timing. C: just researching. D: capital clearly incompatible. Leave null otherwise."
        ),
    )
    disposition: str | None = None
    out_of_scope_reason: str | None = Field(
        default=None,
        description=(
            "Set only for product mismatch: wants to lower the electricity bill or install "
            "solar on a roof. Not for selling a plant or already being a client."
        ),
    )
    handoff_reason: str | None = None
    compliance_violation: str | None = Field(
        default=None,
        description=(
            "Set only when the lead asks for return, payback, price, how much Sunne pays, "
            "legal/ANEEL interpretation, or compares with CDB/Tesouro. Wanting to lease a "
            "plant is not a compliance violation."
        ),
    )
    lead_contact_gap: int = 0
    lead_name: str | None = None
    lead_origin: str | None = None
    journey_status: str | None = None
    requests_consultant: bool = Field(
        default=False,
        description=(
            "True only if the lead explicitly asks for a person, consultant, or to schedule. "
            "Also true if they already are a client or want to sell the plant."
        ),
    )
    requests_exit: bool = Field(
        default=False,
        description="True only if the lead asks to stop, pause, or says they are not interested.",
    )
    anti_icp_reason: str | None = Field(
        default=None,
        description=(
            "Owner gate failure stated this turn: plant not homologated, exclusive contract "
            "with another manager, outside coverage, or wants to manage their own customers."
        ),
    )
    motivacao: str | None = Field(
        default=None,
        description=(
            "Investor motivation if stated: renda_mensal, diversificar, "
            "proteger_patrimonio, or a short literal."
        ),
    )
    estagio_decisao: str | None = None
    capital_faixa: str | None = Field(
        default=None,
        description="Capital range as the lead said it, including mil/k. Do not invent a number.",
    )
    origem_recurso: str | None = None
    horizonte: str | None = None
    horizonte_decisao: str | None = None
    pf_pj: str | None = None
    homologada: bool | None = Field(
        default=None,
        description=(
            "True/False only when the lead clearly answers whether the plant is homologated "
            "and generating. Never infer from a generic sim/não or from 'já tenho usina'."
        ),
    )
    exclusividade: bool | None = Field(
        default=None,
        description=(
            "True only when the lead says there is an exclusive contract with another manager. "
            "False only when they clearly say there is none. Never infer from sim/tenho."
        ),
    )
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
