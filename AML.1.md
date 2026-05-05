# How to get started in money laundering


## Money Laundering

First, take a look at the [AML.2.md](AML.2.md) file which describes
some of the heuristics used by fraud analysts to spot not-so-legit
things happening during financial transactions. These heuristics help
assess whether a bank account has been used for money laundering.

In other words, this is helpful info for someone who is new to
_anti-money laundering_ (AML) or, for that matter, anyone thinking
about **becoming a money launderer**.


## Forensic accounting on leaked data with graph algorithms in `NetworkX`

While it's possible to get open data which describes companies, their
ownership, sanctions risks -- i.e., the "risk" and "link" data in an
investigative graph -- it's difficult to obtain "event" data such as
financial transactions. Generally this class of data is much too
confidential; however, in some cases transactions for large-scale
fraud have been leaked.

[Howard Wilkinson](https://www.ft.com/content/32d47fd8-c18b-11e8-8d55-54197280d3f7)
was the whistleblower in a massive-scale money laundering case at
the Estonia branch of Danske Bank.
Wilkinson noticed bank transactions with a shell company named
"Lantana Trade" and the rest of the story became history.
This leak provided PDFs for 17K wire transfer records in the
[Azerbaijani Laundromat](https://www.occrp.org/en/project/the-azerbaijani-laundromat)
case.

Let's examine the `occrp.ipynb` notebook which implements several of
the heuristics mentioned above using graph algorithms for _flow
analysis_ and _forensice accounting_, developing means of classifying
the roles of shell companies.

This notebook also serves as a pretty good "cheat sheet" for how to
use `NetworkX` when you're just beginning to explore a new dataset as
a graph.


## Extra: What's missing?

Synthetic data.
But we have some bonus material, which we'll cover if we have time!

Recall that obtaining "event" data is difficult. We can't always count
on having brave whistleblowers leak data from banks involved in
sketchy business.

But we can sample from leaks, simulate the transactions of a fraud
network in operation using known patterns of criminal tradecraft, then
generate "event" data as _synthetic data_.


BTW, for more examples of this kind of approach, see
<https://github.com/IBM/AMLSim>
