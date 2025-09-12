import os
import re
import time
import types


class Timer:
    """
    Provides a simple timer that reports the time between being started and stopped.

    >>> t = Timer()
    >>> squares = [x * x for x in range(10**6)]
    >>> t.stop()
    Elapsed time: 0.031 seconds
    """

    all_timers = []
    enable_printing_default = True
    decimal_places_default = 3

    def __init__(
        self,
        start=True,
        output_string="Elapsed time:",
        enable_printing=None,
        decimal_places=None,
        output_function=print,
    ):
        self._start_time = None
        self._stop_time = None
        self.last_timing = None
        self.output = output_function  # e.g. `print` or `logger.info`

        self.output_string = output_string

        if enable_printing is None:
            self.enable_printing = self.enable_printing_default
        else:
            self.enable_printing = enable_printing
        if decimal_places is None:
            decimal_places = self.decimal_places_default
        self.format_string = "{:." + str(decimal_places) + "f} seconds"

        self.all_timers.append(self)

        if start:
            self.start()

    def start(self):
        """Starts the timer"""
        self._start_time = time.perf_counter()

    def stop(self):
        """Stops the timer and returns the elapsed time in seconds"""
        self._stop_time = time.perf_counter()
        if self.start is None:
            raise RuntimeError("Timer was stopped before it was started")
        self.last_timing = self._stop_time - self._start_time  # type: ignore
        if self.enable_printing:
            self.output(
                self.output_string + " " + self.format_string.format(self.last_timing)
            )
        return self.last_timing


def pluralize(value, unit):
    """
    >>> pluralize(2, "minute")
    "minutes"
    >>> pluralize(1, "second")
    "second"
    """
    if value == 1:
        return unit
    else:
        return unit + "s"


def label(value, unit):
    """
    >>> label(2, "minute")
    "2 minutes"
    >>> label(1, "second")
    "1 second"
    """
    if value == 1:
        return f"{value} {unit}"
    else:
        return f"{value} {unit}s"


def strip_ansi(text):
    """
    Remove ANSI escape codes from text
    """
    # Regular expression to match ANSI escape codes
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def human_duration(seconds):
    """
    Display a duration in seconds in a human readable format

    >>> human_duration(98765432.1)
    "3 years 48 days 2 hours 50 minutes 32.1 seconds"
    """
    # Constants
    SECONDS_PER_MINUTE = 60
    SECONDS_PER_HOUR = 60 * SECONDS_PER_MINUTE
    SECONDS_PER_DAY = 24 * SECONDS_PER_HOUR
    SECONDS_PER_YEAR = 365 * SECONDS_PER_DAY

    # Calculate each time unit
    years = int(seconds // SECONDS_PER_YEAR)
    seconds %= SECONDS_PER_YEAR

    days = int(seconds // SECONDS_PER_DAY)
    seconds %= SECONDS_PER_DAY

    hours = int(seconds // SECONDS_PER_HOUR)
    seconds %= SECONDS_PER_HOUR

    minutes = int(seconds // SECONDS_PER_MINUTE)
    seconds %= SECONDS_PER_MINUTE

    # Create a human-readable string
    result = []
    if years > 0:
        result.append(label(years, "year"))
    if days > 0:
        result.append(label(days, "day"))
    if hours > 0:
        result.append(label(hours, "hour"))
    if minutes > 0:
        result.append(label(minutes, "minute"))
    if seconds > 0 or not result:
        result.append(
            f"{seconds:.2f}".rstrip("0").rstrip(".")  # show at most two decimals
            + " "
            + pluralize(seconds, "second")
        )
    return " ".join(result)


def file_or_dir_name(path):
    """
    Given a path, get the file name without extension if it is a file, and otherwise the name of the directory

    >>> file_or_dir_name("test/dir/file.ext")
    "file"
    >>> file_or_dir_name("test/dir/")
    "dir"
    >>> file_or_dir_name("test/dir/file.multiple.ext")
    "file.multiple"
    """
    basename, _ = os.path.splitext(os.path.basename(path))
    if basename == "":
        basename = os.path.basename(os.path.split(path)[0])
        assert basename != ""
    return basename


def set_extension(path, extension):
    """
    >>> set_extension("path/file.ext", "new")
    "path/file.new"
    >>> set_extension("path/file", "ext")
    "path/file.ext"
    >>> set_extension("path/file.multi.ext", "new")
    "path/file.multi.new"
    """
    path, _ = os.path.splitext(path)
    return path + "." + extension


def get_extension(path):
    """
    >>> get_extension("path/file.ext")
    "ext"
    >>> get_extension("path/file.multi.ext")
    "ext"
    >>> get_extension("path/file")
    ""
    """
    _, ext = os.path.splitext(path)
    if ext.startswith("."):
        ext = ext[1:]
    return ext


if __name__ == "__main__":
    # Get all global symbols
    global_symbols = globals()

    # Filter out the functions
    functions_and_classes = [
        (name, obj)
        for name, obj in global_symbols.items()
        if isinstance(obj, (types.FunctionType, type))
    ]
    print("This file provides the following handy helpers:\n")
    for name, obj in functions_and_classes:
        print(name)
        print(obj.__doc__)
