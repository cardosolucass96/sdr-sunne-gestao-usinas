from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agent.chains import build_classifier_chain, invoke_with_temperature_fallback
from app.agent.chains.schemas import IntentClassification
from app.agent.messages import latest_user_message
from app.agent.state import AgentState, JourneyState, LeadProfile, LeadScore

LOGGER = logging.getLogger(__name__)

_MAX_TRANSITION_LOGS = 30
_KNOWN_FIELD_KEYS = (
    "profile",
    "score",
    "motivacao",
    "estagio_decisao",
    "capital_faixa",
    "origem_recurso",
    "horizonte",
    "horizonte_decisao",
    "pf_pj",
    "homologada",
    "exclusividade",
    "concessionaria",
    "cidade_uf",
    "potencia_kwp",
    "data_operacao",
    "capacidade_ociosa_pct",
    "lead_name",
    "lead_origin",
)


def _invoke_with_temperature_fallback(
    chain_factory,
    payload: dict[str, Any],
    *,
    config: RunnableConfig = None,
) -> Any:
    return invoke_with_temperature_fallback(chain_factory, payload, config=config)


def _latest_user_message(state: AgentState) -> str:
    return latest_user_message(state)


def _build_classifier_chain(*, use_custom_temperature: bool = True):
    return build_classifier_chain(use_custom_temperature=use_custom_temperature)


def _message_excerpt(value: str, max_words: int = 16) -> str:
    words = [word for word in value.strip().split() if word]
    return " ".join(words[:max_words])


def _known_fields_snapshot(state: AgentState) -> str:
    parts: list[str] = []
    for key in _KNOWN_FIELD_KEYS:
        value = state.get(key)
        if value is not None and value != "":
            parts.append(f"{key}={value}")
    return "\n".join(parts) if parts else "none"


def _classifier_payload(state: AgentState, latest_message: str) -> dict[str, str]:
    return {
        "latest_user_message": latest_message,
        "current_profile": str(state.get("profile") or "unknown"),
        "current_journey_state": str(state.get("journey_state") or "E0"),
        "resume_context": str(state.get("resume_context") or "none"),
        "known_fields": _known_fields_snapshot(state),
    }


def _investor_fields_from_state(state: AgentState) -> dict[str, str | None]:
    return {
        "motivation": state.get("motivacao"),
        "decision_stage": state.get("estagio_decisao"),
        "capital_band": state.get("capital_faixa"),
        "funding_source": state.get("origem_recurso"),
        "horizon": state.get("horizonte_decisao") or state.get("horizonte"),
        "pf_pj": state.get("pf_pj"),
    }


def _owner_fields_from_state(state: AgentState) -> dict[str, str | bool | int | float | None]:
    return {
        "homologada": state.get("homologada"),
        "exclusividade": state.get("exclusividade"),
        "concessionaria": state.get("concessionaria"),
        "cidade_uf": state.get("cidade_uf"),
        "potencia_kwp": state.get("potencia_kwp"),
        "data_operacao": state.get("data_operacao"),
        "capacidade_ociosa_pct": state.get("capacidade_ociosa_pct"),
    }


def _investor_fields_from_classification(
    classification: IntentClassification,
) -> dict[str, str | None]:
    return {
        "motivation": classification.motivacao,
        "decision_stage": classification.estagio_decisao,
        "capital_band": classification.capital_faixa,
        "funding_source": classification.origem_recurso,
        "horizon": classification.horizonte_decisao or classification.horizonte,
        "pf_pj": classification.pf_pj,
    }


def _owner_fields_from_classification(
    classification: IntentClassification,
) -> dict[str, str | bool | int | float | None]:
    return {
        "homologada": classification.homologada,
        "exclusividade": classification.exclusividade,
        "concessionaria": classification.concessionaria,
        "cidade_uf": classification.cidade_uf,
        "potencia_kwp": classification.potencia_kwp,
        "data_operacao": classification.data_operacao,
        "capacidade_ociosa_pct": classification.capacidade_ociosa_pct,
    }


