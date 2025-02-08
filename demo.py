#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright ©2025 Senzing, Inc. All rights reserved.

"""
Synthetic data generation for investigative graphs based on
patterns of bad-actor tradecraft.

Steps (so far):
  * load slice of OpenSanctions (risk data)
  * load slice of Open Ownership (link data)
  * load the Senzing ER results for these datasets
  * construct a directed graph in `NetworkX` from these connected elements
    + repair the names for each resolved entity (inherited from data records)
  * serialize the graph as JSON in node-link format
  * measure centrality to rank actors within each subgraph
  * partition into subgraphs
  * select N subgraphs as the bad-actor networks
    + identify the top-ranked person as the ultimate beneficial owner
    + identify the set of shell corporations engaging in B2B money transfers
    + generate paths among the shell corps
    + sample distributions to simulate money transfers: timing, amounts
  * use `PyVis` to render an interactive visualization
  * generate transactions across the motifs (event data)
     + parameterize the timing and chunking

TODO:
  - generate legit transactions as decoys (~98%)
  - flatten the graph: serialize records as a set of CSV files
  - have Clair eval to run ER + KG + algos to identify fraud

  - load network motif patterns representing bad-actor tradecraft

  - generate entities for shell corp intermediary organizations
     + apply _channel separation_ to obscure beneficial owners
     + use `name-dataset` and `random-address` to generate intermediares

"""


from collections import Counter, defaultdict
from datetime import datetime, timedelta
import itertools
import json
import pathlib
import random
import re
import sys
import traceback
import typing
import unicodedata

from icecream import ic  # type: ignore  # pylint: disable=E0401
from names_dataset import NameDataset, NameWrapper
import networkx as nx
import numpy as np
import pandas as pd
import pycountry


APPROX_FRAUD_RATE: float = 0.02
MAX_MATCH_LEVEL: float = 11.0
MAX_PATH_LEN: int = 7
MIN_CLIQUE_SIZE: int = 3

# transaction distributions derived from `occrp.ipynb`
INTER_ARRIVAL_MEDIAN: float = 8.7
INTER_ARRIVAL_STDEV: float = 32.745006

TRANSFER_CHUNK_MEDIAN: float = 1.963890e+05
TRANSFER_CHUNK_STDEV: float = 5.301957e+05

TRANSFER_TOTAL_MEDIAN: float = 1.408894e+06
TRANSFER_TOTAL_STDEV: float = 8.014517e+07


# semantics: <https://followthemoney.tech/explorer/>
# ftm:Person, ftm:Company, ftm:Payment
FTM_CLASSES: typing.Dict[ str, str ] = {
    "person": "ftm:Person",
    "organization": "ftm:Company",
    "transaction": "ftm:Payment",
}

SANCTIONED_COUNTRIES: typing.Set[ str ] = set([
    "RU",
])

EMPTY_QUOTE_PAT = re.compile("\".*\"")


######################################################################
## class definitions: simulated patterns of tradecraft

class Simulation:
    """
Simulated patterns of tradecraft.
    """

    def __init__ (
        self,
        config: dict,
        ) -> None:
        """
Constructor.
        """
        self.config: dict = config
        self.rng: np.random.Generator = np.random.default_rng()


    def rng_gaussian (
        self,
        *,
        mean: float = 0.0,
        stdev: float = 1.0,
        ) -> float:
        """
Sample random numbers from a Gaussian distribution.
        """
        return float(self.rng.normal(loc = mean, scale = stdev, size = 1)[0])


    def rng_exponential (
        self,
        *,
        scale: float = 1.0,
        ) -> float:
        """
Sample random numbers from an Exponential distribution.
        """
        return float(self.rng.exponential(scale = scale, size = 1)[0])


    def rng_poisson (
        self,
        *,
        lambda_: float = 1.0,
        ) -> float:
        """
Sample random numbers from a Poisson distribution.
        """
        return float(self.rng.poisson(lam = lambda_, size = 1)[0])


######################################################################
## class definitions: network of bad actors

