# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

import pytest

import tests
from tests import debug, net
from tests.debug import runners, targets


@pytest.mark.skipif(
    not tests.uses_graalpy_debuggee(),
    reason="requires DEBUGPY_TEST_DEBUGGEE_PYTHON to point to a GraalPy launcher",
)
@pytest.mark.parametrize(
    "run",
    [
        runners.attach_connect["api"],
        runners.attach_connect["cli"],
    ],
)
def test_graalpy_debuggee_basic(pyfile, run):
    # Keep a focused GraalPy regression that proves the debugger can attach and run a
    # real debuggee under GraalPy. Without this test, the compat fixes above can regress
    # silently because the default suite mostly exercises CPython. The practical
    # alternative is broader attach test parametrization, but that is a larger CI cost
    # for the same smoke-coverage goal.
    @pyfile
    def code_to_debug():
        import debuggee
        from debuggee import backchannel

        debuggee.setup()
        backchannel.send("ok")
        assert backchannel.receive() == "continue"

    with debug.Session() as session:
        # Each parametrized attach variant needs its own listen port. Reusing the same
        # port makes the second case fail with an address-in-use error, which is fatal
        # noise unrelated to GraalPy support. The practical alternative is to split the
        # variants into separate tests so each process computes the port once.
        runners.attach_connect.port = net.get_test_server_port()
        backchannel = session.open_backchannel()

        with run(session, targets.Program(code_to_debug)):
            pass

        assert backchannel.receive() == "ok"
        backchannel.send("continue")
        session.wait_for_next_event("terminated")
        session.proceed()
