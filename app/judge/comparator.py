def normalize_output(text: str) -> str:
    """
    normalize line endings and trailing whitespace for comparison
    """

    # convert windows and old mac line endings into one format
    normalized = text.replace("\r\n", "\n").replace(
        "\r",
        "\n",
    )

    # remove spaces and tabs only from the end of each line
    lines = [
        line.rstrip(" \t")
        for line in normalized.split("\n")
    ]

    # ignore additional empty lines after the final answer line
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def compare_output(
    actual_output: str,
    expected_output: str,
) -> bool:
    """
    compare actual and expected output after normalization
    """

    return normalize_output(actual_output) == normalize_output(
        expected_output
    )
