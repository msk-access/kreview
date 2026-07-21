# Private memory (machine-local, gitignored)

Everything in this directory except this README is **gitignored**. It is where facts go that
are true only on one machine.

`.agents/memory/` is symlinked in as the Claude Code memory store *and* is committed to this
**public** repo. Those two facts together are a trap: an agent writing what it believes is a
private note is in fact writing to a public repository. This directory is the escape hatch.

## Which store does a fact go in?

> Would this sentence still be **true and useful** for a teammate who cloned the repo on a
> different machine?
>
> **Yes → `.agents/memory/` (public).  No → `.agents/memory/private/`.**

Mechanical tiebreaker: if writing the fact requires naming a path under `$HOME`, a hostname, a
username, a cluster allocation, or a personal account → **private**. If it is about the code,
its conventions, or a tooling policy → **public**.

| Fact | Store |
|---|---|
| "Nextflow ≤25.04 will not start on JDK 25" | public — true everywhere |
| "The JDK 17 lives in `~/mambaforge/envs/nf-env`" | private — one machine |
| "`nbdev-export` is the real exporter; `-m nbdev.export` is a no-op" | public |
| "IRIS allocation / partition names used by this account" | private |

## PHI is not a routing question

Patient identifiers, MRNs, SSNs, DOBs and clinical data are **forbidden in every store**,
private included. Private memory exists for machine-local *configuration* facts, not for
sensitive data. Nothing here is encrypted and nothing here is access-controlled — it is simply
not committed.

## Enforcement

`scripts/check_phi_guard.sh` (assertion 5, run by the pre-push hook and CI) fails if any
**tracked** file under `.agents/memory/` contains an absolute home path, or if this directory
stops being gitignored. That check exists because the mistake it catches has already happened
once: a machine-local note with an absolute path was written into the public store on the
belief that the Claude memory directory was separate from the repo.

## Discoverability

`MEMORY.md` is the only memory file always loaded into context, so private notes are listed
there by name under "Private" — the pointer line stays generic, the content stays here.
