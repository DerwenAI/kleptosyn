#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright ©2025 Senzing, Inc. All rights reserved.

"""
Synthetic data generation for investigative graphs based on network
motifs which represent patterns of bad-actor tradecraft.

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

TODO:
  - load network motif patterns representing bad-actor tradecraft
  - generate entities for shell corp intermediary organizations
     + apply _channel separation_ to obscure beneficial owners
     + use `name-dataset` and `random-address` to generate intermediares
  - generate transactions across the motifs (event data)
     + parameterize the timing and chunking
  - generate legit transactions as decoys (~98%)
  - flatten the graph: serialize records as a set of CSV files
  - have Clair eval to run ER + KG + algos to identify fraud
"""


from collections import defaultdict
import itertools
import json
import pathlib
import random
import sys
import traceback
import typing
import unicodedata

from icecream import ic  # type: ignore  # pylint: disable=E0401
from names_dataset import NameDataset, NameWrapper
import networkx as nx
import numpy as np


APPROX_FRAUD_RATE: float = 0.02
MAX_MATCH_LEVEL: float = 11.0
MIN_CLIQUE_SIZE: int = 3
TRANSFER_CHUNK: float = 10000.0

RNG: np.random.Generator = np.random.default_rng()


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

    return str(unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8").replace("\u200b", ""))


def get_name (
    dat: dict,
    ) -> str:
    """
Extract names from the input data records.
    """
    try:
        for name_rec in dat["NAMES"]:
            if "PRIMARY_NAME_ORG" in name_rec:
                return name_rec["PRIMARY_NAME_ORG"]
            elif name_rec["NAME_TYPE"] == "PRIMARY":
                if "NAME_ORG" in name_rec:
                    return name_rec["NAME_ORG"]
                else:
                    return name_rec["NAME_FULL"]
            else:
                ic(name_rec)
                sys.exit(0)

    except Exception as ex:
        ic(ex)
        traceback.print_exc()

        ic(dat)
        sys.exit(0)


def get_addr (
    dat: dict,
    ) -> typing.Optional[ str ]:
    """
Extract addresses from the input data records.
    """
    try:
        if "ADDRESSES" in dat:
            for addr_rec in dat["ADDRESSES"]:
                if "ADDR_FULL" in addr_rec:
                    return addr_rec["ADDR_FULL"]

        return None
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
                name = scrub_text(get_name(dat)),
                addr = scrub_text(get_addr(dat)),
                noun = dat["RECORD_TYPE"].lower(),
            )


def load_graph (
    ) -> nx.DiGraph:
    """
Load the seed graph from input data files.
    """
    graph: nx.DiGraph = nx.DiGraph()

    # load data Senzing-formatted JSON
    #   - OpenSanctions (risk data)
    #   - Open Ownership (link data)
    load_data(graph, pathlib.Path("open-sanctions.json"))
    load_data(graph, pathlib.Path("open-ownership.json"))

    # load the ER export from Senzing
    er_export_file: pathlib.Path = pathlib.Path("export.json")

    with open(er_export_file, "r", encoding = "utf-8") as fp:
        for line in fp:
            dat: dict = json.loads(line)
            ent_id: str = "sz_" + str(dat["RESOLVED_ENTITY"]["ENTITY_ID"]).strip()

            if ent_id not in graph.nodes:
                graph.add_node(
                    ent_id,
                    kind = "entity",
                )

            ent_addr: typing.Optional[ dict ] = None
            ent_desc: typing.Optional[ str ] = None
            ent_noun: typing.Optional[ str ] = None

            # link to resolved data records
            for dat_rec in dat["RESOLVED_ENTITY"]["RECORDS"]:
                dat_src = dat_rec["DATA_SOURCE"]
                rec_id = dat_rec["RECORD_ID"]

                graph.add_edge(
                    ent_id,
                    rec_id,
                    kind = "resolved",
                    why = scrub_text(dat_rec["MATCH_KEY"]),
                    prob = int(dat_rec["MATCH_LEVEL"]) / MAX_MATCH_LEVEL,
                )

                desc: str = scrub_text(dat_rec["ENTITY_DESC"]).strip()

                if len(desc) > 0:
                    ent_desc = desc

                ent_noun = graph.nodes[rec_id]["noun"]

            graph.nodes[ent_id]["name"] = scrub_text(ent_desc)
            graph.nodes[ent_id]["noun"] = ent_noun

            # link to related entities
            for rel_rec in dat["RELATED_ENTITIES"]:
                rel_id: str = "sz_" + str(rel_rec["ENTITY_ID"]).strip()

                if rel_id not in graph.nodes:
                    graph.add_node(
                        rel_id,
                        kind = "entity",
                    )

                graph.add_edge(
                    ent_id,
                    rel_id,
                    kind = "related",
                    why = scrub_text(rel_rec["MATCH_KEY"]),
                    prob = int(rel_rec["MATCH_LEVEL"]) / MAX_MATCH_LEVEL,
                )

    return graph