class Network:
    """
Network to sample for simulated bad actors.
    """

    def __init__ (
        self,
        config: dict,
        ) -> None:
        """
Constructor.
        """
        self.config: dict = config
        self.graph: nx.DiGraph = nx.DiGraph()


    def load_graph (
        self,
        *,
        er_export_file: pathlib.Path = pathlib.Path("export.json"),
        ) -> None:
        """
Load the entity resolution results exported from Senzing.
        """
        with open(er_export_file, "r", encoding = "utf-8") as fp:
            for line in fp:
                dat: dict = json.loads(line)
                ent_id: str = "sz_" + str(dat["RESOLVED_ENTITY"]["ENTITY_ID"]).strip()

                if ent_id not in self.graph.nodes:
                    self.graph.add_node(
                        ent_id,
                        kind = "entity",
                    )

                ent_addr: typing.Optional[ dict ] = None
                ent_desc: typing.Optional[ str ] = None
                ent_type: typing.Optional[ str ] = None

                ent_countries: typing.List[ typing.Optional[ str ]] = []

                # link to resolved data records
                for dat_rec in dat["RESOLVED_ENTITY"]["RECORDS"]:
                    dat_src = dat_rec["DATA_SOURCE"]
                    rec_id = dat_rec["RECORD_ID"]

                    self.graph.add_edge(
                        ent_id,
                        rec_id,
                        kind = "resolved",
                        why = scrub_text(dat_rec["MATCH_KEY"]),
                        prob = int(dat_rec["MATCH_LEVEL"]) / MAX_MATCH_LEVEL,
                    )

                    ent_type = self.graph.nodes[rec_id]["type"]

                    desc: str = dat_rec["ENTITY_DESC"].strip()
                    country: typing.Optional[ str ] = self.graph.nodes[rec_id]["country"]

                    if len(desc) > 0:
                        ent_desc = desc

                    if country is not None and len(country) > 0:
                        ent_countries.append(self.graph.nodes[rec_id]["country"])

                self.graph.nodes[ent_id]["type"] = ent_type
                self.graph.nodes[ent_id]["name"] = scrub_text(ent_desc)

                country_counts: Counter = Counter(ent_countries)

                if len(country_counts) > 0:
                    self.graph.nodes[ent_id]["country"] = country_counts.most_common()[0][0]

                # link to related entities
                for rel_rec in dat["RELATED_ENTITIES"]:
                    rel_id: str = "sz_" + str(rel_rec["ENTITY_ID"]).strip()

                    if rel_id not in self.graph.nodes:
                        self.graph.add_node(
                            rel_id,
                            kind = "entity",
                        )

                    self.graph.add_edge(
                        ent_id,
                        rel_id,
                        kind = "related",
                        why = scrub_text(rel_rec["MATCH_KEY"]),
                        prob = int(rel_rec["MATCH_LEVEL"]) / MAX_MATCH_LEVEL,
                    )

    def load (
        self,
        ) -> None:
        """
Load the "risk" and "link" data, plus their exported entity resolution,
to construct a graph to sample as simulated bad actors.

  - OpenSanctions (risk data)
  - Open Ownership (link data)
        """
        load_data(self.graph, pathlib.Path("open-sanctions.json"))
        load_data(self.graph, pathlib.Path("open-ownership.json"))

        self.load_graph()

        for node_id, rank in nx.eigenvector_centrality(self.graph).items():
            self.graph.nodes[node_id]["rank"] = rank

        # repair the names for each resolved entity by inheriting up
        # from the resolved data records
        for node_id, dat in self.graph.nodes(data = True):
            if dat["kind"] == "entity" and dat["type"] == "ftm:Person" and dat["name"] is None:
                for neigh_id in self.graph.neighbors(node_id):
                    rec_dat: dict = self.graph.nodes[neigh_id]

                    if rec_dat["kind"] == "data":
                        self.graph.nodes[node_id]["name"] = rec_dat["name"]


    def dump (
        self,
        *,
        graph_file: pathlib.Path = pathlib.Path("graph.json"),
        ) -> None:
        """
Serialize the bad network.
        """
        with open(graph_file, "w", encoding = "utf-8") as fp:
            dat: dict = nx.node_link_data(
                self.graph,
                edges = "edges", # for forward compatibility
            )

            json.dump(
                dat,
                fp,
                indent = 2,
            )


    def report (
        self,
        ) -> None:
        """
Report measures for the loaded network.
        """
        ic(len(self.graph.nodes))
        ic(len(self.graph.edges))

        for src_id, dat in self.graph.nodes(data = True):
            ic(src_id, dat)

        for src_id, dst_id, dat in self.graph.edges(data = True):
            ic(src_id, dst_id, dat)


