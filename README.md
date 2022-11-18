# sneks

Get your snakes in a row.

`sneks` lets you launch a [Dask cluster in the cloud](https://coiled.io/), matched to your local software environment\*, in a single line of code. No more dependency mismatches or Docker image building.

```python
from sneks import get_client

client = get_client()
```

\*your local [Poetry](https://python-poetry.org/) or [PDM](https://pdm.fming.dev/latest/) environment. You must use poetry or PDM. Locking package managers are what sensible people use, and you are sensible.

*Neat! Sneks also supports ARM clusters! Just pass ARM instances in `scheduler_instace_types=`, `worker_instace_types=` and cross your fingers that all your dependencies have cross-arch wheels!*

## Installation

```shell
poetry add -G dev sneks-sync
```

## A full example:

```shell
mkdir example && cd example
poetry init -n
poetry add -G dev sneks-sync
poetry add distributed==2022.5.2 dask==2022.5.2 bokeh pandas pyarrow  # and whatever else you want
```
```python
from sneks import get_client
import dask.dataframe as dd

client = get_client(name="on-a-plane")
ddf = dd.read_parquet(
    "s3://nyc-tlc/trip data/yellow_tripdata_2012-*.parquet",
)
print(ddf.groupby('passenger_count').trip_distance.mean().compute())
```

Oh wait, we forgot to install a dependency!
```shell
poetry add foobar
```

When we reconnect to the cluster (using the same name), the dependencies on the cluster update automatically.
```python
from sneks import get_client
import dask.dataframe as dd
import foobar  # ah, how could we forget this critical tool

client = get_client(name="on-a-plane")
ddf = dd.read_csv(
    "s3://nyc-tlc/csv_backup/yellow_tripdata_2012-*.csv",
)
means = ddf.groupby('passenger_count').trip_distance.mean()
means.apply(foobar.optimize).compute()

```

## Caveats

This is still a proof-of-concept-level package. It's been used personally quite a bit, and proven reliable, but use at your own risk.