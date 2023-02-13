#!/usr/bin/env python3
import random

import atheris
import sys
import fuzz_helpers
import random

with atheris.instrument_imports(include=['parglare']):
    import parglare

def TestOneInput(data):
    fdp = fuzz_helpers.EnhancedFuzzedDataProvider(data)
    try:
        grammar = parglare.Grammar.from_string(fdp.ConsumeRandomString())
        parser = parglare.Parser(grammar)
        parser.parse(fdp.ConsumeRandomString())
    except parglare.exceptions.LocationError:
        return -1


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
