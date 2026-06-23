"""Pydantic models matching the frontend's expected data shapes."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class FireRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
    prompt: str
    knowledge_layer: str
    n_trials: int = 16
    injection_mode: str = "template"


class TraceRequest(BaseModel):
    prompt: str
    system_prompt: str = ""
    max_tokens: int = 10


class FocalRequest(BaseModel):
    prompt: str
    knowledge_layer: str = ""
    max_tokens: int = 10
    nla_model: str = "gemma-3-27b-it"
    nla_source: str = "kitft-l41"
    nla_max_tokens: int = 192
