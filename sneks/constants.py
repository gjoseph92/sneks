COILED_ACCOUNT_NAME = "gjoseph92"
DOCKER_USERNAME = "jabriel"
PROJECT_NAME = "sneks"
SUFFIX = "-full-xarch"
REQUIRED_PACKAGES = frozenset(
    ["dask", "distributed", "bokeh", "cloudpickle", "msgpack"]
)
# Most transitive dependencies of the required packages, so we don't have to re-install
# them with different versions according to the lockfile.
# Also include things we may want on the scheduler (`dask-pyspy`).
OPTIONAL_PACKAGES = frozenset(
    [
        "MarkupSafe",
        "click",
        "dask-pyspy",
        "fsspec",
        "heapdict",
        "jinja2",
        "locket",
        "lz4",
        "numpy",
        "packaging",
        "pandas",
        "partd",
        "psutil",
        "pyarrow",
        "pyparsing",
        "pyyaml",
        "s3fs",
        "sortedcontainers",
        "tblib",
        "toolz",
        "tornado",
        "urllib3",
        "zict",
    ]
)

if __name__ == "__main__":
    # Print constants as environment variables.
    # We can then read them into GitHub Actions with `python sneks/constants.py >> "$GITHUB_ENV"`

    for k, v in list(locals().items()):
        if k.isupper() and isinstance(v, str):
            print(f"{k}={v}")
