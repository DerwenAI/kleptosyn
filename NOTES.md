
## process abstraction

  1. Load entities for people in roles, with beneficiary metadata.
  2. Load entities for shell corp intermediary organizations.
  3. Load network motif patterns representing fraud tradecraft.
  4. Simulate a network plus transactions based on all of the above.
  5. Generate output data in node-link format.


## misc. requirements

  * We must describe the pathing and relations within graph data in flexible ways.
  * Formally speaking, these tradecraft patterns tend to be _walks_ or _circuits_.
  * Tradecraft motifs are not merely data queries, nor merely topological census.
  * Algebraic geometry, i.e., using an adjacency matrix, does not provide rich enough annotation.
  * We might adapt approaches from life sciences, e.g., _activity motifs_.
  * We probably don't need to delve into the topological math as far as _cohomology_.


## outstanding questions

Q: How should we represent network motifs?

  - Cypher paths subset in GraphFrames <https://github.com/Graphlet-AI/graphml-class/blob/main/graphml_class/stats/motif.py>
    - Seems ginormous and slow, with loads of dependencies?
    - GraphFrames has virtues, although we don't want to depend on this overall?
    - Could we use a pure Python Cypher parser instead?
      - Pypher <https://github.com/emehrkay/Pypher>
      - Pycypher <https://github.com/Mizzlr/pycypher>

  - Gremlin <https://tinkerpop.apache.org/docs/current/reference/#_features> provides a graph traversal language

  - SNAP <https://snap-stanford.github.io/cs224w-notes/preliminaries/motifs-and-structral-roles_lecture>
    - RoIX and other methods seem more about identifying structural roles?

  - Mermaid syntax <https://mermaid.js.org/intro/syntax-reference.html>
    - ER diagrams for many use cases, though perhaps not adaptable to network motifs?

  - DSL in DotMotif <https://github.com/aplbrain/dotmotif/wiki/Getting-Started>
    - Lacks variable-length path representation?
    - Lacks metadata on either entities or relations?


Q: Would topological methods, e.g., _sheaf theory_, provide useful formalisms for general descriptions?


Q: Can we reuse controlled vocabularies related to the data sources and use cases? 

  - FollowTheMoney <https://followthemoney.tech/explorer/>


## references

"Financial Crime and Corruption Network Motifs"  
Russell Jurney (2024-10-02)  
<https://blog.graphlet.ai/financial-crime-and-corruption-network-motifs-4cf2e8e10eb5>

"Walks, Paths, Circuits, and Cycles"  
Jennifer Shloming (2022-09-24)  
<https://jennifer_shloming.gitlab.io/intro-graph-theory/walks-paths-circuits-and-cycles.html>

"Graph Levels of Detail"  
Paco Nathan (2023-11-12)
<https://blog.derwen.ai/graph-levels-of-detail-ea4226abba55>

"Curating Grounded Synthetic Data with Global Perspectives for Equitable AI"  
Elin Törnquist, Rob Caulk (2024-06-18)  
<https://arxiv.org/abs/2406.10258>

"Cypher Manual: Patterns"  
Neo4j  
<https://neo4j.com/docs/cypher-manual/current/patterns/>

"Realistic Synthetic Graph Generation"  
Christina Eleftheriou (2024-03-04)  
<http://bit.ly/4h4qb44>

"Activity motifs reveal principles of timing in transcriptional control of the yeast metabolic network"  
Gal Chechik, et al.  (2008-11-25)
<https://pmc.ncbi.nlm.nih.gov/articles/PMC2651818/>

"DotMotif: an open-source tool for connectome subgraph isomorphism search and graph queries"  
Jordan Matelsky, et al. (2021-06-21)  
<https://www.nature.com/articles/s41598-021-91025-5>

"OFFER: A Motif Dimensional Framework for Network Representation"  
Shuo Yu, et al. (2020-08-27)  
<https://arxiv.org/abs/2008.12010>

"motifr"  
Mario Angst, Tim Seppelt (2020-12-30)
<https://marioangst.github.io/motifr/>

"3 Examples of Motifs with Spark GraphFrames"  
Steve Russo (2022-06-17)  
<https://betterprogramming.pub/3-examples-of-motifs-with-spark-graphframes-db873b3fdc8a>

"Representations of Networks"
Eric Bridgeford, et al. (2022)
<https://docs.neurodata.io/graph-stats-book/representations/ch4/network-representations.html>


## notify list

Clair Sullivan
<https://github.com/cj2001>

Brad Rees @ NVIDIA cuGraph
<https://github.com/BradReesWork>

Friedrich Lindenberg @ OpenSanctiosn
<https://github.com/pudo>

Stephen Abbott Pugh @ OpenOwnership
<https://github.com/StephenAbbott>

Zornitsa Manolova @ GLEIF
<https://github.com/GLEIF>

Russ Jurney @ Graphlet.ai
<https://github.com/rjurney>

Allison Miller
<https://www.linkedin.com/feed/update/urn:li:activity:7285305359005569024/>

Amy Hodler @ GraphGeeks.org
<https://github.com/amyhodler>

Andreas Kollegger @ Neo4j
<https://github.com/akollegger>

Jean Villedieu @ Linkurious
<https://linkurious.com/>

Alan Brown @ Aptitude Global
<https://www.aptitudeglobal.com/>
