# KleptoSyn

Synthetic data generation for investigative graphs based on patterns
of bad-actor tradecraft.

Default input data sources:

  * <https://www.opensanctions.org/>
  * <https://www.openownership.org/>
  * <https://www.occrp.org/en/project/the-azerbaijani-laundromat/the-raw-data>

Ontologies used:

  * <https://followthemoney.tech/>


## Build an environment

Based on using Python 3.11+

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -U pip wheel
python3 -m pip install -r requirements.txt
```

This project uses [pre-commit hooks](https://pre-commit.com/) for code
linting, etc.

You will also need the CLI for Google Cloud to get the default input
datasets:
<https://cloud.google.com/storage/docs/discover-object-storage-gcloud>


## Load the default data

```bash
gcloud storage cp gs://erkg/starterkit/open-sanctions.json .
gcloud storage cp gs://erkg/starterkit/open-ownership.json .
gcloud storage cp gs://erkg/starterkit/export.json .

wget https://raw.githubusercontent.com/cj2001/senzing_occrp_mapping_demo/refs/heads/main/occrp_17k.csv
```

## Run the demo script

```bash
./demo.py
```


## Run the notebooks

```bash
./venv/bin/jupyter-lab
```
