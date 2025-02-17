#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
see copyright/license <https://github.com/DerwenAI/kleptosyn/blob/main/LICENSE>

Represent a graph of potential bad-actor networks.
"""

from collections import Counter
import json
import pathlib
import random
import sys
import traceback
import typing
import unicodedata

#from charset_normalizer import from_bytes
from icecream import ic  # type: ignore  # pylint: disable=E0401
import networkx as nx
import pycountry


######################################################################
## class definitions: network of bad actors

class Network:
    """
Network to sample for simulated bad actors.
    """
    ER_ENTITY_PREFIX: str = "sz_"

    # graph semantics: <https://followthemoney.tech/explorer/>
    # ftm:Person, ftm:Company, ftm:Payment
    FTM_CLASSES: typing.Dict[ str, str ] = {
        "person": "ftm:Person",
        "organization": "ftm:Company",
        "transaction": "ftm:Payment",
    }


    def __init__ (
        self,
        config: dict,
        ) -> None:
        """
Constructor.
        """
        self.config: dict = config
        self.graph: nx.DiGraph = nx.DiGraph()


    def scrub_text (
        self,
        text: str,
        ) -> typing.Optional[ str ]:
        """
Scrub text of non-printable characters, typesetting artifacts, UTF-8 errors, etc.
Courtesy of <https://github.com/DerwenAI/pytextrank>
        """
        if text is None:
            return None

        #return str(unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8").replace("\u200b", ""))

        min_scrub: str = unicodedata.normalize(
            "NFKD",
            text,
            #str(from_bytes(str.encode(text)).best()) # unneeded when unicode issues are fixed in the data
        ).replace("\u200b", "").strip()

        #min_scrub: str = unicodedata.normalize("NFKD", text).replace("\u200b", "").strip()
        #max_scrub: str = min_scrub.encode("ascii", "ignore").decode("utf-8").strip()

        return min_scrub


    def extract_name (
        self,
        dat: dict,
        *,
        debug: bool = False,  # pylint: disable=W0613
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
                        if "NAME_ORG" in rec:
                            name = rec["NAME_ORG"]
                            break
                    elif "PRIMARY_NAME_ORG" in rec:
                        name = rec["PRIMARY_NAME_ORG"]
                        break

            if name is not None:
                name = self.scrub_text(name)

                if name == "-" or len(name) < 1:  # type: ignore
                    name = None

            if name is None:
                print("extract_name DQ:", dat)
                sys.exit(0)

            return name

        except Exception as ex:  # pylint: disable=W0718
            ic(ex)
            traceback.print_exc()

            ic(dat)
            sys.exit(0)


    def extract_addr (
        self,
        dat: dict,
        *,
        debug: bool = False,  # pylint: disable=W0613
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
                addr = self.scrub_text(addr)

                if addr == "-" or len(addr) < 1:  # type: ignore
                    addr = None

            return addr

        except Exception as ex:  # pylint: disable=W0718
            ic(ex)
            traceback.print_exc()

            ic(dat)
            sys.exit(0)


    def extract_country (  # pylint: disable=R0912
        self,
        dat: dict,
        *,
        debug: bool = False,  # pylint: disable=W0613
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

        except Exception as ex:  # pylint: disable=W0718
            ic(ex)
            traceback.print_exc()

            ic(dat)
            sys.exit(0)


    def load_dataset (
        self,
        dat_file: pathlib.Path,
        ) -> None:
        """
Load a Senzing formatted JSON dataset.
        """
        with open(dat_file, "rb") as fp:
            for line in fp:
                dat: dict = json.loads(line)
                rec_id: str = dat["RECORD_ID"]

                self.graph.add_node(
                    rec_id,
                    kind = "data",
                    type = self.FTM_CLASSES[dat["RECORD_TYPE"].lower()],
                    name = self.extract_name(dat),
                    addr = self.extract_addr(dat),
                    country = self.extract_country(dat),
                )

                # FOO
                # "RELATIONSHIPS": [{"REL_POINTER_DOMAIN": "OOR", "REL_POINTER_KEY": "12052062250481936308"


    def load_er_export (  # pylint: disable=R0914
        self,
        *,
        er_export_file: pathlib.Path = pathlib.Path("export.json"),
        ) -> None:
        """
