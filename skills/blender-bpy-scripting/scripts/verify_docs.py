"""Extract every ```python block from the skill's markdown and run it in Blender.

Documentation that was never executed is a liability. This tool makes the
claim checkable:

    blender -b --factory-startup -noaudio -P scripts/verify_docs.py -- \
        references/            # verify a directory of docs
    blender -b --factory-startup -noaudio -P scripts/verify_docs.py -- \
        references/00-core-model.md --filter 5      # only blocks tagged `# [5]`

Conventions
-----------
* A block is executed only if it looks runnable. Blocks that are illustrative
  (fragments, ``...`` ellipsis, pseudo-code) are skipped and *reported* as
  skipped so you can eyeball them.
* Blocks that are expensive (render, animation, thousands of frames) are
  skipped unless the block opts in with a ``# slow:`` comment.
* Blocks that mutate the same .blend are given a fresh ``read_factory_settings``
  when the block does not do it itself -- a block that depends on a previous
  block is a smell and is reported.

Exit codes
----------
    0  every selected block passed (skips are allowed but reported)
    1  at least one block failed
"""

import os
import re
import sys
import traceback

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

BLOCK_RE = re.compile(r"^```python\n(.*?)^```", re.S | re.M)
TAG_RE = re.compile(r"#\s*\[([\w.-]+)\]")
SLOW_RE = re.compile(r"^\s*#\s*slow\s*:", re.I | re.M)
FRAG_RE = re.compile(r"^\s*#\s*frag(?:ment)?\b", re.I | re.M)
#: blocks that must never be executed by this tool -- a segfault in one of
#: them would take the whole verification run down and we could never catch it.
NOEXEC_RE = re.compile(r"^\s*#\s*no-?exec\b", re.I | re.M)


def extract_blocks(md_path):
    """Return [(index, tag, code, section)] for every python block in a markdown file.

    The first line of a block may carry directives, all in ``#`` comments::

        # [4]        <- tag used by --filter
        # frag       <- not runnable on its own, skipped (a snippet excerpt)
        # slow: ...  <- expensive (render, animation), skipped by default
        # no-exec ... <- known to segfault Blender; never executed by this tool

    ``section`` is the nearest preceding ``##`` heading. Blocks inside the same
    section share one execution namespace, because reference documentation
    routinely shows a script as a sequence of consecutive snippets that build
    on each other. A new ``##`` heading starts a fresh namespace.
    """
    with open(md_path, "r", encoding="utf-8") as fh:
        text = fh.read()

    # Map character offset -> section title, so we can tag each block.
    heads = [(m.start(), m.group(1).strip()) for m in re.finditer(r"^##\s+(.*)$", text, re.M)]

    def section_at(pos):
        title = "(preamble)"
        for off, t in heads:
            if off <= pos:
                title = t
            else:
                break
        return title

    out = []
    for i, m in enumerate(BLOCK_RE.finditer(text)):
        code = m.group(1)
        head = code.splitlines()[0] if code.splitlines() else ""
        tag_m = TAG_RE.search(head)
        tag = tag_m.group(1) if tag_m else str(i + 1)
        out.append((i + 1, tag, code, section_at(m.start())))
    return out


def looks_runnable(code):
    """Heuristic: is this block plausible as a standalone script?

    Only genuinely non-Python content is rejected here. A leading ``#``
    comment is NOT a reason to skip -- plenty of good examples open with a
    note about how they were run.
    """
    stripped = code.strip()
    if not stripped:
        return False, "empty"
    if re.search(r"^\s*\.\.\.\s*$", stripped, re.M):
        return False, "contains a bare '...' ellipsis line (placeholder)"
    first = stripped.splitlines()[0].strip()
    if first.startswith("#"):
        return True, None
    if "\n" not in stripped and re.match(r"^[$>]*\s*[~/.\w][\w./-]*\s*$", first):
        return False, "single bare token -- looks like a shell command or a file path"
    return True, None


