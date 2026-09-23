# 0001. Python for the build tool

## Status

Accepted.

## Context

This repository replaces the image pipelines in two older repositories.
`strabs-iac` builds images with Python, uv and typer, and tests the image
path — the step order, the argv lists, the checksum guard — in 19 pytest
files. `dulliac` builds images with TypeScript on bun and has no tests for
the image path. Both keep their Pulumi programs, and no Pulumi program moves
here, so the language choice decides one thing: which test suite ports, and
which we write again from nothing.

## Decision

We write the build tool in Python, with uv for the environment, typer for the
command line, and pytest for the tests.

We reject TypeScript on bun. Bun's advantage is a fast Pulumi program, and
this repository runs none. Choosing bun would also discard the 19 test files,
because no automatic port exists from pytest to a bun test runner.

## Consequences

The strabs-iac tests port, so the test suite starts large.

Python and TypeScript now split the wider estate. `dulliac` stays TypeScript
for its Pulumi code, so a person who works on both must read two languages.

The tool needs a Python interpreter at build time. `devenv.nix` pins one, so
a build does not depend on the host interpreter.

Python starts more slowly than bun, but a build spends minutes inside
`virt-customize`, so the start time does not matter.
