# kleptosyn

Synthetic data generation for investigative graphs based on network motifs


## Build an environment

Based on using Python 3.11

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -U pip wheel
python3 -m pip install -r requirements.txt
```

You will also the CLI for Google Cloud to get the input datasets:
<https://cloud.google.com/storage/docs/discover-object-storage-gcloud>


## Load the data

```bash
gcloud storage cp gs://erkg/starterkit/open-sanctions.json .
gcloud storage cp gs://erkg/starterkit/open-ownership.json .
gcloud storage cp gs://erkg/starterkit/export.json .
```

## Run the demo script

```bash
./demo.py
```


## Run the notebooks

```bash
./venv/bin/jupyter-lab
```
