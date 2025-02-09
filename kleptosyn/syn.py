#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Synthetic data generation.

see copyright/license <https://github.com/DerwenAI/kleptosyn/blob/main/LICENSE>
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

    def __init__ (
        self,
        config: dict,
        ) -> None:
        """
Constructor.
        """
        self.config: dict = config
        self.xact: typing.List[ dict ] = []


    def add_transact (
        self,
        transact: dict,
        ) -> None:
        """
Add a transaction to the results.
        """
        self.xact.append(transact)


    def dump (
        self,
        *,
        xact_file: pathlib.Path = pathlib.Path("transact.csv"),
        ) -> None:
        """
Serialize the generated people, companies, and transactions.
        """
        df: pd.DataFrame = pd.DataFrame.from_dict(
            self.xact,
            orient = "columns"
        )

        ic(df.head())

        df.to_csv(
            xact_file,
            sep = "\t",
            encoding = "utf-8",
            index = False,
        )
