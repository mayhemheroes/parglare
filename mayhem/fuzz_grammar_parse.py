#!/usr/bin/env python3
"""fuzz_grammar_parse.py — Atheris harness for parglare (igordejanovic/parglare).

The fuzzer feeds two random strings per input: the first is treated as a parglare
GRAMMAR (compiled via Grammar.from_string), the second as INPUT parsed by an LALR
Parser built from that grammar. This exercises the grammar compiler, table builder,
the recognizer/regex layer and the LR parse loop.

Expected, well-defined failures for arbitrary/garbage input (a malformed grammar, an
unparseable input, an ambiguous grammar with LR conflicts, a regex terminal that
won't compile, or a CPython recursion-limit hit on a pathologically deep grammar)
are caught and ignored — they are NOT defects. Anything else propagates so Atheris
reports it as a genuine crash.

NB: the upstream `mayhem` integration originally caught `parglare.exceptions.LocationError`,
which does not exist in parglare — referencing it in the `except` clause raised
AttributeError on the very first input that errored, so the harness could not fuzz.
This catches the real parglare exception hierarchy instead.
"""
import sys
import re as _re

import atheris

import fuzz_helpers

with atheris.instrument_imports(include=['parglare']):
    import parglare
    from parglare import exceptions as pg_exc

# Errors that are a normal outcome of feeding arbitrary text as a grammar/input — not bugs.
# ParglareError is the base of GrammarError / SyntaxError / DisambiguationError; the rest are
# separate Exception subclasses raised by table construction / parser init / regex compile.
EXPECTED = (
    pg_exc.ParglareError,        # GrammarError, SyntaxError, DisambiguationError, ...
    pg_exc.ParserInitError,
    pg_exc.LoopError,
    pg_exc.LRConflicts,          # SRConflicts / RRConflicts (ambiguous grammar)
    pg_exc.DynamicDisambiguationConflict,
    _re.error,                   # a terminal's regex failed to compile
    RecursionError,              # CPython recursion limit on a pathologically deep grammar/input
)


def TestOneInput(data):
    fdp = fuzz_helpers.EnhancedFuzzedDataProvider(data)
    grammar_str = fdp.ConsumeRandomString()
    input_str = fdp.ConsumeRemainingString()
    # Skip the degenerate EMPTY string. parglare's error formatter
    # (exceptions.get_line_col_at_position) does `lines[-1]` on `"".splitlines()` (== []),
    # so reporting a parse error against an empty text raises IndexError from inside its OWN
    # SyntaxError constructor — a shallow error-path bug that fires on the very first
    # (zero-length) libFuzzer input and would block all fuzzing. Skipping the empty string
    # lets the fuzzer explore the actual grammar compiler / LR parse logic, where genuine
    # exceptions still surface uncaught.
    if not grammar_str or not input_str:
        return -1
    try:
        grammar = parglare.Grammar.from_string(grammar_str)
        parser = parglare.Parser(grammar)
        parser.parse(input_str)
    except EXPECTED:
        return -1


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
