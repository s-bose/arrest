import pytest

from arrest.__main__ import main

CaptureFixture = pytest.CaptureFixture


def test_invalid_arguments():
    with pytest.raises(SystemExit):
        main(["--xyz", "-a"])


# def test_help(capsys: CaptureFixture[str]):
#     with pytest.raises(SystemExit):
#         error_code = main(["--help"])
#         assert error_code == Exit.OK

#     output = capsys.readouterr().out
