#!/usr/bin/python3
"""run_tests.py — behavioral known-answer test (KAT) oracle for parglare.

Invoked via the `/mayhem/pglr-tests` ELF launcher (NOT directly), so the verify-repo
sabotage oracle can neuter the launcher and prove the test oracle is behavioral
(LD_PRELOAD _exit(0) kills the non-system launcher before python runs → no RUNTESTS
line → mayhem/test.sh fails).

These are EXACT-VALUE assertions, not "did it import / exit 0": a calculator grammar
with semantic actions is parsed and its computed result is checked to the value, LR
operator precedence/associativity is exercised, and invalid input is required to raise
parglare's SyntaxError. A no-op / behaviour-altering patch to parglare's grammar
compiler, table builder or parse loop cannot pass it.

Prints exactly one machine-readable line:

    RUNTESTS tests=<n> passed=<p> failed=<f> skipped=<s>

Exit 0 iff failed == 0. mayhem/test.sh parses that line into a CTRF report.
"""
from __future__ import annotations

import sys
import traceback

from parglare import Grammar, Parser
from parglare.actions import pass_inner, pass_single
from parglare.exceptions import SyntaxError as PGSyntaxError

# A precedence/associativity-bearing calculator grammar with semantic actions
# (lifted from parglare's own examples/calc) — evaluating it end-to-end exercises the
# grammar compiler, LALR table construction, the recognizer and the reduce actions.
CALC_GRAMMAR = r"""
Calc: Assignments E;
Assignments: Assignment | Assignments Assignment | EMPTY;
Assignment: VariableName "=" Number;

E: E "+" E {left, 1}
 | E "-" E {left, 1}
 | E "*" E {left, 2}
 | E "/" E {left, 2}
 | "(" E ")"
 | VariableRef
 | Number
;

VariableRef: VariableName;

terminals
VariableName: /[a-zA-Z_][_a-zA-Z0-9]*/;
Number: /\d+(\.\d+)?/;
"""


def _act_assignment(context, nodes):
    name, _, number = nodes[0], nodes[1], nodes[2]
    if context.extra is None:
        context.extra = {}
    context.extra[name] = number


CALC_ACTIONS = {
    "Calc": lambda _, nodes: nodes[1],
    "Assignment": _act_assignment,
    "E": [
        lambda _, nodes: nodes[0] + nodes[2],
        lambda _, nodes: nodes[0] - nodes[2],
        lambda _, nodes: nodes[0] * nodes[2],
        lambda _, nodes: nodes[0] / nodes[2],
        pass_inner,
        pass_single,
        pass_single,
    ],
    "Number": lambda _, value: float(value),
    "VariableRef": lambda context, nodes: context.extra[nodes[0]],
}


def _calc(expr):
    g = Grammar.from_string(CALC_GRAMMAR)
    parser = Parser(g, actions=CALC_ACTIONS)
    return parser.parse(expr)


# --- known-answer cases ---------------------------------------------------------------

def t_precedence():
    # '*' binds tighter than '+': 2 + 3 * 4 == 14, not 20.
    assert _calc("2 + 3 * 4") == 14.0, _calc("2 + 3 * 4")


def t_left_assoc():
    # '-' is left associative: 10 - 3 - 2 == 5, not 9.
    assert _calc("10 - 3 - 2") == 5.0, _calc("10 - 3 - 2")


def t_parens():
    assert _calc("(2 + 3) * 4") == 20.0, _calc("(2 + 3) * 4")


def t_variables():
    assert _calc("a = 5 b = 7 a * b + 1") == 36.0, _calc("a = 5 b = 7 a * b + 1")


def t_simple_sequence():
    # An explicit token-sequence grammar: the parser must enforce the grammar exactly.
    g = Grammar.from_string("S: 'a' 'b' 'c';")
    p = Parser(g)
    assert p.parse("a b c") is not None


def t_syntax_error_raised():
    # An input that violates the grammar MUST raise parglare's SyntaxError, not pass.
    g = Grammar.from_string("S: 'a' 'b' 'c';")
    p = Parser(g)
    try:
        p.parse("a b")
    except PGSyntaxError:
        return
    raise AssertionError("expected SyntaxError for 'a b' against \"S: 'a' 'b' 'c';\"")


TESTS = [
    t_precedence,
    t_left_assoc,
    t_parens,
    t_variables,
    t_simple_sequence,
    t_syntax_error_raised,
]


def main() -> int:
    passed = failed = 0
    for t in TESTS:
        try:
            t()
            passed += 1
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    total = passed + failed
    print(f"RUNTESTS tests={total} passed={passed} failed={failed} skipped=0")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
