# ADR-0005: Provider-Agnostic AI Abstraction Layer

## Status
Accepted

## Context
The project requires AI-generated scoring, resume tailoring, and cover letter
generation. LLM providers (Anthropic, OpenAI, Google Gemini) differ in SDKs,
pricing, and capability, and may need to be swapped over the project's life —
for cost, capability, or availability reasons.

## Decision
Define an `LLMProvider` protocol (`complete(system, prompt,
response_format) -> str`) that all application services depend on. Ship one
concrete adapter (Anthropic) in early milestones; add OpenAI/Gemini adapters
later behind the same interface. Provider selection is a config value
resolved via a factory at startup.

## Alternatives Considered
- **Hardcode a single provider's SDK directly in application services** —
  simpler initially, but couples business logic to a specific vendor's
  request/response shape, making a future provider swap a rewrite rather than
  a new adapter file. Rejected because "swap providers easily" is an explicit
  project requirement, not a hypothetical.
- **A heavyweight abstraction framework (e.g. LangChain) instead of a
  hand-rolled interface** — would provide more built-in tooling (chains,
  memory helpers), but adds a large dependency and abstraction surface for a
  need this project can meet with a small, explicit `Protocol` — favoring
  simplicity and full understanding of the code over framework convenience.

## Consequences
- Adding a new provider means writing one adapter class and registering it in
  the factory — no changes to scoring, resume-tailoring, or cover-letter
  service code.
- Structured output is enforced via Pydantic response schemas at the service
  layer, not inside the provider adapter — keeping the adapter interface
  provider-agnostic (a raw string in, validated object out at the call site).
- The trade-off is some upfront design work (defining the protocol, the
  factory, and per-provider prompt/response normalization) before any AI
  feature ships — a deliberate cost paid once, in Milestone 4, for
  flexibility across the rest of the project.
