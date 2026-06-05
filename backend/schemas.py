"""Pydantic models matching the frontend's expected data shapes (from data.js mockup)."""

from pydantic import BaseModel


class FireRequest(BaseModel):
    prompt: str
    knowledge_layer: str
    n_trials: int = 8
    injection_mode: str = "system_user"


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