######################################################################
## local function definitions

def eval_names_dataset (
    ) -> None:
    """
Generate synthetic data about names, based in countries.
<https://github.com/philipperemy/name-dataset>
    """
    nd = NameDataset()
    ic(NameWrapper(nd.search("Philippe")).describe)

    foo = nd.get_top_names(
        n = 11,
        use_first_names = False,
        country_alpha2 = "IR",
        #gender = "F",
    )

    ic(foo)


def scrub_text (
    text: str,
    ) -> typing.Optional[ str ]:
    """
Scrub text of non-printable characters, typesetting artifacts, UTF-8 errors, etc.
Courtesy of <https://github.com/DerwenAI/pytextrank>
    """
    if text is None:
        return None

    #return str(unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8").replace("\u200b", ""))

    min_scrub: str = unicodedata.normalize("NFKD", text).replace("\u200b", "").strip()
    max_scrub: str = min_scrub.encode("ascii", "ignore").decode("utf-8").strip()

    if len(max_scrub) < 1 or EMPTY_QUOTE_PAT.match(max_scrub) is not None:
        return min_scrub

    return max_scrub


def extract_name (
    dat: dict,
    *,
    debug: bool = False,
    ) -> str:
    """
Extract names from the input data records.
    """
    try:
        name: typing.Optional[ str ] = None

        if "PRIMARY_NAME_FULL" in dat:
            name = dat["PRIMARY_NAME_FULL"]
        else:
            for rec in dat["NAMES"]:
                if "NAME_TYPE" in rec and rec["NAME_TYPE"] == "PRIMARY":
                    if "NAME_FULL" in rec:
                        name = rec["NAME_FULL"]
                        break
                    elif "NAME_ORG" in rec:
                        name = rec["NAME_ORG"]
                        break
                elif "PRIMARY_NAME_ORG" in rec:
                    name = rec["PRIMARY_NAME_ORG"]
                    break

        if name is not None:
            name = scrub_text(name)

            if name == "-" or len(name) < 1:
                name = None
        
        if name is None:
            print("extract_name DQ:", dat)
            sys.exit(0)

        return name

    except Exception as ex:
        ic(ex)
        traceback.print_exc()

        ic(dat)
        sys.exit(0)


def extract_addr (
    dat: dict,
    *,
    debug: bool = False,
    ) -> typing.Optional[ str ]:
    """
Extract addresses from the input data records.
    """
    try:
        addr: typing.Optional[ str ] = None

        if "ADDRESSES" in dat:
            for rec in dat["ADDRESSES"]:
                if "ADDR_FULL" in rec:
                    addr = rec["ADDR_FULL"]
                    break

        if addr is not None:
            addr = scrub_text(addr)

            if addr == "-" or len(addr) < 1:
                addr = None
        
        return addr
    except Exception as ex:
        ic(ex)
        traceback.print_exc()

        ic(dat)
        sys.exit(0)


def extract_country (
    dat: dict,
    *,
    debug: bool = False,
    ) -> typing.Optional[ str ]:
    """
Extract country codes from the input data records.
    """
    try:
        country: typing.Optional[ str ] = None

        if "REGISTRATION_COUNTRY" in dat:
            country = dat["REGISTRATION_COUNTRY"].strip().upper()
        elif "COUNTRIES" in dat:
            for rec in dat["COUNTRIES"]:
                for key, val in rec.items():
                    if key in ["CITIZENSHIP", "NATIONALITY", "REGISTRATION_COUNTRY"]:
                        country = val.strip().upper()
                        break
        elif "ADDRESSES" in dat:
            for rec in dat["ADDRESSES"]:
                for key, val in rec.items():
                    if key in ["ADDR_COUNTRY"]:
                        country = val.strip().upper()
                        break
        elif "ATTRIBUTES" in dat:
            for rec in dat["ATTRIBUTES"]:
                for key, val in rec.items():
                    if key in ["NATIONALITY"]:
                        country = val.strip().upper()
                        break

        # data quality check
        if country is not None:
            if len(country) < 1:
                country = None

            else:
                country_info = pycountry.countries.get(alpha_2 = country)

                if country_info is None:
                    print("UNKONWN:", country)

        return country
    except Exception as ex:
        ic(ex)
        traceback.print_exc()

        ic(dat)
        sys.exit(0)


