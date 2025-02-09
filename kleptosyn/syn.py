#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
see copyright/license <https://github.com/DerwenAI/kleptosyn/blob/main/LICENSE>

Synthetic data generation.
"""

import pathlib
import typing

from icecream import ic  # type: ignore  # pylint: disable=E0401
import pandas as pd


######################################################################
## class definitions: synthetic data results

class SynData:
    """
Synthetic data results: people, companies, transactions.
    """
    FRAUD_COL_NAME: str = "fraud"


    def __init__ (
        self,
        config: dict,
        ) -> None:
        """
Constructor.
        """
        self.config: dict = config

        self.xact: typing.List[ dict ] = []
        self.ents: typing.List[ dict ] = []


    def add_transact (
        self,
        transact: dict,
        ) -> None:
        """
Add a transaction to the results.
        """
        self.xact.append(transact)


    def add_entity (
        self,
        entity: dict,
        ) -> None:
        """
Add an entity to the results.
        """
        self.ents.append(entity)


    def dump (
        self,
        *,
        xact_file: pathlib.Path = pathlib.Path("transact.csv"),
        ents_file: pathlib.Path = pathlib.Path("entities.csv"),
        debug: bool = True,
        ) -> None:
        """
Serialize the generated people, companies, and transactions.
        """
        # serialize the transactions
        df_xact: pd.DataFrame = pd.DataFrame.from_dict(
            self.xact,
            orient = "columns"
        ).drop(
            self.FRAUD_COL_NAME,
            axis = 1,
        )

        if debug:
            ic(df_xact.head())

        df_xact.to_csv(
            xact_file,
            sep = "\t",
            encoding = "utf-8",
            index = False,
        )

        # serialize the people and companies
        df_ents: pd.DataFrame = pd.DataFrame.from_dict(
            self.ents,
            orient = "columns"
        ).drop_duplicates().sort_values(by = [ "name" ])

        if debug:
            ic(df_ents.head())

        df_ents.to_csv(
            ents_file,
            sep = "\t",
            encoding = "utf-8",
            index = False,
        )
