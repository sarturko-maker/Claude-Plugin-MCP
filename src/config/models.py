"""Pydantic model for loaded negotiation configuration.

The NegotiationConfig model holds markdown strings that Claude reads as prompt
context. The engine never interprets this content -- it passes through to the
LLM. The model also tracks whether custom configuration was found, which
triggers the conversational setup flow when False.
"""

from pydantic import BaseModel


class NegotiationConfig(BaseModel):
    """Loaded negotiation configuration.

    All string fields are markdown that Claude reads as prompt context.
    The engine never interprets this content -- it passes through to the LLM.

    Attributes:
        persona: Persona markdown describing who Claude is as a lawyer.
        authority: Authority framework markdown defining what Claude can
            and cannot do autonomously.
        playbook: Playbook markdown with clause-by-clause guidance.
            Empty string if no playbook is configured.
        has_custom_config: True if any custom config files were found
            (not just shipped defaults). When False, Claude should offer
            the conversational setup flow.
    """

    persona: str
    authority: str
    playbook: str = ""
    has_custom_config: bool = False
