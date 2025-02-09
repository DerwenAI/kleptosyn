#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

see copyright/license <https://github.com/DerwenAI/kleptosyn/blob/main/LICENSE>
"""

from kleptosyn import Network, Simulation, SynData


######################################################################
## main entry point

if __name__ == "__main__":
    config: dict = {}

    sim: Simulation = Simulation(config)
    net: Network = Network(config)
    syn: SynData = SynData(config)

    net.load()
    net.dump()

    #net.report()
    #sys.exit(0)

    sim.simulate(net, syn)
    syn.dump()
