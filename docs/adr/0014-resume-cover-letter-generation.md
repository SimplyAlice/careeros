# ADR-0014: Resume/Cover Letter Generation — New Tables, Fact/Narrative Split, Local Storage Interim

## Status
Accepted

## Context

Milestone 6 implements AI-generated, versioned, PDF-rendered resumes and
cover letters. Three design questions needed resolving before writing any
code:

1. Two existing tables already touch "resumes": `resumes` (Milestone 2,
   flat, tied to `users`, never wired to any repository/service) and
   `resume_metadata` (Milestone 4, upload metadata only, explicitly no
   file content). Neither fits what Milestone 6 needs — versioned,
   AI-generated, job-tailorable, PDF-backed documents.
2. AI-generated resume content risks the same fabrication problem
   `docs/architecture/ai-architecture.md` already flags for resumes
   generally: an LLM asked to "write a resume" might invent skills,
   employers, or achievements the candidate doesn't actually have.
3. There's no cloud storage yet (Azure Blob Storage is documented in
   `docs/architecture/cloud-architecture.md` as the eventual home for
   generated documents, but isn't wired up) — generated PDFs need
   somewhere to live now.

## Decisions

### New tables, not reused ones

Add `generated_resumes` and `generated_cover_letters`, both tied to
`profiles.id` (the Milestone 4/5 pattern), left completely separate from
`resumes` and `resume_metadata`. `resumes` remains untouched and unused;
`resume_metadata` remains scoped to its original purpose (recording that
a resume *file* was uploaded, still with no content storage — out of
scope for this milestone). Reusing either would have required awkwardly
repurposing a table designed for something else; a new table costs
nothing extra and keeps each table's purpose legible.

### The AI writes narrative, not facts

`TailoredResumeContent` (the AI-generated portion) is deliberately narrow:
only a `professional_summary` and an `emphasized_skills` list. The
rendered resume's Experience and Education sections come directly,
unmodified, from the candidate's real `Profile` — the AI never touches
them. This is enforced in code, not just by prompt instruction:
`ResumeGenerationService._parse_response` rejects any `emphasized_skills`
entry that isn't a case-insensitive match against the profile's real
skills, raising `DocumentGenerationResponseError` rather than silently
accepting an invented skill. Cover letters follow the same principle: the
AI writes the body paragraphs; the greeting and sign-off are templated
deterministically at render time, not AI-generated.

### Local filesystem storage now, Azure Blob Storage later

`FileStorage` (`app/application/documents/ports.py`) is a `Protocol`
implemented today by `LocalFileStorage` (writes to a configurable local
directory, `GENERATED_DOCUMENTS_DIR`). This mirrors the Strategy pattern
already used for job sources (Milestone 3) and AI providers (Milestone
5): the interface is shaped to match what an Azure Blob Storage adapter
would need (`save`/`read` by path/key), so swapping backends later is a
new adapter class, not a design change.

### fpdf2 for PDF rendering

Chosen over WeasyPrint (requires system-level Cairo/Pango, complicating
the Docker image for no benefit here) and ReportLab (heavier, more dated
API for this need). fpdf2 is pure Python, needs no system dependencies,
and is sufficient for the plain, ATS-safe, single-column layout
`docs/architecture/system-design.md` (FR-10) already specifies for
resumes.

## Alternatives Considered

- **Let the AI generate the full resume, including experience/education
  text**, and rely entirely on prompt instructions ("don't invent
  anything") to keep it factual. Rejected: prompt instructions are not a
  reliable safety mechanism on their own — an occasional hallucinated
  bullet point in a resume has real consequences for the actual person
  using it. Grounding the factual sections directly in the real `Profile`
  data removes the failure mode structurally instead of hoping the model
  behaves.
- **Extend the Milestone 2 `resumes` table** with the new fields
  (job_id, professional_summary, emphasized_skills, file_path) instead of
  creating a new table. Rejected: `resumes.user_id` has the same
  pre-auth-blocker problem already solved for `job_matches`
  (`docs/adr/0013-score-against-profile-not-user.md`) and
  `candidate_profiles` (`docs/adr/0012-profile-management.md`) — reusing
  it would mean re-solving the same nullable-FK problem for a table that
  was never used in the first place, versus just building the right
  table from scratch.
- **Store generated PDFs as `BYTEA` directly in Postgres** instead of on
  the filesystem, avoiding the need for a `FileStorage` abstraction at
  all. Rejected: this couples document storage to the database's own
  scaling characteristics (large binary blobs bloat the database, slow
  backups) and forecloses the documented path to Blob Storage — an
  abstraction that costs one small interface is worth it here.

## Consequences

- `Job` (Milestone 3) gained two new relationships:
  `generated_resumes` (no `delete-orphan` cascade — a resume tailored to
  a job outlives that job's deletion, via `ON DELETE SET NULL`) and
  `generated_cover_letters` (`delete-orphan` cascade, since a cover
  letter is meaningless without the job it was written for, matching
  `ON DELETE CASCADE`). `Profile` (Milestone 4) gained the same two
  relationships, both with `delete-orphan` cascade.
- Local storage means generated documents don't survive a container
  rebuild unless `GENERATED_DOCUMENTS_DIR` is mounted as a Docker volume
  — acceptable for local development and this stage of the project;
  tracked as resolved once the Azure Blob Storage adapter lands.
- `requirements-dev.txt` gained `mypy` itself and `types-fpdf2` — the
  former closes a pre-existing gap (mypy was never actually declared as
  a dependency despite the README instructing `pip install -r
  requirements-dev.txt && mypy app`), found while adding the latter.