def report_graph (
    graph: nx.DiGraph,
    ) -> None:
    """
Report measures about the loaded seed graph.
    """
    ic(len(graph.nodes))
    ic(len(graph.edges))

    for src_id, dat in graph.nodes(data = True):
        ic(src_id, dat)

    for src_id, dst_id, dat in graph.edges(data = True):
        ic(src_id, dst_id, dat)


def dump_graph (
    graph: nx.DiGraph,
    *,
    graph_file: pathlib.Path = pathlib.Path("graph.json"),
    ) -> None:
    """
Serialize the seed graph.
    """
    with open(graph_file, "w", encoding = "utf-8") as fp:
        dat: dict = nx.node_link_data(
            graph,
            edges = "edges", # for forward compatibility
        )

        json.dump(
            dat,
            fp,
            indent = 2,
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
            if graph.nodes[node_id]["noun"] == "person"
        ], reverse = True)

        shells: list = [
            node_id
            for node_id in clique
            if graph.nodes[node_id]["kind"] == "entity"
            if graph.nodes[node_id]["noun"] == "organization"
        ]

        if len(owners) > 0 and len(shells) >= MIN_CLIQUE_SIZE:
            bad_cliques.append([ owners[0][1] ] + shells)

    return random.choice(bad_cliques)


def rng_gaussian (
    *,
    mean: float = 0.0,
    stdev: float = 1.0,
    size: int = 100,
    ) -> typing.Iterator[ float ]:
    """
Sample random numbers from a Gaussian distribution.
    """
    for sample in RNG.normal(loc = mean, scale = stdev, size = (size, 1)):
        for num in sample:
            yield float(num)


def rng_exponential (
    *,
    scale: float = 1.0,
    size: int = 100,
    ) -> typing.Iterator[ float ]:
    """
Sample random numbers from an Exponential distribution.
    """
    for sample in RNG.exponential(scale = scale, size = (size, 1)):
        for num in sample:
            yield float(num)


######################################################################
## main entry point

if __name__ == "__main__":
    #eval_names_dataset()

    graph: nx.DiGraph = load_graph()

    for node_id, rank in nx.eigenvector_centrality(graph).items():
        graph.nodes[node_id]["rank"] = rank

    ## repair the names for each resolved entity
    for node_id, dat in graph.nodes(data = True):
        if dat["kind"] == "entity" and dat["noun"] == "person" and dat["name"] is None:
            for neigh_id in graph.neighbors(node_id):
                rec_dat: dict = graph.nodes[neigh_id]

                if rec_dat["kind"] == "data":
                    graph.nodes[node_id]["name"] = rec_dat["name"]

    dump_graph(graph)
    #sys.exit(0)

    ## review how much data got linked
    #report_graph(graph)

    ## select one subgraph as the bad-actor network
    bad_clique: list = select_bad_actor(graph)

    for node_id in bad_clique:
        dat: dict = graph.nodes[node_id]
        ic(node_id, dat)

    ubo_person: str = bad_clique[0]
    shell_corps: list = bad_clique[1:]

    ic(ubo_person, shell_corps)

    ## generate paths among the shell corps
    paths = [
        path
        for path in itertools.permutations(shell_corps, r = MIN_CLIQUE_SIZE)
    ]

    for path in random.sample(paths, 4):
        ic(path)


    ## sample distributions to simulate money transfers: timing, amounts
    DAYS: int = 2

    for i, sample in enumerate(rng_gaussian(mean = TRANSFER_CHUNK / 2, stdev = TRANSFER_CHUNK / 4)):
        if i > 10:
            break
        else:
            ic(i, TRANSFER_CHUNK - sample)

    for i, sample in enumerate(rng_exponential(scale = DAYS)):
        if i > 10:
            break
        else:
            ic(i, sample)
    

