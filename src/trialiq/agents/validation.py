"""Validation agent: gates synthesis on deterministic retrieval results."""
from trialiq.services.models import ConditionSearchStatus, EntitySearchStatus, GraphQueryStatus

from .models import AgentStatus, RetrievalResult, ValidationResult


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


class ValidationAgent:
    def run(self, retrieval: RetrievalResult) -> ValidationResult:
        errors = list(retrieval.errors)
        warnings = list(retrieval.warnings)

        if retrieval.graph_response is not None:
            response = retrieval.graph_response
            errors.extend(response.validation.errors)
            warnings.extend(response.validation.warnings)

            if response.status != GraphQueryStatus.SUCCESS or not response.validation.valid:
                status = (
                    AgentStatus.VALIDATION_FAILED
                    if response.status == GraphQueryStatus.VALIDATION_FAILED
                    else AgentStatus(response.status.value)
                )
                return ValidationResult(
                    status=status,
                    can_synthesize=False,
                    errors=_unique(errors),
                    warnings=_unique(warnings),
                )

            if not response.evidence or not response.evidence.get("trial"):
                errors.append("Trial evidence is missing.")
                return ValidationResult(
                    status=AgentStatus.INSUFFICIENT_EVIDENCE,
                    can_synthesize=False,
                    errors=_unique(errors),
                    warnings=_unique(warnings),
                )

            return ValidationResult(
                status=AgentStatus.SUCCESS,
                can_synthesize=True,
                errors=[],
                warnings=_unique(warnings),
            )

        if retrieval.condition_search_response is not None:
            response = retrieval.condition_search_response
            errors.extend(response.validation.errors)
            warnings.extend(response.validation.warnings)

            if response.status != ConditionSearchStatus.SUCCESS or not response.validation.valid:
                return ValidationResult(
                    status=AgentStatus(response.status.value),
                    can_synthesize=False,
                    errors=_unique(errors),
                    warnings=_unique(warnings),
                )

            return ValidationResult(
                status=AgentStatus.SUCCESS,
                can_synthesize=True,
                errors=[],
                warnings=_unique(warnings),
            )

        if retrieval.entity_search_response is not None:
            response = retrieval.entity_search_response
            errors.extend(response.validation.errors)
            warnings.extend(response.validation.warnings)
            if response.status != EntitySearchStatus.SUCCESS or not response.validation.valid:
                return ValidationResult(status=AgentStatus(response.status.value), can_synthesize=False, errors=_unique(errors), warnings=_unique(warnings))
            if not response.matches:
                return ValidationResult(status=AgentStatus.INSUFFICIENT_EVIDENCE, can_synthesize=False, errors=_unique(errors) or ["Entity search returned no matches."], warnings=_unique(warnings))
            return ValidationResult(status=AgentStatus.SUCCESS, can_synthesize=True, errors=[], warnings=_unique(warnings))

        if retrieval.related_trial_response is not None:
            response = retrieval.related_trial_response
            errors.extend(response.validation.errors)
            warnings.extend(response.validation.warnings)
            if response.status != GraphQueryStatus.SUCCESS or not response.validation.valid:
                return ValidationResult(status=AgentStatus(response.status.value), can_synthesize=False, errors=_unique(errors), warnings=_unique(warnings))
            if not response.matches:
                return ValidationResult(status=AgentStatus.INSUFFICIENT_EVIDENCE, can_synthesize=False, errors=_unique(errors) or ["Related-trial traversal returned no matches."], warnings=_unique(warnings))
            if any(not match.connected_via for match in response.matches):
                return ValidationResult(status=AgentStatus.INSUFFICIENT_EVIDENCE, can_synthesize=False, errors=_unique(errors) or ["Related-trial path evidence is missing."], warnings=_unique(warnings))
            return ValidationResult(status=AgentStatus.SUCCESS, can_synthesize=True, errors=[], warnings=_unique(warnings))

        if retrieval.shared_entity_response is not None:
            response = retrieval.shared_entity_response
            errors.extend(response.validation.errors)
            warnings.extend(response.validation.warnings)
            if response.status != GraphQueryStatus.SUCCESS or not response.validation.valid:
                return ValidationResult(status=AgentStatus(response.status.value), can_synthesize=False, errors=_unique(errors), warnings=_unique(warnings))
            return ValidationResult(status=AgentStatus.SUCCESS, can_synthesize=True, errors=[], warnings=_unique(warnings))

        if retrieval.status != AgentStatus.SUCCESS:
            return ValidationResult(
                status=retrieval.status,
                can_synthesize=False,
                errors=_unique(errors) or [f"Retrieval ended with status {retrieval.status.value}."],
                warnings=_unique(warnings),
            )

        return ValidationResult(
            status=AgentStatus.INSUFFICIENT_EVIDENCE,
            can_synthesize=False,
            errors=_unique(errors) or ["No retrieval response was produced."],
            warnings=_unique(warnings),
        )