def load_data (
    graph: nx.DiGraph,
    dat_file: pathlib.Path,
    ) -> None:
    """
Load a Senzing formatted JSON dataset.
    """
    with open(dat_file, "r", encoding = "utf-8") as fp:
        for line in fp:
            dat: dict = json.loads(line)
            rec_id: str = dat["RECORD_ID"]

            graph.add_node(
                rec_id,
                kind = "data",
                type = FTM_CLASSES[dat["RECORD_TYPE"].lower()],
                name = extract_name(dat),
                addr = extract_addr(dat),
                country = extract_country(dat),
            )


def select_bad_actor (
    graph: nx.DiGraph,
    ) -> typing.List[ str ]:
    """
Select one viable "bad actor" network from among the subgraphs
    """
    bad_cliques: list = []

    for clique in nx.weakly_connected_components(graph):
        owners: list = sorted([
            ( graph.nodes[node_id]["rank"], node_id, )
            for node_id in clique
            if graph.nodes[node_id]["kind"] == "entity"
            if graph.nodes[node_id]["type"] == "ftm:Person"
        ], reverse = True)

        shells: list = [
            node_id
            for node_id in clique
            if graph.nodes[node_id]["kind"] == "entity"
            if graph.nodes[node_id]["type"] == "ftm:Company"
            if graph.nodes[node_id]["country"] not in SANCTIONED_COUNTRIES
        ]

        if len(owners) > 0 and len(shells) >= MIN_CLIQUE_SIZE:
            bad_cliques.append([ owners[0][1] ] + shells)

    return random.choice(bad_cliques)


######################################################################
## main entry point

if __name__ == "__main__":
    #eval_names_dataset()

    config: dict = {}
    sim: Simulation = Simulation(config)
    net: Network = Network(config)

    net.load()
    net.dump()

    #net.report()
    #sys.exit(0)

    ## select one subgraph as the bad-actor network
    bad_clique: list = select_bad_actor(net.graph)

    for node_id in bad_clique:
        dat: dict = net.graph.nodes[node_id]
        ic(node_id, dat)

    ubo_person: str = bad_clique[0]
    shell_corps: list = bad_clique[1:]
    path_range: typing.List[ int ] = list(range(MIN_CLIQUE_SIZE, min(len(shell_corps) + 1, MAX_PATH_LEN)))
    total_funds: float = round(sim.rng_gaussian(mean = TRANSFER_TOTAL_MEDIAN / 2.0, stdev = TRANSFER_TOTAL_MEDIAN / 100.0), 2)

    ic(ubo_person, total_funds, path_range, shell_corps)
    #sys.exit(0)

    ## generate paths among the shell corps
    xact: typing.List[ dict ] = []
    subtotal: float = 0.0

    while subtotal < total_funds:
        paths = [
            path
            for path in itertools.permutations(shell_corps, r = random.choice(path_range))
        ]

        for path in random.sample(paths, 4):
            ic(ubo_person, subtotal, path[0])

            for pair in itertools.pairwise(path):
                src_id: int = pair[0]
                dst_id: int = pair[1]

                gen_amount: float = sim.rng_gaussian(mean = TRANSFER_CHUNK_MEDIAN / 2.0, stdev = TRANSFER_CHUNK_MEDIAN / 10.0)
                amount: float = round(TRANSFER_CHUNK_MEDIAN - gen_amount, 2)
                assert amount > 0.0, f"negative amount: {gen_amount}"

                subtotal += amount

                gen_offset: float = sim.rng_poisson(lambda_ = INTER_ARRIVAL_MEDIAN)
                date: datetime = datetime.now() + timedelta(hours = gen_offset * 24.0)

                xact.append({
                    "payer": net.graph.nodes[src_id]["name"],
                    "payer_country": net.graph.nodes[src_id]["country"],
                    "benef": net.graph.nodes[dst_id]["name"],
                    "benef_country": net.graph.nodes[dst_id]["country"],
                    "amount": amount,
                    "date": date.date().isoformat(),
                })

    ## export the generated transactions
    df_xact: pd.DataFrame = pd.DataFrame.from_dict(
        xact,
        orient = "columns"
    )

    ic(df_xact.head())

    xact_file: pathlib.Path = pathlib.Path("transact.csv")
    df_xact.to_csv(xact_file, sep = "\t", encoding = "utf-8")
