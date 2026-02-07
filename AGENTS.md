# Repository-wide agent guidelines

## Scope

- This file applies to the entire repository and all AI-assisted changes.
- For role-specific guidelines, see the [`agents/`](agents/) directory.

## Agent Roles

This repository uses a three-layer agent role system:

1. **AGENTS.md** (this file) - Global rules & non-negotiables
2. **agents/*.md** - Reusable role definitions (see [`agents/index.md`](agents/index.md))
3. **Prompt** - Task-specific instructions (usage pattern, not a file)

Available agents:
- **[Planner Agent](agents/planner-agent.md)** - **Default entry point: analyzes prompts and coordinates other agents**
- [Backend Solver Agent](agents/backend-solver-agent.md) - Backend/domain logic guidance
- [Frontend UI Agent](agents/frontend-ui-agent.md) - React/TypeScript, Material-UI components
- [API Agent](agents/api-agent.md) - FastAPI endpoints, request/response handling
- [Testing Agent](agents/testing-agent.md) - pytest, Vitest, test coverage
- [Data Agent](agents/data-agent.md) - Data files, schemas, validation

**Note:** The Planner Agent is the default coordinator. When no specific agent is mentioned, it will analyze the prompt and route to the appropriate specialized agent(s).

## Exceptions & Overrides

- If a user request directly contradicts this document:
    1. The agent MUST pause and call out the conflict explicitly
    2. The agent MUST ask whether this is a one-off exception or a new rule
    3. The agent MUST NOT silently violate existing guidelines
- If an exception is approved, the agent should:
    - Propose an update to this file explaining why the exception exists
    - Scope the exception narrowly (what changes, what does not)
 
## Intent Clarity

- Do not infer unstated goals
- Do not generalize a specific request into a broader redesign
- If intent is ambiguous, ask before acting

## Entry Points

- **CLI:** `{{CLI_ENTRY_POINT}}` <CLI command or module>
- **API:** `{{API_ENTRY_POINT}}` <API start command>
- **Frontend:** `{{FRONTEND_ENTRY_POINT}}` <frontend dev server command>
- **Tutorial/Examples:** `{{TUTORIAL_ENTRY_POINT}}` <tutorial or examples command>

## Repository overview

See `docs/repo_overview.md` for the repo map, entry points, and pointers to key files.

## Placeholder audit

See `docs/audit.md` to track placeholder replacement during setup.

## Template and architecture

- `docs/TEMPLATE.md` - Template philosophy and required customizations
- `docs/architecture.md` - Architecture template (data flow, boundaries, invariants)

For detailed workflow instructions, see:
- [Frontend UI Agent](agents/frontend-ui-agent.md) - UI development workflow
- [API Agent](agents/api-agent.md) - API development workflow
- [Data Agent](agents/data-agent.md) - Data file management

## Configuration

- Configuration files live in `{{CONFIG_PATHS}}` <config file paths>
- Configuration helpers are in `{{CONFIG_HELPER_PATHS}}` <helper module paths>
- Do NOT rename or remove config keys without updating the schema and tutorial
- See [Data Agent](agents/data-agent.md) for data file management guidelines

---

For domain-specific backend examples, see [Backend Solver Agent](agents/backend-solver-agent.md).

---

## Architecture Constraints

- Separation of concerns must be maintained:
  - Data loading must not contain scoring logic
  - Scoring logic must not perform search
  - Search logic must not embed configuration defaults
  - UI code must not contain solver logic
- Prefer small, localized changes over global refactors
- Large refactors must be split into staged, reviewable steps
- For solver-specific architecture constraints, see [Backend Solver Agent](agents/backend-solver-agent.md)

## Coding Conventions

- Follow both Python and TypeScript standards as appropriate
- Prefer explicit, readable logic over clever optimizations
- Avoid introducing new dependencies unless necessary

## Pre-Commit Requirements

All code must pass pre-commit hooks before committing. The following standards are enforced:

### Code Formatting (Black)
- **Line length:** Maximum 100 characters per line
- Black will auto-format code, but agents should write code that follows this limit
- Run `black --line-length=100` to format code before committing

### File Standards
- Files must end with a newline character
- No trailing whitespace allowed
- YAML, JSON, and TOML files must be valid
- No merge conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
- Large files (>500KB) will be blocked

### Type Checking (MyPy)
- MyPy runs with relaxed settings to allow gradual typing
- Current settings: `--ignore-missing-imports`, `--no-strict-optional`, `--allow-untyped-calls`, `--allow-untyped-defs`
- Several error codes are disabled (assignment, index, attr-defined, operator, call-arg, var-annotated, arg-type, call-overload)
- While strict typing is not enforced, agents should still write type-safe code when possible

### Best Practices for Agents
- Write code that will pass Black formatting (100 char line limit)
- Ensure files end with newlines
- Remove trailing whitespace
- Validate JSON/YAML syntax if creating or modifying these files
- Test that `pre-commit run --all-files` passes before considering code complete

## .gitignore Management

### When to Update .gitignore

**MUST update `.gitignore` when:**
- Creating or modifying build/compilation output directories (e.g., `dist/`, `build/`, `out/`)
- Adding test coverage tools that generate reports (e.g., `coverage/`, `htmlcov/`, `.coverage`)
- Introducing dependency management artifacts (e.g., `node_modules/`, `venv/`, `.venv/`, `__pycache__/`)
- Adding IDE/editor configuration directories (e.g., `.idea/`, `.vscode/`, `.vs/`)
- Creating temporary or cache directories (e.g., `.pytest_cache/`, `.mypy_cache/`, `.cache/`)
- Adding log files or runtime artifacts (e.g., `*.log`, `*.tmp`, `.env.local`)
- Setting up package managers that create lock files you don't want tracked (rare, but possible)
- Adding generated documentation or reports (e.g., auto-generated API docs, coverage HTML)

**SHOULD update `.gitignore` when:**
- Adding new tools or frameworks that generate artifacts
- Creating scripts that produce output files
- Setting up new development environments
- Adding configuration files that may contain secrets (e.g., `.env`, `secrets.json`)

**DO NOT add to `.gitignore`:**
- Source code files (`.py`, `.ts`, `.tsx`, `.js`, `.jsx`, etc.)
- Configuration files that are meant to be shared (e.g., `package.json`, `requirements.txt`, `vite.config.ts`)
- Documentation files (`.md`, `.txt`, `.rst`)
- Test files (they should be tracked)
- Schema files or data files that are part of the project
- Build configuration files (e.g., `Dockerfile`, `Makefile`, `.github/workflows/`)

### Categories of Files to Ignore

**Build Artifacts:**
- Compiled code: `*.pyc`, `*.class`, `*.o`, `*.so`, `*.dll`
- Build outputs: `dist/`, `build/`, `out/`, `target/`, `bin/`, `obj/`
- Bundled assets: `*.bundle.js`, `*.chunk.js` (if generated)

**Dependencies:**
- Package manager directories: `node_modules/`, `venv/`, `.venv/`, `env/`, `.env/`
- Package manager lock files: Only if explicitly not wanted (usually `package-lock.json` and `requirements.txt` ARE tracked)

**IDE/Editor Files:**
- IDE directories: `.idea/`, `.vscode/` (unless project-specific settings are shared), `.vs/`, `.eclipse/`
- Editor swap files: `*.swp`, `*.swo`, `*~`, `.DS_Store`

**Test & Coverage:**
- Coverage reports: `coverage/`, `htmlcov/`, `.coverage`, `coverage.xml`, `*.cover`, `.nyc_output/`
- Test cache: `.pytest_cache/`, `.mypy_cache/`, `.hypothesis/`

**Temporary & Runtime:**
- Log files: `*.log`, `logs/`, `*.tmp`
- Environment files: `.env.local`, `.env.*.local` (but `.env.example` should be tracked)
- Cache directories: `.cache/`, `.parcel-cache/`, `.next/`, `.nuxt/`

**OS-Specific:**
- System files: `.DS_Store`, `Thumbs.db`, `desktop.ini`
- OS directories: `.Trash-*`, `*.swp`

**Generated/Compiled Assets:**
- Image files that are generated: Only if they're build artifacts (not source assets)
- Compiled stylesheets: `*.css.map` (if generated), but not source `.css` files
- Minified files: `*.min.js`, `*.min.css` (if generated)

### Best Practices

1. **Be Specific**: Prefer specific paths over broad patterns when possible
   - Good: `frontend/coverage/`, `backend/htmlcov/`
   - Less ideal: `**/coverage/` (unless you have multiple coverage directories)

2. **Group Related Entries**: Use comments to organize sections
   ```gitignore
   # Coverage reports
   htmlcov/
   .coverage
   frontend/coverage/
   ```

3. **Check Before Adding**: Verify that files you're ignoring aren't needed by other developers
   - If a file is needed for the project to work, it should be tracked
   - If a file is generated or environment-specific, it should be ignored

4. **Document Unusual Exclusions**: If you ignore something non-standard, add a comment explaining why

5. **Review Existing Patterns**: Before adding new entries, check if an existing pattern already covers it
   - Example: `**/*.log` might already cover `app.log`

6. **Test Your Changes**: After modifying `.gitignore`, verify that:
   - Previously tracked files that should be ignored are now ignored
   - Important files are still tracked
   - The repository still builds/works correctly

### Common Mistakes to Avoid

- **Ignoring source files**: Never ignore `.py`, `.ts`, `.js`, `.tsx`, `.jsx` files
- **Ignoring configuration files**: Don't ignore `package.json`, `requirements.txt`, `vite.config.ts`, etc.
- **Ignoring test files**: Test files should be tracked
- **Too broad patterns**: Avoid patterns like `**/*.json` that might ignore important config files
- **Ignoring data files**: Project data files (like `data/en_us.json`) should be tracked
- **Forgetting to commit `.gitignore` changes**: Always commit `.gitignore` updates with the changes that require them

### When Creating New Directories or Tools

When introducing new tools, build processes, or directories that generate files:

1. **Identify generated files**: Determine what files/directories the tool creates
2. **Check if they should be tracked**: Generated artifacts typically should not be
3. **Update `.gitignore` immediately**: Add exclusions before committing any generated files
4. **Verify in CI/CD**: Ensure build processes work without tracked artifacts

### Example Workflow

When adding a new tool that generates reports:
```bash
# 1. Tool generates files in reports/ directory
# 2. Before committing, add to .gitignore:
echo "reports/" >> .gitignore
# 3. Verify it works:
git status  # Should not show reports/ files
# 4. Commit both the tool setup AND .gitignore update together
```

## Documentation

### When to Update README.md

Update `README.md` when changes affect **user-facing aspects** of the project:

- **User-facing features**: New modes, CLI options, or capabilities that users interact with
- **Setup/installation**: Changes to dependencies, environment setup, or prerequisites
- **Usage instructions**: New config fields, API endpoints, or workflow changes
- **Entry points**: Changes to how users run the tool (CLI commands, API routes)
- **Configuration**: New config fields or schema changes (also update `schemas/config_schema.json`)

**Examples:**
- Adding a new solver mode
- Changing CLI arguments or command syntax
- Adding new API endpoints
- Updating environment variable requirements
- Changing tutorial examples or quickstart instructions

### When to Update docs/

Update files in `docs/` when changes affect **technical implementation details**:

- **Algorithm behavior**: Changes to scoring, search logic, or decision-making (per "Change Discipline" section: "Any change that alters solver behavior must be documented")
- **Architecture**: Structural changes to code organization, data flow, or module responsibilities
- **Technical details**: Implementation specifics that explain how/why something works
- **Mode-specific behavior**: Changes to project-specific modes or feature variants

**Examples:**
- Modifying scoring thresholds or piecewise functions
- Changing quality definitions or constraints
- Updating search logic or pruning rules
- Adding new constraints or validity checks
- Refactoring that changes data flow between modules

### Doc-by-Doc Update Rules

- **`docs/repo_overview.md`**: Update when folder structure changes, entry points move, or key pointers change (new core docs, CI changes, tooling changes).
- **`docs/architecture.md`**: Update when data flow, module boundaries, or key invariants change.
- **`docs/DEPLOYMENT.md`**: Update when deployment strategy, hosting options, or environment variables change.
- **`docs/DEPLOYMENT_QUICKSTART.md`**: Update when the shortest deploy path changes or commands/URLs change.
- **`docs/audit.md`**: Update during setup to track placeholder replacement status and ownership.

### Decision Matrix

| Change Type | README.md | docs/ | Both |
|------------|-----------|-------|------|
| New solver mode | ✅ | ✅ | ✅ |
| Algorithm behavior change | ❌ | ✅ | ❌ |
| New config field | ✅ | ❌ | ❌ |
| API endpoint addition | ✅ | ❌ | ❌ |
| Scoring formula change | ❌ | ✅ | ❌ |
| Architecture refactor | ❌ | ✅ | ❌ |
| Bug fix (no behavior change) | ❌ | ❌ | ❌ |
| UI feature addition | ✅ | ❌ | ❌ |

### Documentation Best Practices

1. **Document intent, not just behavior**: Explain why decisions were made, not just what changed
2. **Update docs alongside code**: Don't defer documentation; update it in the same commit
3. **Keep examples current**: If you change behavior, update tutorial examples and code samples
4. **Cross-reference appropriately**: Link between README.md and docs/ when relevant
5. **Maintain consistency**: Follow existing documentation patterns and structure

## Testing

### General Testing Requirements

- **Coverage directories must be in `.gitignore`**: See ".gitignore Management" section for details
  - Backend: `htmlcov/`, `.coverage`, `coverage.xml`
  - Frontend: `frontend/coverage/`
- When setting up or modifying test coverage configuration, verify that:
  - Non-code files (images, data files, configs) are excluded from coverage
  - Coverage output directories are in `.gitignore`
  - Coverage thresholds meet project requirements (90% for frontend, 90% for backend)

### Backend Testing (ex: Python)

- Add or update tests in `/tests/` so future updates don't accidentally harm old features
- When changing scoring behavior, add at least one test that encodes the intended tradeoff
- Tests must pass before committing code changes
- Coverage must remain at or above 90% for `{{BACKEND_PACKAGES}}` <backend packages>
- See "Pre-Commit Requirements" section for code style standards enforced by pre-commit hooks
- Run `pytest --cov` to verify coverage before submitting changes
- Integration tests in `tests/integration/` exercise the complete stack (UI → API → Solver)

### Frontend Testing (ex: TypeScript/React)

- Frontend tests live in `{{FRONTEND_TEST_PATHS}}` <test folder>. Use the suite-specific sections below to avoid mixing requirements; coverage targets apply only to Unit/RTL tests and do not apply to MCP demo tests.
- Test utilities and mock data are in `{{FRONTEND_TEST_UTILS_PATHS}}` <test utils paths>

#### Unit/RTL Testing

- **Location**: `{{FRONTEND_TEST_PATHS}}` <test folder> (e.g. `*.test.tsx`, `*.test.ts`)
- **How to run**: `{{FRONTEND_TEST_COMMANDS}}` <test command(s)>
- **When to use**: Default for component behavior, edge cases, and coverage-driven changes

#### MCP Demo Testing

- **Location**: `{{FRONTEND_MCP_TEST_PATHS}}` <MCP test folder> (e.g. `*.mcp.test.tsx`)
- **How to run**: `{{FRONTEND_MCP_TEST_COMMANDS}}` <MCP test command(s)>
- **When to use**: Targeted, tool-invoked checks or demonstrations; not a CI replacement
- **Coverage**: No coverage requirement; MCP demo tests are excluded from coverage goals
- **Coverage requirement: Frontend code must maintain at least 90% test coverage**
  - Overall coverage targets: 90% statements, 90% functions, 75% branches, 90% lines
  - Component coverage should be 90%+ for all user-facing components
- Run frontend tests with:
  - `{{FRONTEND_TEST_ALL_COMMAND}}` <run all tests command> - Run all tests
  - `{{FRONTEND_TEST_COVERAGE_COMMAND}}` <coverage command> - Run tests with coverage report
  - `{{FRONTEND_TEST_WATCH_COMMAND}}` <watch command> - Run tests in watch mode
- Coverage reports are generated in `{{FRONTEND_COVERAGE_PATHS}}` <coverage output paths>
- When adding new frontend components or features:
  - Create corresponding test files following the naming pattern `ComponentName.test.tsx`
  - Test user interactions, edge cases, and error states
  - Use React Testing Library best practices (query by role, test user behavior)
  - Mock external dependencies (API calls, browser APIs)
- Test files should be comprehensive and cover:
  - Component rendering and display
  - User interactions (clicks, form inputs, navigation)
  - Error handling and edge cases
  - Integration with other components
- See `{{FRONTEND_COVERAGE_SUMMARY_PATH}}` <coverage summary path> for current test coverage status and patterns

For domain-specific anti-patterns, see [Backend Solver Agent](agents/backend-solver-agent.md).

## Change Discipline

- Any change that alters solver behavior must be documented
- If behavior changes, tests must change first or alongside code
- Refactors must not change outputs unless explicitly requested

## When in Doubt

- Prefer preserving existing behavior over simplification
- Prefer adding comments over rewriting logic
- Ask for clarification instead of guessing intent

## Change Scope & Blast Radius

- Prefer the smallest change that satisfies the request
- Avoid touching unrelated files or logic “while you’re there”
- Large refactors must be split into staged, reviewable steps

## Reversibility

- Prefer changes that are easy to undo
- Avoid destructive migrations or irreversible transformations
- When possible, gate new behavior behind flags or config options

## Glossary (Project-Specific)

- Add project-specific terms here after setup.

## Learning from Changes

- If a change reveals a missing rule or invariant:
    - Propose adding it to this document
- This file should evolve as the project’s intent becomes clearer