Load the entity resolution results exported from Senzing.
        """
        with open(er_export_file, "rb") as fp:
            for line in fp:
                dat: dict = json.loads(line)
                ent_id: str = self.ER_ENTITY_PREFIX + str(dat["RESOLVED_ENTITY"]["ENTITY_ID"]).strip()

                if ent_id not in self.graph.nodes:
                    self.graph.add_node(
                        ent_id,
                        kind = "entity",
                    )

                ent_desc: typing.Optional[ str ] = None
                ent_type: typing.Optional[ str ] = None

                ent_countries: typing.List[ typing.Optional[ str ]] = []

                # link to resolved data records
                for dat_rec in dat["RESOLVED_ENTITY"]["RECORDS"]:
                    rec_id = dat_rec["RECORD_ID"]

                    self.graph.add_edge(
                        ent_id,
                        rec_id,
                        kind = "resolved",
                        why = self.scrub_text(dat_rec["MATCH_KEY"]),
                        prob = int(dat_rec["MATCH_LEVEL"]),
                    )

                    ent_type = self.graph.nodes[rec_id]["type"]

                    desc: str = dat_rec["ENTITY_DESC"].strip()
                    country: typing.Optional[ str ] = self.graph.nodes[rec_id]["country"]

                    if len(desc) > 0:
                        ent_desc = desc

                    if country is not None and len(country) > 0:
                        ent_countries.append(self.graph.nodes[rec_id]["country"])

                self.graph.nodes[ent_id]["type"] = ent_type
                self.graph.nodes[ent_id]["name"] = self.scrub_text(ent_desc)  # type: ignore

                country_counts: Counter = Counter(ent_countries)

                if len(country_counts) > 0:
                    self.graph.nodes[ent_id]["country"] = country_counts.most_common()[0][0]

                # link to related entities
                for rel_rec in dat["RELATED_ENTITIES"]:
                    rel_id: str = self.ER_ENTITY_PREFIX + str(rel_rec["ENTITY_ID"]).strip()

                    if rel_id not in self.graph.nodes:
                        self.graph.add_node(
                            rel_id,
                            kind = "entity",
                        )

                    self.graph.add_edge(
                        ent_id,
                        rel_id,
                        kind = "related",
                        why = self.scrub_text(rel_rec["MATCH_KEY"]),
                        prob = int(rel_rec["MATCH_LEVEL"]),
                    )

    def repair (
        self,
        ) -> None:
        """
        Repair the names for each resolved entity by inheriting up
        from the resolved data records
        """
        for node_id, dat in self.graph.nodes(data = True):
            if dat["kind"] == "entity" and dat["type"] == "ftm:Person" and dat["name"] is None:
                for neigh_id in self.graph.neighbors(node_id):
                    rec_dat: dict = self.graph.nodes[neigh_id]

                    if rec_dat["kind"] == "data":
                        self.graph.nodes[node_id]["name"] = rec_dat["name"]


    def load (
        self,
        ) -> None:
        """
Load the "risk" and "link" data, plus their exported entity resolution,
to construct a graph to sample as simulated bad actors.

  - OpenSanctions (risk data)
  - Open Ownership (link data)
        """
        self.load_dataset(pathlib.Path("open-sanctions.json"))
        self.load_dataset(pathlib.Path("open-ownership.json"))
        self.load_er_export()
        self.repair()

        # use centrality to rank entities (e.g., as influentual UBOs)
        for node_id, rank in nx.eigenvector_centrality(self.graph).items():
            self.graph.nodes[node_id]["rank"] = rank


    def get_pii_features (
        self,
        node_id: str,
        ) -> dict:
        """
Accessor builds and returns a dictionary of the PII features for the
specified entity.
        """
        rec_id: str = node_id

        if self.graph.nodes[node_id]["kind"] == "entity":
            rec_list: typing.List[ str ] = [
                neigh_id
                for neigh_id in self.graph.neighbors(node_id)
                if self.graph.nodes[neigh_id]["kind"] == "data"
                #if self.graph.nodes[neigh_id]["addr"] is not None
            ]

            if len(rec_list) > 0:
                rec_id = random.choice(rec_list)

        if rec_id is None:
            ic(node_id)
            sys.exit(0)

        return {
            "name": self.graph.nodes[rec_id]["name"],
            "addr": self.graph.nodes[rec_id]["addr"],
            "type": "person" if (self.graph.nodes[rec_id]["type"] == "ftm:Person") else "organization",
        }


    def dump (
        self,
        *,
        graph_file: pathlib.Path = pathlib.Path("graph.json"),
        ) -> None:
        """
Serialize the bad-actor network.
NB: this is considered the best way to handle JSON file writes with mixed charsets.
        """
        with open(graph_file, "w") as fp:  # pylint: disable=W1514
            dat: dict = nx.node_link_data(
                self.graph,
                edges = "edges", # for forward compatibility
            )

            json.dump(
                dat,
                fp,
                indent = 2,
                ensure_ascii = False,
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
