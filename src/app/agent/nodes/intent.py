from __future__ import annotations

import logging
import re
import unicodedata
from datetime import UTC, datetime
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agent.chains import build_classifier_chain, invoke_with_temperature_fallback
from app.agent.messages import latest_user_message
from app.agent.state import AgentState, JourneyState, LeadProfile, LeadScore

LOGGER = logging.getLogger(__name__)

_MAX_TRANSITION_LOGS = 30
_MIN_INVESTOR_CAPITAL_BRL = 50_000

_INVESTMENT_OUT_OF_SCOPE = (
    "só baixar minha conta de luz",
    "quero baixar a conta",
    "quero reduzir a conta",
    "quero baixar conta",
    "quero economizar a luz",
    "quero economizar meu consumo",
    "instalar solar no meu telhado",
)

_OWNER_PROFILE_HINTS = (
    "tenho uma usina",
    "já tenho usina",
    "usina já instalada",
    "já tenho uma usina",
    "sou dono de usina",
    "sou proprietario de usina",
    "sou proprietário de usina",
    "tenho usina",
    "minha usina",
)

_INVESTOR_PROFILE_HINTS = (
    "avaliando investir",
    "quero investir",
    "quero comprar",
    "comprar energia",
    "montar uma usina",
    "montar usina",
    "tenho interesse em investir",
    "interesse em investir",
    "interessado em investir",
)

_OUT_OF_SCOPE_GAP_REASONS = (
    "só baixar minha conta de luz",
    "quero baixar minha conta",
    "quero reduzir a conta",
    "quero instalar solar no meu telhado",
    "instalar no telhado",
    "quero reduzir minha conta",
    "quero vender minha usina",
    "quero vender usina",
)

_COMPLIANCE_TRIGGER_WORDS = (
    "rentabilidade",
    "retorno",
    "payback",
    "renda fixa",
    "aplicação",
    "aplicacao",
    "investimento seguro",
    "sem risco",
    "risco zero",
)

_COMPLIANCE_QUESTIONS = (
    "quanto custa",
    "quanto vai custar",
    "quanto custa uma usina",
    "quanto vocês pagam",
    "quanto paga",
    "quanto rende",
    "quanto ganha",
    "em quanto tempo",
)
_COMPLIANCE_LEGAL = ("fio b", "marco legal", "anatel", "norma", "regulatorio", "regulatório")

_HOMOLOGATION_POSITIVE = ("sim", "já", "ja", "tem sim", "tem", "já tem")
_HOMOLOGATION_NEGATIVE = ("não", "nao", "pendente", "em andamento", "ainda não", "ainda nao")
_EXCLUSIVITY_NEGATIVE = ("não", "nao", "sem", "nunca tive", "nao tenho", "nunca tenho")
_EXCLUSIVITY_POSITIVE = ("sim", "tenho", "já tenho", "possuo", "exclusividade")

_LEAD_NAME_PATTERNS = (
    r"meu nome e (.+)",
    r"meu nome é (.+)",
    r"me chamo (.+)",
    r"sou (.+)",
)
_LEAD_ORIGIN_PATTERNS = (
    ("google", "google"),
    ("instagram", "instagram"),
    ("facebook", "facebook"),
    ("tiktok", "tiktok"),
    ("linkedin", "linkedin"),
)
_STATE_PROGRESS_SIGNALS = (
    "sim",
    "claro",
    "ok",
    "beleza",
    "vamos",
    "pode",
    "quero",
    "interessado",
)

