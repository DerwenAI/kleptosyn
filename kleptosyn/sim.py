#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simulating patterns of bad-actor tradecraft.

see copyright/license <https://github.com/DerwenAI/kleptosyn/blob/main/LICENSE>
"""

from datetime import datetime, timedelta
import itertools
import random
import typing

from icecream import ic  # type: ignore  # pylint: disable=E0401
import networkx as nx
import numpy as np

from .net import Network
from .syn import SynData


######################################################################
## class definitions: simulated patterns of tradecraft

class Simulation:
    """
Simulated patterns of tradecraft.
    """
    APPROX_FRAUD_RATE: float = 0.02
    MAX_PATH_LEN: int = 7
    MIN_CLIQUE_SIZE: int = 3

    SANCTIONED_COUNTRIES: typing.Set[ str ] = set([
        "RU",
    ])

    # distributions derived from `occrp.ipynb` analysis
    INTER_ARRIVAL_MEDIAN: float = 8.7
    INTER_ARRIVAL_STDEV: float = 32.745006

    TRANSFER_CHUNK_MEDIAN: float = 1.963890e+05
    TRANSFER_CHUNK_STDEV: float = 5.301957e+05

    TRANSFER_TOTAL_MEDIAN: float = 1.408894e+06
    TRANSFER_TOTAL_STDEV: float = 8.014517e+07


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


    def select_bad_actor (
        self,
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
                if graph.nodes[node_id]["country"] not in self.SANCTIONED_COUNTRIES
            ]

            if len(owners) > 0 and len(shells) >= self.MIN_CLIQUE_SIZE:
                bad_cliques.append([ owners[0][1] ] + shells)

        return random.choice(bad_cliques)


    def simulate (
        self,
        net: Network,
        syn: SynData,
        ) -> None:
        """
Simulate patterns of tradecraft across sampled bad-actor networks.
        """
        ## select one subgraph as the bad-actor network
        bad_clique: list = self.select_bad_actor(net.graph)

        for node_id in bad_clique:
            dat: dict = net.graph.nodes[node_id]
            ic(node_id, dat)

        ubo_person: str = bad_clique[0]
        shell_corps: list = bad_clique[1:]

        path_range: typing.List[ int ] = list(range(self.MIN_CLIQUE_SIZE, min(len(shell_corps) + 1, self.MAX_PATH_LEN)))

        total_funds: float = round(self.rng_gaussian(mean = self.TRANSFER_TOTAL_MEDIAN / 2.0, stdev = self.TRANSFER_TOTAL_MEDIAN / 100.0), 2)

        ic(ubo_person, total_funds, path_range, shell_corps)

        ## generate paths among the shell corps
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

                    gen_amount: float = self.rng_gaussian(mean = self.TRANSFER_CHUNK_MEDIAN / 2.0, stdev = self.TRANSFER_CHUNK_MEDIAN / 10.0)
                    amount: float = round(self.TRANSFER_CHUNK_MEDIAN - gen_amount, 2)
                    assert amount > 0.0, f"negative amount: {gen_amount}"

                    subtotal += amount

                    gen_offset: float = self.rng_poisson(lambda_ = self.INTER_ARRIVAL_MEDIAN)
                    date: datetime = datetime.now() + timedelta(hours = gen_offset * 24.0)

                    syn.add_transact({
                        "payer": net.graph.nodes[src_id]["name"],
                        "payer_country": net.graph.nodes[src_id]["country"],
                        "benef": net.graph.nodes[dst_id]["name"],
                        "benef_country": net.graph.nodes[dst_id]["country"],
                        "amount": amount,
                        "date": date.date().isoformat(),
                    })
