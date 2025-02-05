#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright ©2025 Senzing, Inc. All rights reserved.

"""
Synthetic data generation for investigative graphs based on network
motifs which represent patterns of bad-actor tradecraft.

Given a configuration of distributions for:
  - network size and shape
  - fraud kinds and rates

A high-level description of a process for generating synthetic graph
data is:

  1. Generate entities for people
     - sample from distribution for inclusion in cliques
     - sample from distribution for channel seperation
     - sample from distribution for anomalies (false positives)
     - populate roles, beneficiary metadata, etc.
  2. Generate entities for shell corp intermediary organizations.
     - sample from distribution for inclusion in cliques
  3. Load network motif patterns representing fraud tradecraft.
     - may be overlapping?
  4. Generate graph elements based on all of the above.
     - generate entities
     - generate network
     - generate transactions
  5. Serialize output
     - format: node-link, JSONL, Parquet, etc.
"""


from collections import defaultdict
import json
import pathlib
import sys
import traceback
import typing
import unicodedata

from icecream import ic  # type: ignore  # pylint: disable=E0401
from names_dataset import NameDataset, NameWrapper
import networkx as nx


MAX_MATCH_LEVEL: float = 11.0


######################################################################
## local function definitions

def report_graph (
    graph: nx.DiGraph,
    ) -> None:
    """foo"""
    ic(len(graph.nodes))
    ic(len(graph.edges))

    for src_id, dat in graph.nodes(data = True):
        ic(src_id, dat)

    for src_id, dst_id, dat in graph.edges(data = True):
        ic(src_id, dst_id, dat)


def eval_names_dataset (
    ) -> None:
    """foo"""
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
    """foo"""
    if text is None:
        return None

    return str(unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8").replace("\u200b", ""))


def get_name (
    dat: dict,
    ) -> str:
    """foo"""
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
    """foo"""
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


######################################################################
## main entry point

if __name__ == "__main__":
    graph: nx.DiGraph = nx.DiGraph()
    #eval_names_dataset()

    ## load data from OpenSanctions
    os_file: pathlib.Path = pathlib.Path("open-sanctions.json")
    
    with open(os_file, "r", encoding = "utf-8") as fp:
        for line in fp:
            dat: dict = json.loads(line)
            rec_id: str = dat["RECORD_ID"]

            graph.add_node(
                rec_id,
                kind = "data",
                name = scrub_text(get_name(dat)),
                addr = scrub_text(get_addr(dat)),
            )

    ## load data from Open Ownership
    os_file: pathlib.Path = pathlib.Path("open-ownership.json")
    
    with open(os_file, "r", encoding = "utf-8") as fp:
        for line in fp:
            dat: dict = json.loads(line)
            rec_id: str = dat["RECORD_ID"]

            graph.add_node(
                rec_id,
                kind = "data",
                name = scrub_text(get_name(dat)),
                addr = scrub_text(get_addr(dat)),
            )

    ## load the ER export from Senzing
    er_export_file: pathlib.Path = pathlib.Path("export.json")

    with open(er_export_file, "r", encoding = "utf-8") as fp:
        for line in fp:
            dat: dict = json.loads(line)
            ent_id: str = "sz_" + str(dat["RESOLVED_ENTITY"]["ENTITY_ID"]).strip()
            #ic(ent_id, dat)

            if ent_id not in graph.nodes:
                graph.add_node(
                    ent_id,
                    kind = "entity",
                )

            ent_desc: typing.Optional[ str ] = None
            ent_addr: typing.Optional[ dict ] = None

            # link to resolved data records
            for dat_rec in dat["RESOLVED_ENTITY"]["RECORDS"]:
                #ic(ent_id, dat_rec)
                dat_src = dat_rec["DATA_SOURCE"]
                rec_id = dat_rec["RECORD_ID"]

                graph.add_edge(
                    ent_id,
                    rec_id,
                    kind = "resolved",
                    why = scrub_text(dat_rec["MATCH_KEY"]),
                    prob = int(dat_rec["MATCH_LEVEL"]) / MAX_MATCH_LEVEL,
                )

                ent_desc = dat_rec["ENTITY_DESC"]

            graph.nodes[ent_id]["name"] = scrub_text(ent_desc)

            # link to related entities
            for rel_rec in dat["RELATED_ENTITIES"]:
                #ic(rel_rec)
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

    ## serialize the graph
    graph_file: pathlib.Path = pathlib.Path("graph.json")

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

    sys.exit(0)

    ## review how much data got linked
    report_graph(graph)

    ## examine the subgraphs
    for clique in nx.weakly_connected_components(graph):
        if len(clique) > 4:
            print(len(clique), clique)

    # sample from entities distribution for inclusion in cliques
