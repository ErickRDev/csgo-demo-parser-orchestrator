import configparser
import os
import patoolib
import subprocess

from copy import deepcopy
from pathlib import Path
from optparse import OptionParser
from sys import exit
from time import time

OUTPUT_DIR_PATH = None
PARSER_PATH = None


def invoke_parser(fp: Path):
    """
    Invokes parsing routine to parse supplied file.
    """
    res = subprocess.run(
        args=["node", PARSER_PATH, "--demo", str(fp.absolute()), "--verboseness", "-1"]
    )

    return res.returncode == 0


def extract_demos_from_archive(compressed_fp: Path, target_dir: str):
    """
    Extracts demo files from archive.
    """
    patoolib.extract_archive(
        str(compressed_fp.absolute()), verbosity=-1, outdir=target_dir
    )

    return Path(target_dir).glob("*.dem")


def process_archive(fp: Path):
    """
    Processes an archive, extracting its demo files
    and invoking the parsing routine for each.
    """
    if len(fp.name.split(".")) == 1:
        # NOTE: file has no extension:
        # adding .rar extension for two reasons:
        # 1. so that we can create a directory with the same "stem" of the file
        # 2. so that patool can properly identify the archive file type
        fp = fp.rename(fp.with_suffix(".rar"))

    # TODO: make this directory creation configurable
    # so that we can have saner names in the directory
    # hierarchy.
    target_dir = os.path.join(OUTPUT_DIR_PATH, fp.stem)
    try:
        os.mkdir(target_dir)
    except FileExistsError as e:
        print("File already processed, skipping")
        return

    print(f"Extracting demo files from archive: {fp.name}")
    extracted_files = extract_demos_from_archive(fp, target_dir)

    for f in extracted_files:
        t = time()
        print(f"Parsing demo file: {f.name}")
        if not invoke_parser(Path(f)):
            print("ERROR :: failed to parse file, skipping to next archive")
            return
        os.remove(f)
        print(f"...done; {time() - t:.2f}s elapsed")


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("config.ini")

    PARSER_PATH = config["parser"]["path"]
    if not PARSER_PATH or not os.path.isfile(PARSER_PATH):
        # TODO: also verify whether node is installed
        print("Invalid configurations: expected parser path")
        exit()

    parser = OptionParser()

    parser.add_option(
        "-f",
        "--file",
        dest="f",
        help="extract demo files from FILE and invokes the parser for each",
        metavar="FILE",
    )

    parser.add_option(
        "-d",
        "--directory",
        dest="d",
        help="for each compressed file in DIR extract demo files and invokes the parser for each",
        metavar="DIR",
    )

    opts, _ = parser.parse_args()

    if not opts.f and not opts.d:
        print("Invalid arguments: supply either -d or -f")
        exit()

    print("Started")
    t = time()

    # NOTE: directory processing takes precedence
    # over single file processing
    if opts.d:
        print(f"Processing directory: {opts.d}")

        if not os.path.isdir(opts.d):
            print("The supplied directory does not exist")
            exit()

        OUTPUT_DIR_PATH = opts.d
        for f in Path(opts.d).glob("*"):
            if f.is_dir():
                continue

            name_tokens = f.name.split(".")

            if len(name_tokens) == 2 and name_tokens[1] == "json":
                # skipping JSON files that might be
                # bundled together with the downloaded files
                # i.e. manifest & progress files
                continue

            process_archive(f)
    else:
        print(f"Processing file: {opts.f}")

        if not os.path.isfile(opts.f):
            print("The supplied file does not exist")
            exit()

        fp = Path(opts.f)
        OUTPUT_DIR_PATH = str(fp.parent)
        process_archive(fp)

    print(f"Ended; {time() - t:.2f}s elapsed")