def _merge_latest_fields(
    latest_fields: dict[str, Any],
    previous_fields: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(previous_fields)
    merged.update({key: value for key, value in latest_fields.items() if value is not None})
    return merged


def _resolve_profile(
    classification: IntentClassification,
    current_profile: LeadProfile,
) -> LeadProfile:
    if classification.profile in {"investidor", "proprietario", "fora_de_escopo"}:
        return classification.profile
    if current_profile in {"investidor", "proprietario", "fora_de_escopo", "unknown"}:
        return current_profile
    return "unknown"


def _owner_gate_reason(
    owner_fields: dict[str, Any],
    anti_icp_reason: str | None,
) -> str | None:
    if anti_icp_reason:
        return anti_icp_reason
    if owner_fields.get("homologada") is False:
        return "Usina sem homologacao ativa."
    if owner_fields.get("exclusividade") is True:
        return "Usina com exclusividade ativa com outra gestora."
    return None


def _can_progress_investor_to_e3(investor_fields: dict[str, str | None]) -> bool:
    return bool(investor_fields.get("motivation"))


def _has_minimum_investor_data(investor_fields: dict[str, str | None]) -> bool:
    return bool(
        investor_fields.get("motivation")
        and (investor_fields.get("capital_band") or investor_fields.get("horizon"))
    )


def _has_minimum_owner_data(owner_fields: dict[str, Any]) -> bool:
    if owner_fields.get("homologada") is not True:
        return False
    if owner_fields.get("exclusividade") is True:
        return False
    if owner_fields.get("potencia_kwp") is None:
        return False
    if not owner_fields.get("data_operacao"):
        return False
    if owner_fields.get("capacidade_ociosa_pct") is None:
        return False
    return bool(owner_fields.get("cidade_uf") or owner_fields.get("concessionaria"))


def _can_progress_owner_to_e3(owner_fields: dict[str, Any]) -> bool:
    if owner_fields.get("homologada") is False:
        return False
    if owner_fields.get("exclusividade") is True:
        return False
    return bool(owner_fields.get("cidade_uf") or owner_fields.get("concessionaria"))


def _next_journey_state(
    state: AgentState,
    *,
    profile: LeadProfile,
    score: LeadScore | None,
    investor_fields: dict[str, str | None],
    owner_fields: dict[str, Any],
    compliance_violation: str | None,
    out_of_scope_reason: str | None,
    owner_gate_reason: str | None,
    requests_consultant: bool,
    requests_exit: bool,
) -> tuple[JourneyState, int, str]:
    current_state = state.get("journey_state") or "E0"
    lead_gap = int(state.get("lead_contact_gap") or 0)

    if current_state in {"E5", "E6"}:
        return current_state, 0, "Estado terminal mantido."

    if current_state in {"E0", "E1"} and compliance_violation is not None:
        if current_state == "E0":
            return "E1", 1, "Triagem obrigatoria antes de escalonamento."
        return "E1", lead_gap, "Triagem ainda não confirmada; segue E1 antes de escalar."

    if current_state in {"E2a", "E2b", "E3", "E4"} and compliance_violation is not None:
        return "E5", 0, "Pergunta de compliance -> escalonamento."

    if current_state == "E0":
        next_gap = 0 if profile != "unknown" else 1
        return "E1", next_gap, "Primeiro contato recebido, iniciando triagem."

    if current_state == "E1":
        if profile == "fora_de_escopo":
            return "E6", 0, "Triagem identificou fora de escopo."
        if profile == "investidor":
            return "E2a", 0, "Perfil investidor identificado."
        if profile == "proprietario":
            return "E2b", 0, "Perfil proprietario identificado."

        lead_gap += 1
        if lead_gap >= 2:
            return (
                "E2a",
                0,
                "Sem resposta de triagem em dois toques; perfil assumido pelo contexto.",
            )
        return "E1", lead_gap, "Triagem sem resposta objetiva ainda."

    if current_state == "E2a":
        if profile == "proprietario":
            return "E2b", 0, "Reclassificacao para perfil proprietario sem reiniciar."
        if out_of_scope_reason or profile == "fora_de_escopo":
            return "E6", 0, "Lead fora de escopo."
        if score == "D":
            return "E6", 0, "Score D: capital ou fit incompatível."
        if profile == "investidor" and _can_progress_investor_to_e3(investor_fields):
            return "E3", 0, "Qualificacao inicial coletada e validada."
        if requests_consultant:
            return "E3", 0, "Lead demonstrou interesse e segue para explicacao do modelo."
        return "E2a", 0, "Coletando dados de investidor."

    if current_state == "E2b":
        if profile == "investidor":
            return "E2a", 0, "Reclassificacao para perfil investidor sem reiniciar."
        if out_of_scope_reason or profile == "fora_de_escopo":
            return "E6", 0, "Lead fora de escopo na qualificacao proprietario."
        if owner_gate_reason:
            return "E6", 0, "Trava de proprietario ativa."
        if _can_progress_owner_to_e3(owner_fields):
            return "E3", 0, "Travas verificadas para proprietario."
        return "E2b", 0, "Coletando dados de proprietario."

    if current_state == "E3":
        if out_of_scope_reason:
            return "E6", 0, "Lead saiu do escopo na fase de explicacao."
        if requests_exit:
            return "E6", 0, "Lead pediu pausa/encerramento."
        if requests_consultant:
            if not (
                profile == "fora_de_escopo"
                or _has_minimum_investor_data(investor_fields)
                or _has_minimum_owner_data(owner_fields)
            ):
                return (
                    current_state,
                    lead_gap,
                    "Dados mínimos ainda incompletos para encerrar com consultor.",
                )
            return "E5", 0, "Lead sinaliza desejo de proximo passo."
        return "E4", 0, "Passando para coleta complementar."

    if current_state == "E4":
        if out_of_scope_reason:
            return "E6", 0, "Lead saiu do escopo durante coleta complementar."
        if requests_exit:
            return "E6", 0, "Lead pediu pausa/encerramento na coleta."
        if requests_consultant:
            if not (
                profile == "fora_de_escopo"
                or _has_minimum_investor_data(investor_fields)
                or _has_minimum_owner_data(owner_fields)
            ):
                return (
                    current_state,
                    lead_gap,
                    "Dados mínimos ainda incompletos para encerrar com consultor.",
                )
            return "E5", 0, "Lead solicita seguimento com consultor."
        return "E4", 0, "Coleta complementar mantida."

    return "E4", 0, "Estado de transicao default para coleta."


def _handoff_reason(
    profile: LeadProfile,
    out_of_scope_reason: str | None,
    compliance_violation: str | None,
    owner_gate_reason: str | None,
) -> str | None:
    if out_of_scope_reason:
        return out_of_scope_reason
    if owner_gate_reason:
        return owner_gate_reason
    if compliance_violation:
        return compliance_violation
    if profile == "fora_de_escopo":
        return "Perfil fora de escopo identificado."
    return None


def _clear_previous_profile_fields(
    updates: dict[str, Any],
    previous_profile: LeadProfile,
    next_profile: LeadProfile,
) -> None:
    if previous_profile == next_profile:
        return

    if previous_profile == "investidor":
        updates["motivacao"] = None
        updates["estagio_decisao"] = None
        updates["capital_faixa"] = None
        updates["origem_recurso"] = None
        updates["horizonte"] = None
        updates["horizonte_decisao"] = None
        updates["pf_pj"] = None
    if previous_profile == "proprietario":
        updates["homologada"] = None
        updates["exclusividade"] = None
        updates["concessionaria"] = None
        updates["cidade_uf"] = None
        updates["potencia_kwp"] = None
        updates["data_operacao"] = None
        updates["capacidade_ociosa_pct"] = None

    updates["score"] = None


def _transition_log_entry(
    *,
    prev_state: str,
    next_state: str,
    profile: LeadProfile,
    score: LeadScore | None,
    message: str,
    reason: str,
) -> dict[str, str]:
    return {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "prev_state": prev_state,
        "next_state": next_state,
        "profile": profile,
        "score": score or "",
        "message_excerpt": message,
        "transition_reason": reason,
    }


def _merge_transition_log(
    state: AgentState,
    entry: dict[str, str],
) -> list[dict[str, str]]:
    logs = list(state.get("journey_transitions") or [])
    logs.append(entry)
    return logs[-_MAX_TRANSITION_LOGS:]


def _handoff_package_text(
    *,
    profile: LeadProfile,
    score: LeadScore | None,
    state: AgentState,
    investor_fields: dict[str, str | None],
    owner_fields: dict[str, Any],
    disposition: str | None,
) -> str:
    lead_name = state.get("lead_name") or "-"
    lead_origin = state.get("lead_origin") or "-"
    homologada = owner_fields["homologada"]
    if homologada is None:
        homologada = state.get("homologada")
    exclusividade = owner_fields["exclusividade"]
    if exclusividade is None:
        exclusividade = state.get("exclusividade")
    next_step = (
        "encerrado com registro" if (profile == "fora_de_escopo") else "agendar com consultor"
    )
    objection = disposition or "-"
    return " | ".join(
        [
            f"Nome: {lead_name}",
            f"Origem: {lead_origin}",
            f"Perfil: {profile}",
            f"Score: {score or 'N/A'}",
            f"Motivacao: {investor_fields['motivation'] or state.get('motivacao') or '-'}",
            f"Capital: {investor_fields['capital_band'] or state.get('capital_faixa') or '-'}",
            (
                f"Origem recurso: "
                f"{investor_fields['funding_source'] or state.get('origem_recurso') or '-'}"
            ),
            f"Horizonte: {investor_fields['horizon'] or state.get('horizonte_decisao') or '-'}",
            f"Cidade/UF: {owner_fields['cidade_uf'] or state.get('cidade_uf') or '-'}",
            f"Homologada: {homologada}",
            f"Exclusividade: {exclusividade}",
            f"Proxima acao: {next_step}",
            f"Objecao pendente: {objection}",
        ]
    )


def _determine_status(
    next_state: JourneyState,
    score: LeadScore | None,
    profile: LeadProfile,
    out_of_scope_reason: str | None,
    compliance_violation: str | None,
) -> str:
    if next_state == "E6":
        return "qualified_out_of_scope"
    if compliance_violation:
        return "handoff_required"
    if profile in {"investidor", "proprietario"}:
        if score is not None:
            return "classified"
        return "qualified"
    if out_of_scope_reason:
        return "qualified_out_of_scope"
    return "triaged"


def _update_flow(
    state: AgentState,
    latest_message: str,
    classification: IntentClassification,
) -> dict[str, Any]:
    current_profile = state.get("profile") or "unknown"
    current_state = state.get("journey_state") or "E0"

    investor_fields = _merge_latest_fields(
        _investor_fields_from_classification(classification),
        previous_fields=_investor_fields_from_state(state),
    )
    owner_fields = _merge_latest_fields(
        _owner_fields_from_classification(classification),
        previous_fields=_owner_fields_from_state(state),
    )

    profile = _resolve_profile(classification, current_profile)
    if profile in {"investidor", "proprietario", "fora_de_escopo"} and profile != current_profile:
        LOGGER.info(
            "agent.journey.reclassified",
            extra={"previous_profile": current_profile, "new_profile": profile},
        )

    out_of_scope_reason = classification.out_of_scope_reason
    if profile == "fora_de_escopo" and not out_of_scope_reason:
        out_of_scope_reason = "Lead fora de escopo (conta de luz/telhado)."

    compliance_violation = classification.compliance_violation
    owner_gate = _owner_gate_reason(owner_fields, classification.anti_icp_reason)
    if owner_gate and profile == "unknown":
        profile = "proprietario"

    score: LeadScore | None = None
    if profile == "investidor":
        score = classification.score or (
            state.get("score") if current_profile == "investidor" else None
        )

    next_state, lead_gap, transition_reason = _next_journey_state(
        state,
        profile=profile,
        score=score,
        investor_fields=investor_fields,
        owner_fields=owner_fields,
        compliance_violation=compliance_violation,
        out_of_scope_reason=out_of_scope_reason,
        owner_gate_reason=owner_gate,
        requests_consultant=classification.requests_consultant,
        requests_exit=classification.requests_exit,
    )

    assumed_uncertain = "perfil assumido pelo contexto" in transition_reason
    if assumed_uncertain and profile == "unknown":
        profile = "investidor"

    disposition = state.get("disposition")
    if out_of_scope_reason or owner_gate:
        disposition = "out_of_scope"
    if compliance_violation:
        disposition = "handoff_due_to_compliance"
    if assumed_uncertain:
        disposition = "triage_assumed_uncertain"
    if next_state in {"E5", "E6"} and disposition is None:
        disposition = "handoff_ready"

    handoff_reason = _handoff_reason(profile, out_of_scope_reason, compliance_violation, owner_gate)
    transition = _transition_log_entry(
        prev_state=current_state,
        next_state=next_state,
        profile=profile,
        score=score,
        message=_message_excerpt(latest_message),
        reason=transition_reason,
    )

    updates: dict[str, Any] = {
        "profile": profile,
        "journey_state": next_state,
        "lead_contact_gap": lead_gap,
        "transition_reason": transition_reason,
        "journey_transitions": _merge_transition_log(state, transition),
        "journey_status": _determine_status(
            next_state=next_state,
            score=score,
            profile=profile,
            out_of_scope_reason=out_of_scope_reason,
            compliance_violation=compliance_violation,
        ),
        "status": _determine_status(
            next_state=next_state,
            score=score,
            profile=profile,
            out_of_scope_reason=out_of_scope_reason,
            compliance_violation=compliance_violation,
        ),
        "out_of_scope_reason": out_of_scope_reason,
        "handoff_reason": handoff_reason,
        "compliance_violation": compliance_violation,
    }

    if score is not None:
        updates["score"] = score
    if disposition is not None:
        updates["disposition"] = disposition

    if investor_fields["motivation"]:
        updates["motivacao"] = investor_fields["motivation"]
    if investor_fields["decision_stage"]:
        updates["estagio_decisao"] = investor_fields["decision_stage"]
    if investor_fields["capital_band"]:
        updates["capital_faixa"] = investor_fields["capital_band"]
    if investor_fields["funding_source"]:
        updates["origem_recurso"] = investor_fields["funding_source"]
    if investor_fields["horizon"]:
        updates["horizonte_decisao"] = investor_fields["horizon"]
        updates["horizonte"] = investor_fields["horizon"]
    if investor_fields["pf_pj"]:
        updates["pf_pj"] = investor_fields["pf_pj"]

    if owner_fields["homologada"] is not None:
        updates["homologada"] = owner_fields["homologada"]
    if owner_fields["exclusividade"] is not None:
        updates["exclusividade"] = owner_fields["exclusividade"]
    if owner_fields["concessionaria"]:
        updates["concessionaria"] = owner_fields["concessionaria"]
    if owner_fields["cidade_uf"]:
        updates["cidade_uf"] = owner_fields["cidade_uf"]
    if owner_fields["potencia_kwp"] is not None:
        updates["potencia_kwp"] = owner_fields["potencia_kwp"]
    if owner_fields["data_operacao"]:
        updates["data_operacao"] = owner_fields["data_operacao"]
    if owner_fields["capacidade_ociosa_pct"] is not None:
        updates["capacidade_ociosa_pct"] = owner_fields["capacidade_ociosa_pct"]

    lead_name = classification.lead_name or state.get("lead_name")
    if lead_name:
        updates["lead_name"] = lead_name
    lead_origin = classification.lead_origin or state.get("lead_origin")
    if lead_origin:
        updates["lead_origin"] = lead_origin

    _clear_previous_profile_fields(updates, current_profile, profile)

    if next_state in {"E5", "E6"}:
        handoff_state = dict(state)
        handoff_state.update(updates)
        updates["handoff_package"] = _handoff_package_text(
            profile=profile,
            score=score,
            state=handoff_state,
            investor_fields=investor_fields,
            owner_fields=owner_fields,
            disposition=disposition,
        )

    LOGGER.info(
        "agent.journey.transition",
        extra={
            "journey_state_prev": current_state,
            "journey_state_next": next_state,
            "profile": profile,
            "score": score,
            "transition_reason": transition_reason,
            "compliance_violation": bool(compliance_violation),
        },
    )

    return updates


def classify_intent(
    state: AgentState,
    config: RunnableConfig = None,
) -> dict[str, Any]:
    latest_message = _latest_user_message(state)
    if not latest_message and state.get("resume_context"):
        latest_message = "Retome a conversa com o lead de forma natural."
    if not latest_message:
        return {
            "latest_user_message": "",
            "intent": "fallback",
            "intent_reason": "No user message was available for classification.",
            "profile": "unknown",
            "journey_state": "E0",
            "status": "classified",
        }

    result = _invoke_with_temperature_fallback(
        _build_classifier_chain,
        _classifier_payload(state, latest_message),
        config=config,
    )

    return {
        "latest_user_message": latest_message,
        "intent": result.intent,
        "intent_reason": result.reason,
        "requires_specialist": result.requires_specialist,
        "specialist_name": result.specialist_name,
        "specialist_reason": result.specialist_reason,
        **_update_flow(state, latest_message, result),
    }
