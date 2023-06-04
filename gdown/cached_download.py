from __future__ import print_function

import hashlib
import os
import os.path as osp
import shutil
import sys
import tempfile

import filelock

from .download import download

cache_root = osp.join(osp.expanduser("~"), ".cache/gdown")
if not osp.exists(cache_root):
    try:
        os.makedirs(cache_root)
    except OSError:
        pass


def md5sum(filename, blocksize=None):
    if blocksize is None:
        blocksize = 65536

    hash = hashlib.md5()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            hash.update(block)
    return hash.hexdigest()


def assert_md5sum(filename, md5, quiet=False, blocksize=None):
    if not (isinstance(md5, str) and len(md5) == 32):
        raise ValueError(f"MD5 must be 32 chars: {md5}")

    if not quiet:
        print(f"Computing MD5: {filename}")
    md5_actual = md5sum(filename)

    if md5_actual == md5:
        if not quiet:
            print(f"MD5 matches: {filename}")
        return True

    raise AssertionError(
        f"MD5 doesn't match:\nactual: {md5_actual}\nexpected: {md5}"
    )


def cached_download(
    url=None, path=None, md5=None, quiet=False, postprocess=None, **kwargs
):
    """Cached download from URL.

    Parameters
    ----------
    url: str
        URL. Google Drive URL is also supported.
    path: str, optional
        Output filename. Default is basename of URL.
    md5: str, optional
        Expected MD5 for specified file.
    quiet: bool
        Suppress terminal output. Default is False.
    postprocess: callable
        Function called with filename as postprocess.
    kwargs: dict
        Keyword arguments to be passed to `download`.

    Returns
    -------
    path: str
        Output filename.
    """
    if path is None:
        path = (
            url.replace("/", "-SLASH-")
            .replace(":", "-COLON-")
            .replace("=", "-EQUAL-")
            .replace("?", "-QUESTION-")
        )
        path = osp.join(cache_root, path)

    # check existence
    if osp.exists(path):
        if not md5:
            if not quiet:
                print(f"File exists: {path}")
            return path
        else:
            try:
                assert_md5sum(path, md5, quiet=quiet)
                return path
            except AssertionError as e:
                # show warning and overwrite if md5 doesn't match
                print(e, file=sys.stderr)

    # download
    lock_path = osp.join(cache_root, "_dl_lock")
    try:
        os.makedirs(osp.dirname(path))
    except OSError:
        pass
    temp_root = tempfile.mkdtemp(dir=cache_root)
    try:
        temp_path = osp.join(temp_root, "dl")

        if not quiet:
            msg = "Cached Downloading"
            msg = f"{msg}: {path}" if path else f"{msg}..."
            print(msg, file=sys.stderr)

        download(url, temp_path, quiet=quiet, **kwargs)
        with filelock.FileLock(lock_path):
            shutil.move(temp_path, path)
    except Exception:
        shutil.rmtree(temp_root)
        raise

    if md5:
        assert_md5sum(path, md5, quiet=quiet)

    # postprocess
    if postprocess is not None:
        postprocess(path)

    return path