_E5_TRIGGER_TERMS = (
    "agendar",
    "agendamento",
    "consultor",
    "falar com",
    "pessoa",
    "quero falar",
)
_E6_TRIGGER_TERMS = (
    "depois",
    "mais tarde",
    "agora nao",
    "agora não",
    "não quero",
    "nao quero",
    "sem interesse",
    "encerrar",
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


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _contains_any(value: str, phrases: tuple[str, ...]) -> bool:
    normalized = _normalize_text(value)
    return any(phrase in normalized for phrase in phrases)


def _extract_last_words(value: str, max_words: int = 12) -> str:
    words = [word for word in re.split(r"\s+", value.strip()) if word]
    return " ".join(words[:max_words])


def _extract_lead_name(message: str) -> str | None:
    for pattern in _LEAD_NAME_PATTERNS:
        match = re.match(pattern, _normalize_text(message))
        if not match:
            continue
        name = match.group(1).strip().title()
        return " ".join(name.split()) if name else None
    return None


def _extract_lead_origin(message: str) -> str | None:
    normalized = _normalize_text(message)
    for _, origin in _LEAD_ORIGIN_PATTERNS:
        if origin in normalized:
            return origin
    return None


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


def _merge_latest_fields(
    latest_fields: dict[str, str | None],
    previous_fields: dict[str, str | None],
) -> dict[str, str | None]:
    merged = dict(previous_fields)
    merged.update({key: value for key, value in latest_fields.items() if value is not None})
    return merged


def _merge_owner_fields(
    latest_fields: dict[str, str | bool | int | float | None],
    previous_fields: dict[str, str | bool | int | float | None],
) -> dict[str, str | bool | int | float | None]:
    merged = dict(previous_fields)
    for key, value in latest_fields.items():
        if value is not None:
            merged[key] = value
    return merged


def _find_profile_hint(message: str) -> LeadProfile | None:
    normalized = _normalize_text(message)

    is_owner = _contains_any(normalized, _OWNER_PROFILE_HINTS)
    is_investor = _contains_any(normalized, _INVESTOR_PROFILE_HINTS)
    out_of_scope = _contains_any(normalized, _OUT_OF_SCOPE_GAP_REASONS)

    if out_of_scope:
        return "fora_de_escopo"
    if is_owner and is_investor:
        return "investidor"
    if is_owner:
        return "proprietario"
    if is_investor:
        return "investidor"
    return None


def _parse_money_amounts(message: str) -> list[float]:
    normalized = _normalize_text(message)
    normalized = normalized.replace(".", "").replace(",", ".")
    matches = re.findall(r"(?<!\d)(\d+(?:\.\d+)?)(?:\s*(?:mil|k))?", normalized)
    amounts: list[float] = []
    for raw in matches:
        try:
            amounts.append(float(raw))
        except ValueError:
            continue
    return amounts


def _extract_investor_fields(message: str) -> dict[str, str | None]:
    normalized = _normalize_text(message)

    capital = None
    money_values = _parse_money_amounts(message)
    if money_values:
        capital = (
            f"até {money_values[-1]:g}"
            if _contains_any(normalized, ("ate", "até", "maximo", "máximo"))
            else f"{money_values[0]:g}"
        )

    horizon = None
    horizon_match = re.search(
        r"(\d+)\s*(m?meses?|mes|dias|semanas|semana|mês|meses)",
        normalized,
    )
    if horizon_match:
        horizon = f"{horizon_match.group(1)} {horizon_match.group(2)}"

    if "comparando" in normalized:
        stage = "comparando_opcoes"
    elif "entendendo" in normalized or "entender" in normalized:
        stage = "entendendo_proposta"
    else:
        stage = None

    if "renda mensal" in normalized:
        motivation = "renda_mensal"
    elif "diversificar" in normalized:
        motivation = "diversificar"
    elif "proteger" in normalized or "patrimonio" in normalized or "patrimônio" in normalized:
        motivation = "proteger_patrimonio"
    else:
        motivation = None

    if "financiamento" in normalized:
        funding = "financiamento"
    elif "recurso proprio" in normalized or "recurso próprio" in normalized:
        funding = "proprio"
    else:
        funding = None

    if "pj" in normalized or "pessoa juridica" in normalized or "empresa" in normalized:
        pf_pj = "PJ"
    elif "pf" in normalized or "pessoa fisica" in normalized or "pessoa física" in normalized:
        pf_pj = "PF"
    else:
        pf_pj = None

    return {
        "motivation": motivation,
        "decision_stage": stage,
        "capital_band": capital,
        "funding_source": funding,
        "horizon": horizon,
        "pf_pj": pf_pj,
    }


def _parse_bool(message: str, positive: tuple[str, ...], negative: tuple[str, ...]) -> bool | None:
    normalized = _normalize_text(message)
    has_positive = _contains_any(normalized, positive)
    has_negative = _contains_any(normalized, negative)
    if has_positive and not has_negative:
        return True
    if has_negative and not has_positive:
        return False
    return None


def _parse_owner_fields(message: str) -> dict[str, str | bool | int | float | None]:
    normalized = _normalize_text(message)

    city_match = re.search(r"\bcidade\s+([a-zã-õç ]{2,60})", normalized)
    city = city_match.group(1).strip() if city_match else None

    concession_match = re.search(
        r"\b(concessionaria|distribuidora)\s+([a-zã-õç ]{2,60})",
        normalized,
    )
    concession = concession_match.group(2).strip() if concession_match else None

    power_match = re.search(r"(\d+(?:\.\d+)?)\s*(kwp|kw)", normalized)
    power = float(power_match.group(1)) if power_match else None

    ociosa_match = re.search(r"(\d+(?:\.\d+)?)\s*%", normalized)
    ociosa = float(ociosa_match.group(1)) if ociosa_match else None

    operation_match = re.search(
        r"\b(?:data|em)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        normalized,
    )
    operation = operation_match.group(1) if operation_match else None

    return {
        "homologada": _parse_bool(normalized, _HOMOLOGATION_POSITIVE, _HOMOLOGATION_NEGATIVE),
        "exclusividade": _parse_bool(normalized, _EXCLUSIVITY_POSITIVE, _EXCLUSIVITY_NEGATIVE),
        "concessionaria": concession,
        "cidade_uf": city,
        "potencia_kwp": power,
        "data_operacao": operation,
        "capacidade_ociosa_pct": ociosa,
    }


def _estimate_horizon_days(horizon: str | None) -> int | None:
    if not horizon:
        return None
    match = re.search(r"(\d+)\s*(meses?|dias|semanas?)", _normalize_text(horizon))
    if not match:
        return None

    value = int(match.group(1))
    unit = match.group(2)
    if "mes" in unit:
        return value * 30
    if "sem" in unit:
        return value * 7
    return value


def _capital_value(capital_band: str | None) -> float | None:
    if not capital_band:
        return None
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", _normalize_text(capital_band).replace(",", "."))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _detect_compliance_violation(message: str) -> str | None:
    normalized = _normalize_text(message)
    if _contains_any(normalized, _COMPLIANCE_TRIGGER_WORDS):
        return (
            "Pergunta regulatória/financeira identificada. "
            "Responder com padrão de escalonamento para o consultor."
        )

    if _contains_any(normalized, _COMPLIANCE_QUESTIONS):
        return (
            "Pergunta de custo/retorno/valores identificada. "
            "Responder com padrão de escalonamento para o consultor."
        )

    if any(keyword in normalized for keyword in ("procon", "advogado", *_COMPLIANCE_LEGAL)):
        return "Questão jurídica/regulatória identificada. Escalonar para consultor."

    return None


def _calculate_investor_score(
    message_fields: dict[str, str | None],
    *,
    profile: LeadProfile,
) -> tuple[LeadScore | None, str | None]:
    if profile != "investidor":
        return None, None

    motivation = message_fields.get("motivation")
    capital = _capital_value(message_fields.get("capital_band"))
    horizon = _estimate_horizon_days(message_fields.get("horizon"))

    if capital is not None and capital < _MIN_INVESTOR_CAPITAL_BRL:
        return "D", f"Capital abaixo do mínimo de {_MIN_INVESTOR_CAPITAL_BRL}."

    if not motivation:
        return "C", "Motivacao ainda nao coletada."

    if motivation and capital is not None and horizon is not None and horizon <= 90:
        return "A", "Motivacao clara, capital no minimo e horizonte curto."

    if motivation and (capital is not None or horizon is not None):
        return "B", "Perfil promissor, aguarda complementar informacoes."

    return "C", "Perfil com sinal de interesse inicial."


def _is_owner_rejected(owner_fields: dict[str, Any], message: str) -> tuple[bool, str | None]:
    homologada = owner_fields.get("homologada")
    exclusividade = owner_fields.get("exclusividade")
    city = owner_fields.get("cidade_uf") or ""

    if homologada is False:
        return True, "Usina sem homologacao ativa."
    if exclusividade is True:
        return True, "Usina com exclusividade ativa com outra gestora."
    if _contains_any(city, ("fora de cobertura", "nao atende", "não atende")):
        return True, "Cidade/UF fora da cobertura atual."
    if _contains_any(message, ("gestor", "já tem gestor", "já tem gestora")) and _contains_any(
        message, ("contrato", "exclusivo", "exclusiva")
    ):
        return True, "Lead informa relacionamento com outra gestora."
    if _contains_any(
        message,
        (
            "gerenciar clientes",
            "gerenciar meus clientes",
            "gestao de clientes",
            "gero os clientes",
        ),
    ):
        return True, "Lead indica gestão de carteira própria."

    if _contains_any(message, ("quero vender", "tenho interesse em vender")):
        return True, "Lead indica venda da usina, oportunidade fora do fluxo padrão."

    return False, None


def _infer_profile_from_context(state: AgentState) -> LeadProfile:
    resume_context = _normalize_text(str(state.get("resume_context") or ""))
    if "proprietario" in resume_context or "usina" in resume_context:
        return "proprietario"
    if "investidor" in resume_context or "investir" in resume_context:
        return "investidor"
    if _contains_any(state.get("latest_user_message") or "", _OWNER_PROFILE_HINTS):
        return "proprietario"
    return "investidor"


def _can_progress_investor_to_e3(investor_fields: dict[str, str | None]) -> bool:
    return bool(investor_fields.get("motivation"))


def _has_minimum_investor_data(investor_fields: dict[str, str | None]) -> bool:
    return bool(
        investor_fields.get("motivation")
        and (investor_fields.get("capital_band") or investor_fields.get("horizon"))
    )


def _has_minimum_owner_data(owner_fields: dict[str, Any], state: AgentState) -> bool:
    if owner_fields["homologada"] is not True:
        return False
    if owner_fields["exclusividade"] is True:
        return False
    if owner_fields["homologada"] is None and state.get("homologada") is False:
        return False
    if owner_fields["exclusividade"] is None and state.get("exclusividade") is True:
        return False

    has_power = owner_fields["potencia_kwp"] is not None or state.get("potencia_kwp") is not None
    has_operation_date = owner_fields["data_operacao"] is not None or state.get("data_operacao")
    has_idle_capacity = (
        owner_fields["capacidade_ociosa_pct"] is not None
        or state.get("capacidade_ociosa_pct") is not None
    )
    if not has_power or not has_operation_date or not has_idle_capacity:
        return False

    has_location = bool(owner_fields["cidade_uf"] or owner_fields["concessionaria"])
    if not has_location:
        return False
    return True


def _can_progress_owner_to_e3(owner_fields: dict[str, Any], state: AgentState) -> bool:
    if owner_fields["homologada"] is False:
        return False

    if owner_fields["exclusividade"] is True:
        return False

    if owner_fields["homologada"] is None and state.get("homologada") is False:
        return False

    return bool(owner_fields["cidade_uf"] or owner_fields["concessionaria"])


def _next_journey_state(
    state: AgentState,
    latest_message: str,
    *,
    profile: LeadProfile,
    investor_fields: dict[str, str | None],
    owner_fields: dict[str, Any],
    compliance_violation: str | None,
    out_of_scope_reason: str | None,
) -> tuple[JourneyState, int, str]:
    current_state = state.get("journey_state") or "E0"
    lead_gap = int(state.get("lead_contact_gap") or 0)
    normalized = _normalize_text(latest_message)

    # Gold rule: never skip E1.
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
            assumed = _infer_profile_from_context(state)
            return (
                "E2a" if assumed == "investidor" else "E2b",
                0,
                "Sem resposta de triagem em dois toques; perfil assumido pelo contexto.",
            )

        return "E1", lead_gap, "Triagem sem resposta objetiva ainda."

    if current_state == "E2a":
        if profile == "proprietario":
            return "E2b", 0, "Reclassificacao para perfil proprietario sem reiniciar."

        if out_of_scope_reason:
            return "E6", 0, "Lead fora de escopo."

        if profile == "investidor" and _can_progress_investor_to_e3(investor_fields):
            return "E3", 0, "Qualificacao inicial coletada e validada."

        if _contains_any(normalized, ("agendar", "consultor", "falar com", "quero seguir")):
            return "E3", 0, "Lead demonstrou interesse e segue para explicacao do modelo."

        return "E2a", 0, "Coletando dados de investidor."

    if current_state == "E2b":
        if profile == "investidor":
            return "E2a", 0, "Reclassificacao para perfil investidor sem reiniciar."

        if out_of_scope_reason:
            return "E6", 0, "Lead fora de escopo na qualificacao proprietario."

        if _is_owner_rejected(owner_fields, latest_message)[0]:
            return "E6", 0, "Trava de proprietario ativa."

        if _can_progress_owner_to_e3(owner_fields, state):
            return "E3", 0, "Travas verificadas para proprietario."

        return "E2b", 0, "Coletando dados de proprietario."

    if current_state == "E3":
        if out_of_scope_reason:
            return "E6", 0, "Lead saiu do escopo na fase de explicacao."
        if _contains_any(normalized, _E6_TRIGGER_TERMS):
            return "E6", 0, "Lead pediu pausa/encerramento."
        if _contains_any(normalized, _E5_TRIGGER_TERMS):
            if not (
                profile == "fora_de_escopo"
                or _has_minimum_investor_data(investor_fields)
                or _has_minimum_owner_data(owner_fields, state)
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
        if _contains_any(normalized, _E6_TRIGGER_TERMS):
            return "E6", 0, "Lead pediu pausa/encerramento na coleta."
        if _contains_any(normalized, _E5_TRIGGER_TERMS):
            if not (
                profile == "fora_de_escopo"
                or _has_minimum_investor_data(investor_fields)
                or _has_minimum_owner_data(owner_fields, state)
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
) -> str | None:
    if out_of_scope_reason:
        return out_of_scope_reason
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
        updates["capital_faixa"] = None  # type: ignore[index]
        updates["origem_recurso"] = None  # type: ignore[index]
        updates["horizonte"] = None
        updates["horizonte_decisao"] = None
        updates["pf_pj"] = None  # type: ignore[index]
    if previous_profile == "proprietario":
        updates["homologada"] = None
        updates["exclusividade"] = None
        updates["concessionaria"] = None
        updates["cidade_uf"] = None
        updates["potencia_kwp"] = None  # type: ignore[index]
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
            f"Homologada: {owner_fields['homologada'] or state.get('homologada')}",
            f"Exclusividade: {owner_fields['exclusividade'] or state.get('exclusividade')}",
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


def _update_flow(state: AgentState, latest_message: str) -> dict[str, Any]:
    current_profile = state.get("profile") or "unknown"
    current_state = state.get("journey_state") or "E0"
    latest_investor_fields = _extract_investor_fields(latest_message)
    latest_owner_fields = _parse_owner_fields(latest_message)

    investor_fields = _merge_latest_fields(
        latest_investor_fields,
        previous_fields=_investor_fields_from_state(state),
    )
    owner_fields = _merge_owner_fields(
        latest_fields=latest_owner_fields,
        previous_fields=_owner_fields_from_state(state),
    )

    profile_hint = _find_profile_hint(latest_message)

    profile: LeadProfile
    if profile_hint is not None:
        profile = profile_hint
    elif current_profile in {"investidor", "proprietario", "fora_de_escopo", "unknown"}:
        if current_profile == "investidor" and _contains_any(latest_message, _OWNER_PROFILE_HINTS):
            profile = "proprietario"
        elif current_profile == "proprietario" and _contains_any(
            latest_message, _INVESTOR_PROFILE_HINTS
        ):
            profile = "investidor"
        else:
            profile = current_profile
    else:
        profile = _infer_profile_from_context(state)

    if profile in {"investidor", "proprietario", "fora_de_escopo"} and profile != current_profile:
        LOGGER.info(
            "agent.journey.reclassified",
            extra={"previous_profile": current_profile, "new_profile": profile},
        )

    out_of_scope_reason = None
    if profile == "fora_de_escopo":
        out_of_scope_reason = "Lead fora de escopo (conta de luz/telhado)."
    if _contains_any(latest_message, _INVESTMENT_OUT_OF_SCOPE):
        out_of_scope_reason = "Mensagem indica necessidade fora do produto de gestao de usinas."

    compliance_violation = _detect_compliance_violation(latest_message)
    owner_rejected, owner_reason = _is_owner_rejected(owner_fields, latest_message)
    if owner_rejected:
        profile = "proprietario"
        out_of_scope_reason = out_of_scope_reason or owner_reason

    score: LeadScore | None = None
    if profile == "investidor":
        score, _ = _calculate_investor_score(investor_fields, profile=profile)

    next_state, lead_gap, transition_reason = _next_journey_state(
        state,
        latest_message,
        profile=profile,
        investor_fields=investor_fields,
        owner_fields=owner_fields,
        compliance_violation=compliance_violation,
        out_of_scope_reason=out_of_scope_reason,
    )

    disposition = state.get("disposition")
    if out_of_scope_reason:
        disposition = "out_of_scope"
    if compliance_violation:
        disposition = "handoff_due_to_compliance"
    if next_state in {"E5", "E6"} and disposition is None:
        disposition = "handoff_ready"

    handoff_reason = _handoff_reason(profile, out_of_scope_reason, compliance_violation)

    transition = _transition_log_entry(
        prev_state=current_state,
        next_state=next_state,
        profile=profile,
        score=score,
        message=_extract_last_words(_normalize_text(latest_message), max_words=16),
        reason=transition_reason,
    )
    transition_log = _merge_transition_log(state, transition)

    updates: dict[str, Any] = {
        "profile": profile,
        "journey_state": next_state,
        "lead_contact_gap": lead_gap,
        "transition_reason": transition_reason,
        "journey_transitions": transition_log,
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
    }

    if score is not None:
        updates["score"] = score
    if disposition is not None:
        updates["disposition"] = disposition
    updates["out_of_scope_reason"] = out_of_scope_reason
    updates["handoff_reason"] = handoff_reason
    updates["compliance_violation"] = compliance_violation

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
    lead_name = _extract_lead_name(latest_message)
    if lead_name or state.get("lead_name"):
        updates["lead_name"] = lead_name or state.get("lead_name")
    lead_origin = _extract_lead_origin(latest_message)
    if lead_origin or state.get("lead_origin"):
        updates["lead_origin"] = lead_origin or state.get("lead_origin")

    _clear_previous_profile_fields(updates, current_profile, profile)
    if "perfil assumido pelo contexto" in transition_reason:
        updates["disposition"] = "triage_assumed_uncertain"

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
) -> dict[str, str]:
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
        {"latest_user_message": latest_message},
        config=config,
    )

    flow_updates = _update_flow(state, latest_message)

    return {
        "latest_user_message": latest_message,
        "intent": result.intent,
        "intent_reason": result.reason,
        "requires_specialist": result.requires_specialist,
        "specialist_name": result.specialist_name,
        "specialist_reason": result.specialist_reason,
        **flow_updates,
    }
