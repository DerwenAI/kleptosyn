#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
see copyright/license <https://github.com/DerwenAI/kleptosyn/blob/main/LICENSE>

Simulating patterns of bad-actor tradecraft.
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

    # distributions derived from the `occrp.ipynb` analysis
    XACT_TIMING_MEDIAN: float = 8.7
    XACT_TIMING_STDEV: float = 32.745006

    XACT_CHUNK_MEDIAN: float = 1.963890e+05
    XACT_CHUNK_STDEV: float = 5.301957e+05

    XACT_TOTAL_MEDIAN: float = 1.408894e+06
    XACT_TOTAL_STDEV: float = 8.014517e+07


    def __init__ (
        self,
        config: dict,
        ) -> None:
        """
Constructor.
        """
        self.config: dict = config

        self.rng: np.random.Generator = np.random.default_rng()

        self.start: datetime = datetime.fromisoformat(self.config["start_date"])
        self.finish: datetime = self.start

        self.b2b_actors: typing.Set[ str ] = set()
        self.bad_actors: typing.Set[ str ] = set()

        self.total_fraud: float = 0.0


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


    @classmethod
    def rng_uniform_datetime (
        cls,
        start: datetime,
        finish: datetime,
        ) -> datetime:
        """
Sample random dates between two `datetime` objects.
        """
        delta: timedelta = finish - start
        rand_sec: int = random.randrange((delta.days * 24 * 60 * 60) + delta.seconds)

        return start + timedelta(seconds = rand_sec)


    def select_bad_actor (
        self,
        graph: nx.DiGraph,
        ) -> list:
        """
Select the bad-actor networks from among the viable subgraphs.

returns:
    bad-actor network patterns
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
                bad_cliques.append([[ owners[0][1] ] + shells, clique ])

        return random.choice(bad_cliques)


    def gen_xact_amount (
        self,
        ) -> float:
        """
Generate the amount for a transaction, based on a random variable.

returns:
    `amount`: transaction amount, non-negative, rounded to two decimal points.
        """
        gen_amount: float = self.rng_gaussian(
            mean = self.XACT_CHUNK_MEDIAN / 2.0,
            stdev = self.XACT_CHUNK_MEDIAN / 10.0,
        )

        amount: float = round(self.XACT_CHUNK_MEDIAN - gen_amount, 2)
        assert amount > 0.0, f"negative amount: {gen_amount}"

        return amount


    def gen_xact_timing (
        self,
        ) -> datetime:
        """
Generate the timing for a transaction, based on a random variable.

returns:
    `timing`: transaction datetime offset
        """
        gen_offset: float = self.rng_poisson(lambda_ = self.XACT_TIMING_MEDIAN)
        timing: datetime = self.start + timedelta(hours = gen_offset * 24.0)

        return timing


    def run_one_fraud (  # pylint: disable=R0913,R0917
        self,
        net: Network,
        syn: SynData,
        paths: typing.List[ str ],
        *,
        debug: bool = True,
        ) -> float:
        """
Simulate one bad-actor running fraud.

returns:
    `subtotal`: amount of money transferred
        """
        subtotal: float = 0.0

        for path in random.sample(paths, 4):
            for pair in itertools.pairwise(path):
                pay_id: str = pair[0]
                pay_info: dict = net.get_pii_features(pay_id)
                syn.add_entity(pay_info)

                ben_id: str = pair[1]
                ben_info: dict = net.get_pii_features(ben_id)
                syn.add_entity(ben_info)

                amount: float = self.gen_xact_amount()
                subtotal += amount

                timing: datetime = self.gen_xact_timing()
                self.finish = max(self.finish, timing)

                if debug:
                    ic(pair, amount, timing)

                # accumulate results from these simulation steps
                syn.add_transact({
                    "pay": pay_info["name"],
                    "pay_country": net.graph.nodes[pay_id]["country"],
                    "ben": ben_info["name"],
                    "ben_country": net.graph.nodes[ben_id]["country"],
                    "amount": amount,
                    "date": timing.date().isoformat(),
                    syn.FRAUD_COL_NAME: True,
                })

        return subtotal


    def simulate_fraud (
        self,
        net: Network,
        syn: SynData,
        *,
        debug: bool = True,
        ) -> None:
        """
Simulate patterns of tradecraft across sampled bad-actor networks.
        """
        # populate the bad-actor network
        bad_actor: list = self.select_bad_actor(net.graph)
        bad_clique: typing.List[ str ] = bad_actor[0]
        self.bad_actors.update(set(bad_actor[1]))

        if debug:
            for node_id in bad_clique:
                dat: dict = net.graph.nodes[node_id]
                ic(node_id, dat)

        ubo_owner: str = bad_clique[0]
        shell_corps: typing.Set[ str ] = set(bad_clique[1:])

        path_range: typing.List[ int ] = list(
            range(
                self.MIN_CLIQUE_SIZE,
                min(len(shell_corps) + 1, self.MAX_PATH_LEN),
            )
        )

        # generate a target for transferred funds based on a random variable
        target_funds: float = round(
            self.rng_gaussian(
                mean = self.XACT_TOTAL_MEDIAN / 2.0,
                stdev = self.XACT_TOTAL_MEDIAN / 100.0,
            ),
            2,
        )

        if debug:
            ic(ubo_owner, target_funds, path_range, shell_corps)

        # iterate until reaching the target amount
        subtotal: float = 0.0

        while subtotal < target_funds:
            # generate paths among the shell corps
            paths: typing.List[ str ] = list(
                itertools.permutations(  # type: ignore
                    shell_corps,
                    r = random.choice(path_range),
                )
            )

            subtotal += self.run_one_fraud(
                net,
                syn,
                paths,
                debug = debug,
            )

        self.total_fraud += subtotal


    def simulate_legit (
        self,
        net: Network,
        syn: SynData,
        *,
        debug: bool = False,
        ) -> None:
        """
Simulate legit B2B transfers.
        """
        # populate the set of B2B good-actor companies
        shells: typing.List[ str ] = [
            node_id
            for node_id in net.graph.nodes
            if node_id not in self.bad_actors
            if net.graph.nodes[node_id]["country"] not in self.SANCTIONED_COUNTRIES
            if net.graph.nodes[node_id]["kind"] == "entity"
            if net.graph.nodes[node_id]["type"] == "ftm:Company"
        ]

        # generate a target for transferred funds based the inverse of the fraud rate
        target_funds: float = self.total_fraud / self.APPROX_FRAUD_RATE

        # iterate until reaching the target amount
        subtotal: float = 0.0

        while subtotal < target_funds:
            pair: typing.List[ str ] = random.sample(shells, 2)
            self.b2b_actors.update(set(pair))

            pay_id: str = pair[0]
            pay_info: dict = net.get_pii_features(pay_id)
            syn.add_entity(pay_info)

            ben_id: str = pair[1]
            ben_info: dict = net.get_pii_features(ben_id)
            syn.add_entity(ben_info)

            amount: float = self.gen_xact_amount()
            subtotal += amount

            timing: datetime = self.rng_uniform_datetime(self.start, self.finish)

            if debug:
                ic(pair, amount, timing)

            # accumulate results from these simulation steps
            syn.add_transact({
                "pay": pay_info["name"],
                "pay_country": net.graph.nodes[pay_id]["country"],
                "ben": ben_info["name"],
                "ben_country": net.graph.nodes[ben_id]["country"],
                "amount": amount,
                "date": timing.date().isoformat(),
                syn.FRAUD_COL_NAME: False,
            })

        if debug:
            ic(subtotal)
