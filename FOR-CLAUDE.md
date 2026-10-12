# For the Claude Code session installing this package

You are installing `/checkpoint` for the person you are working with. Read this file first, then `README.md`, then every file in the package before changing anything on their machine.

## What this package is

- A **sanitized, generalized copy** of a working setup that runs on another person's machine. Their name, home paths, private repo and machine-specific commands were replaced with settings and defaults. The logic is unchanged.
- It was tested end to end in a throwaway HOME with a local bare git remote. The tested steps were install, `checkpoint.py new`/`finish`/`set-url`, the start, prompt and end hooks, and `PUSH HELD` with the register as a subfolder. Publishing the artifact was **not** tested in that run; it works in the original setup.
- It targets macOS or Linux with `python3`, `git` and `pandoc`. It has not been tested on Windows.
- It is not a plugin. It is a skill, three hooks and a git-backed folder of Markdown, wired together by `settings.json` and a section of `~/.claude/CLAUDE.md`.

## What is fixed and what is yours to decide

Fixed (keep as-is unless the user asks):
- The checkpoint section headings and bold labels in `TEMPLATE.md`. `checkpoint.py` and `render.py` parse them.
- The five-column table in the register `README.md`. The hooks parse it.
- The markers `[done]`, `[superseded]`, `[obsolete]`, `[resolved]` and `[pinned]`, and the Sequence states `[done]`, `[now]`, `[gated: why]`, `[blocked: why]`, `[todo]`.
- The `patch` JSON keys documented in `skill/SKILL.md` and `checkpoint.py --help`.
- `register/_template/kinds/`: the game kind's section names and the `systems/*.json` field lists.
- The rules in `config/CLAUDE-snippet.md`. In that snippet, "me" means the user.

Ask the user before choosing:
- **Where the register lives.** The default is `~/claude-session-register/`. It can be its own private repo or a subfolder of an existing private docs repo. If it is not the default, they must export `CHECKPOINT_REGISTER` in their shell profile, and the allow paths in the settings snippet must change to match.
- **The private git remote** for the register. Never use a public repo; checkpoints hold internal decisions. Never create a remote repo without explicit approval.
- **The `Waiting on` label.** It defaults to the first word of `git config user.name`; `CHECKPOINT_OWNER` overrides it.
- **The wrap-up phrase list** in `hooks/checkpoint-wrapup-phrases.txt`. Any phrase on it triggers a full checkpoint, commit and push.

## Install procedure

1. **Inventory before touching anything.** Read `~/.claude/settings.json` and `~/.claude/CLAUDE.md`. List `~/.claude/skills/` and `~/.claude/hooks/`. Report to the user:
   - any existing `checkpoint` skill;
   - any existing `session-checkpoint-*` hooks;
   - their existing `SessionStart`, `UserPromptSubmit` and `SessionEnd` hooks.
2. **Check prerequisites**: `python3`, `git` and `pandoc`. If one is missing, tell the user; don't install it silently.
3. **Settle the choices above** with the user.
4. **Run `install.sh`**, setting `CHECKPOINT_REGISTER` if the path is not the default. It copies files, backs up anything it replaces and creates the symlinks. It does not edit `settings.json` or `CLAUDE.md`.
5. **Set up the register repo.** Run `git init` (unless it is inside an existing repo), add the user's private remote, commit, and push once with `-u` so the branch has an upstream. `checkpoint.py` refuses to push without one.
6. **Merge `config/settings-snippet.json`** into `~/.claude/settings.json`:
   - append to existing `hooks` arrays, never replace them;
   - append the allow rules, adjusting paths to the chosen register;
   - show the user the diff and get approval before writing;
   - validate that the result is JSON.
7. **Append `config/CLAUDE-snippet.md`** to `~/.claude/CLAUDE.md`. Show it first. Reconcile any conflicting rules the user already has; don't duplicate them.
8. **Verify without touching the real register.**
   - Copy `register/_template/` and `register/README.md` into a scratch folder.
   - Run `python3 <copy>/_template/checkpoint.py new test-topic "test"`.
   - Then run `echo '{"now":["Test state."],"next":"Test step.","glance":{"Status":"testing"},"add":{"Decisions":["Test decision."]}}' | python3 <copy>/_template/checkpoint.py patch test-topic - --finish --out <scratch>/out --no-git`, and check it prints `PATCHED=` and `PUBLISH=yes`.
   - Run one bad patch (`echo '{"bogus":1}' | ...`) and check it refuses with "nothing was written".
   - Open the HTML it prints.
   - Pipe `{"transcript_path":"<fake.jsonl>"}` into the start hook, using a fake transcript containing `{"type":"custom-title","customTitle":"test-topic"}`, with `CHECKPOINT_REGISTER` pointed at the copy.
   - Report what you actually observed.
9. **Tell the user to restart Claude Code**, then `/rename <topic>` and `/checkpoint --new <topic>` in a real session.

## Constraints to carry over

- **No credentials, secrets, or restricted data in any checkpoint.** Pages publish to claude.ai. Ask the user what their organization does not allow there.
- Sessions on an API key or a cloud provider (Bedrock, Vertex) cannot publish artifacts. For those sessions, `/checkpoint` still writes, commits and pushes, then says the artifact is unavailable.
- `checkpoint.py finish` holds its push (`PUSH HELD`) when unrelated unpushed commits share the repo. Surface that to the user; never push those commits yourself.
- If something in the package doesn't fit their environment, say so and propose the change. Don't quietly rewrite the logic.
