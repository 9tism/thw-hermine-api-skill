# CLAUDE.md

Project: **thw-hermine-api-skill** – the shareable, anonymised Claude skill „thw-hermine-api“
(German) about the API of Hermine, the THW messenger based on stashcat, plus a standalone
reference client in `thw-hermine-api/scripts/hermine_client.py`.

Texts in the skill, comments and CLI output are German; keep it that way.

## Layout

- `thw-hermine-api/` – the skill itself (`SKILL.md`, `README.md`, `LICENSE`, `references/`,
  `scripts/hermine_client.py` + `requirements.txt`, `evals/`).
- `thw-hermine-api-workspace/` – eval runs and benchmarks from the skill-creator (gitignored).
- `dist/` – built ZIPs (gitignored).

## Workflow

- When new Hermine knowledge turns up, update the skill and the reference client together.
- Release: bump `metadata.version` in `SKILL.md`, the version in `README.md` and
  `__version__` in `scripts/hermine_client.py`, then build the ZIP (evals stay out):

  ```sh
  zip -rq -X dist/YYYYMMDD-thw-hermine-api-<version>.zip thw-hermine-api -x "*/__pycache__/*" "thw-hermine-api/evals/*"
  ```

## Constraints

- Keep personal data (names, IDs, unit, e-mail addresses) out of the skill.
- The reference client stays read-only plus exactly one write (`message/send`), and it
  identifies honestly – never spoof official clients or browsers.
- Test sending only in a channel the user names explicitly.
