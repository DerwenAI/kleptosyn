#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
see copyright/license <https://github.com/DerwenAI/kleptosyn/blob/main/LICENSE>

Synthetic data generation.
"""

from datetime import datetime
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
        self.finish: datetime = datetime.now()
        self.total_fraud: float = 0.0
        self.bad_actors: typing.Set[ str ] = set()
        self.xact: typing.List[ dict ] = []


    def add_transact (
        self,
        transact: dict,
        ) -> None:
        """
Add a transaction to the results.
        """
        self.xact.append(transact)


    def add_fraud (
        self,
        last_date: datetime,
        subtotal: float,
        ubo_owner: str,
        shell_corps: typing.Set[ str ],
        ) -> None:
        """
Track one generated fraud pattern within the output data.
        """
        self.finish = max(self.finish, last_date)
        self.total_fraud += subtotal

        self.bad_actors.update([ ubo_owner ])
        self.bad_actors.update(shell_corps)


    def dump (
        self,
        *,
        xact_file: pathlib.Path = pathlib.Path("transact.csv"),
        debug: bool = True,
        ) -> None:
        """
Serialize the generated people, companies, and transactions.
        """
        df: pd.DataFrame = pd.DataFrame.from_dict(
            self.xact,
            orient = "columns"
        ).drop(
            self.FRAUD_COL_NAME,
            axis = 1,
        )

        if debug:
            ic(df.head())

        df.to_csv(
            xact_file,
            sep = "\t",
            encoding = "utf-8",
            index = False,
        )
