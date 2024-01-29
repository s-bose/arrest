import io

import pytest

from arrest.__main__ import Exit, arg_parser, main
from arrest.exceptions import ArrestError

CaptureFixture = pytest.CaptureFixture

help_str = io.StringIO()
arg_parser.print_help(help_str)


def test_invalid_arguments(capsys: CaptureFixture[str]):
    return_code = main(["--xyz", "-a"])
    assert return_code == Exit.ERROR

    output = capsys.readouterr().out
    assert help_str.getvalue() in output


def test_noargs(capsys: CaptureFixture[str]):
    return_code = main([])
    assert return_code == Exit.ERROR

    output = capsys.readouterr().out
    assert help_str.getvalue() in output


def test_help(capsys: CaptureFixture[str]):
    with pytest.raises(SystemExit):
        return_code = main(["--help"])
        assert return_code == Exit.OK

    output = capsys.readouterr().out
    help_message = io.StringIO()
    arg_parser.print_help(help_message)

    assert output == help_message.getvalue()


def test_missing_url(capsys: CaptureFixture[str]):
    return_code = main(["-o", "abc"])
    assert return_code == Exit.ERROR

    output = capsys.readouterr().out
    assert "Missing `--url`" in output


def test_output(capsys: CaptureFixture[str], mocker):
    mocker.patch("arrest.openapi.OpenAPIGenerator.generate_schema", return_value=None)

    return_value = main(["--url", "tests/fixtures/openapi_petstore.json"])

    assert return_value == Exit.OK
    output = capsys.readouterr().out
    assert "No output path specified. Using current directory" in output
    assert "Files generated successfully" in output


def test_exception(capsys: CaptureFixture[str], mocker):
    mocker.patch(
        "arrest.openapi.OpenAPIGenerator.generate_schema", side_effect=ArrestError("something went wrong")
    )

    return_value = main(["--url", "tests/fixtures/openapi_petstore.json"])
    assert return_value == Exit.ERROR
    err = capsys.readouterr().err

    assert "arrest.exceptions.ArrestError: something went wrong" in err
