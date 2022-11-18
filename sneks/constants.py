COILED_ACCOUNT_NAME = "gjoseph92"
DOCKER_USERNAME = "jabriel"
PROJECT_NAME = "sneks"
SUFFIX = "-full-xarch"
REQUIRED_PACKAGES = frozenset(
    ["dask", "distributed", "bokeh", "cloudpickle", "msgpack"]
)
OPTIONAL_PACKAGES = frozenset(["numpy", "pandas", "s3fs", "pyarrow, dask-pyspy"])


if __name__ == "__main__":
    # Print constants as environment variables.
    # We can then read them into GitHub Actions with `python sneks/constants.py >> "$GITHUB_ENV"`

    for k, v in list(locals().items()):
        if k.isupper() and isinstance(v, str):
            print(f"{k}={v}")
