from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, conint, model_validator


class AgentGenerationRequest(BaseModel):
    case_id: str


class GeneratedAgent(BaseModel):
    role: Literal["consumer", "supporter", "critic", "media"]
    stance: str = Field(min_length=1)
    concern: str = Field(min_length=1)
    emotional_sensitivity: conint(ge=1, le=10)
    spread_tendency: conint(ge=1, le=10)
    persona_description: str = Field(min_length=1)
    initial_beliefs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _normalize(self) -> "GeneratedAgent":
        self.initial_beliefs = [value.strip() for value in self.initial_beliefs if value.strip()]
        return self


class AgentGenerationResponse(BaseModel):
    case_id: str
    case_status: str
    agents: list[GeneratedAgent]
