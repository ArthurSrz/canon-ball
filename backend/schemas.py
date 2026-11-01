"""Pydantic models matching the frontend's expected data shapes."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class FireRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
    prompt: str
    knowledge_layer: str
    n_trials: int = 16
    injection_mode: str = "template"
    # Both arms are rendered from `knowledge_layer`. "none" leaves the control arm bare.
    # The test arm is fired as a knowledge graph; the control arm carries the same facts
    # in prose, so the delta between them is the graph, not the content.
    knowledge_form: str = "knowledge_graph"
    control_knowledge_form: str = "prose"
    # Tokens a single shot may generate. None uses canon_experiment's default; raising it
    # lets long answers finish, and moves the dispersion numbers with them.
    max_tokens: int | None = None


class StructureRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
    knowledge_layer: str
    form: str = "knowledge_graph"


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
