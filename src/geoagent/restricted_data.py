"""Graceful handling of datasets that are not redistributed with the public repository.

The 300-block human reference set and the block-level historical OpenStreetMap features are kept out of the
public repository (see docs/data-availability.md). The tools that read them stay registered, so the tool list
is the same everywhere; when the file is absent a tool returns a structured, bilingual "dataset not available"
answer instead of raising. Nothing here creates, edits or fabricates data.
"""
import functools
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def path(env_var, *default_parts):
    """Location of a restricted file: the environment variable if set, otherwise the default path in the repo."""
    return os.environ.get(env_var) or os.path.join(ROOT, *default_parts)


def guard(fn, dataset, env_var, default_rel):
    """Wrap a read-only tool so that a missing restricted file yields an explanatory result."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except FileNotFoundError:
            return {
                "found": False,
                "available": False,
                "dataset": dataset,
                "error": ("The %s is not distributed with the public repository. Place the file at %s or set the "
                          "environment variable %s to its location. See docs/data-availability.md."
                          % (dataset, default_rel, env_var)),
                "error_ar": ("مجموعة البيانات (%s) غير موزَّعة مع المستودع العام. ضع الملف في %s أو عيّن متغيّر البيئة %s. "
                             "راجع docs/data-availability.md." % (dataset, default_rel, env_var)),
            }
    return wrapper
