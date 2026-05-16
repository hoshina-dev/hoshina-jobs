import contextlib
import io
import os
import sys
import traceback
import base64

STDOUT_PATH = "/tmp/py_stdout"
STDERR_PATH = "/tmp/py_stderr"


def write_file(path: str, data: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(data)


def run_code(code: str) -> int:
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    exit_code = 0

    globals_dict = {"__name__": "__main__"}

    with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
        try:
            exec(code, globals_dict)
        except SystemExit as exc:
            exit_code = exc.code if isinstance(exc.code, int) else 1
            if exc.code not in (0, None, ""):
                print(exc.code, file=sys.stderr)
        except Exception:
            traceback.print_exc()
            exit_code = 1

    stdout_value = stdout_buffer.getvalue()
    stderr_value = stderr_buffer.getvalue()

    write_file(STDOUT_PATH, stdout_value)
    write_file(STDERR_PATH, stderr_value)

    if stdout_value:
        sys.stdout.write(stdout_value)
    if stderr_value:
        sys.stderr.write(stderr_value)

    return exit_code


def decode_code() -> str:
    encoded = os.getenv("PY_CODE_B64", "")
    if not encoded:
        message = "PY_CODE_B64 environment variable is required\n"
        sys.stderr.write(message)
        write_file(STDOUT_PATH, "")
        write_file(STDERR_PATH, message)
        return ""

    try:
        return base64.b64decode(encoded, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        message = f"Invalid PY_CODE_B64: {exc}\n"
        sys.stderr.write(message)
        write_file(STDOUT_PATH, "")
        write_file(STDERR_PATH, message)
        return ""


def main() -> int:
    code = decode_code()
    if not code:
        return 1

    return run_code(code)


if __name__ == "__main__":
    sys.exit(main())