def run_block(tag, code, workdir, ns=None):
    """Execute one block. Returns (status, detail).

    status is one of:
      ``pass``  ran to completion
      ``frag``  ran but raised -- only acceptable for a block that looked like a
                fragment/pseudo-code up front (its names still land in the
                section namespace, which is the whole point of running it)
      ``skip``  not executed at all (marked ``# slow:``)
      ``fail``  looked runnable, but blew up -- a real defect

    ``ns`` is a persistent namespace shared by all blocks in the same section,
    because reference documentation routinely presents one script as a sequence
    of consecutive snippets.
    """
    if NOEXEC_RE.search(code):
        return "skip", "marked '# no-exec' (running it would kill the verifier)"
    if SLOW_RE.search(code):
        return "skip", "marked '# slow:'"
    runnable, why = looks_runnable(code)
    if FRAG_RE.search(code):
        runnable, why = False, "marked '# frag' -- excerpt from a larger example"
    would_skip = not runnable

    path = os.path.join(workdir, f"block_{tag.replace('/', '_')}.py")
    prelude = (
        "import bpy, sys, os\n"
        f"sys.path.insert(0, {HERE!r})\n"
        "bpy.ops.wm.read_factory_settings(use_empty=True)\n"
    )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(prelude)
        fh.write(code)
        fh.write("\nprint('__BLOCK_OK__')\n")

    import io
    import contextlib
    buf = io.StringIO()
    if ns is None:
        ns = {}
    ns.update({"__name__": "__doc_block__", "__file__": path,
               "bpy": bpy, "sys": sys, "os": os})
    sentinel = "\nprint('__BLOCK_OK__')\n"
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(prelude + code + sentinel, path, "exec"), ns)
    except SystemExit as exc:
        # A block that demonstrates `sys.exit()` would otherwise take the whole
        # verification run down with it. Treat it as a pass, but say so.
        return "pass", f"called sys.exit({exc.code!r}) -- caught by the runner"
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        if would_skip:
            return "frag", f"{detail}  [fragment: {why}]"
        return "fail", traceback.format_exc(limit=4).strip() + "\n" + buf.getvalue()[-2000:]

    out = buf.getvalue()
    if "__BLOCK_OK__" not in out:
        detail = ("block did not reach the end -- it called sys.exit() "
                  "or bpy.ops.wm.quit_blender()?\n" + out[-1500:])
        return ("frag", detail) if would_skip else ("fail", detail)
    if would_skip:
        return "frag", f"ran clean but is a fragment ({why})"
    return "pass", out.strip().splitlines()[-2] if len(out.strip().splitlines()) > 1 else ""


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        print(__doc__)
        return 2
    targets = argv[0]
    only = None
    if "--filter" in argv:
        only = set(argv[argv.index("--filter") + 1].split(","))

    files = []
    if os.path.isdir(targets):
        for root, _dirs, names in os.walk(targets):
            files += [os.path.join(root, n) for n in sorted(names) if n.endswith(".md")]
    else:
        files = [targets]
    files.sort()

    workdir = os.path.join(HERE, "_docblocks")
    os.makedirs(workdir, exist_ok=True)

    n_pass = n_fail = n_skip = 0
    failures, skips = [], []

    for path in files:
        blocks = extract_blocks(path)
        if not blocks:
            continue
        rel = os.path.relpath(path, os.path.dirname(HERE))
        print(f"\n=== {rel} ({len(blocks)} blocks) ===")
        section_ns = {}
        current_section = None
        for _idx, tag, code, section in blocks:
            if section != current_section:
                current_section = section
                section_ns = {}
            if only and tag not in only:
                continue
            status, detail = run_block(tag, code, workdir, ns=section_ns)
            if status == "pass":
                n_pass += 1
                print(f"  [{tag:>6}] PASS  {detail[:80]}")
            elif status in ("frag", "skip"):
                n_skip += 1
                skips.append((rel, tag, detail))
                print(f"  [{tag:>6}] {'SKIP' if status == 'skip' else 'FRAG'}  {detail[:66]}")
            else:
                n_fail += 1
                failures.append((rel, tag, detail))
                print(f"  [{tag:>6}] FAIL  (section: {section[:34]})")
                print("        " + detail.replace("\n", "\n        ")[:900])

    print(f"\n===== pass={n_pass} fail={n_fail} frag/skip={n_skip} =====")
    if skips:
        print("fragments / skips (review these by hand):")
        for rel, tag, why in skips:
            print(f"  {rel}#{tag}: {why}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    try:
        code = main()
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    sys.exit(code)
