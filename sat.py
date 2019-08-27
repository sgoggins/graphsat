#!/usr/bin/env python3
"""Functions for Satchecking CNFs, Graphs etc.

Satisfiability of CNFs
======================
A CNF is satisfiable if there exists a truth assignment for each variable in the CNF
such that on applying the assignment, the CNF evaluates to True.
This module implements three different sat-solvers:

   1. cnf_bruteforce_satcheck: a brute-force solver.
      This solver is easy to understand and reason about. It does not have other external
      dependencies. However, it is quite slow.
   2. cnf_pysat_satcheck: using the `pysat` library's Minisat22 solver.
      This solver calls Minisat v2.2 via the pysat library. It is the fast solver in this
      list but has many external dependencies (because pysat has many dependencies).
   3. cnf_minisat_satcheck: using Minisat v2.2 as a subprocess.
      This calls minisat.c directly as a subprocess. minisat.c is easy to obtain and install.
      However, creating subprocesses is not a very fast process.

Connection between CNFs and MHGraphs
====================================
For every CNF, we can construct an associated MHGraph by replacing all variables and their
negations by vertices of the same name.

Satisfiability of a MHGraph
===========================
A MHGraph is satisfiable if every CNF supported on the MHGraph is.
This module implements three different MHGraph sat-solvers:

    1. mhgraph_bruteforce_satcheck: easiest to understand and reason about.
    2. mhgraph_pysat_satcheck: fasted.
    3. mhgraph_minisat_satcheck: slowest.
"""
import itertools as it
from typing import cast, Dict, FrozenSet, Iterable, Iterator, Set, Tuple

from loguru import logger  # type: ignore
import cnf
import graph
import mhgraph


# Functions for Checking Satisfiability of CNFs
# =============================================


def generate_assignments(cnf_instance: cnf.CNF) -> Iterator[Dict[cnf.Variable, cnf.Bool]]:
    """Generate all :math:`2^n` truth-assignments for a CNF with :math:`n` Variables.

    A CNF's `truth-assignment` will be represented as a dictionary with keys being
    all the Variables that appear in the CNF and values being Bools.
    ``TRUE``/``FALSE`` CNFs are treated as having :math:`0` Variables and therefore their
    only corresponding truth-assignment is the empty dictionary.

    Args:
       cnf_instance (:obj:`cnf.CNF`)

    Return:
       First, tautologically reduce the CNF. Then, return an Iterator of truth-assignment
       dictionaries with keys being Variables and values being Bools.
    """
    cnf_reduced: cnf.CNF
    cnf_reduced = cnf.tautologically_reduce_cnf(cnf_instance)

    literal_set: FrozenSet[cnf.Literal]
    literal_set = cnf.literals_in_cnf(cnf_reduced) - {cnf.TRUE, cnf.FALSE}

    variable_set: Set[cnf.Variable]
    variable_set = set(map(cnf.variable, map(cnf.absolute_value, literal_set)))

    assignment_values: Iterator[Tuple[cnf.Bool, ...]]
    assignment_values = it.product([cnf.TRUE, cnf.FALSE], repeat=len(variable_set))

    for Boolean_tuple in assignment_values:  # pylint: disable=invalid-name
        yield dict(zip(variable_set, Boolean_tuple))


def cnf_bruteforce_satcheck(cnf_instance: cnf.CNF) -> bool:
    """Use brute force to check satisfiability of CNF.

    .. note::
       Brute-forcing is the most sub-optimal strategy possible. Do not use this function
       on large CNFs. (Anything more than 6 Variables or 6 Clauses is large.)

    Args:
       cnf_instance (:obj:`cnf.CNF`)

    Return:
       First, tautologically reduce the CNF. Then. if the CNF is Satisfiable return
       ``True`` else return ``False``.
    """
    cnf_reduced: cnf.CNF
    cnf_reduced = cnf.tautologically_reduce_cnf(cnf_instance)

    if cnf_reduced == cnf.TRUE_CNF:
        return True
    if cnf_reduced == cnf.FALSE_CNF:
        return False

    def simplifies_cnf_to_TRUE(assignment: Dict[cnf.Variable, cnf.Bool]) -> bool:  # noqa, pylint: disable=invalid-name
        return cnf.assign(cnf_reduced, assignment) == cnf.TRUE_CNF

    satisfying_assignments: Iterator[Dict[cnf.Variable, cnf.Bool]]
    satisfying_assignments = filter(simplifies_cnf_to_TRUE, generate_assignments(cnf_reduced))

    return any(satisfying_assignments)


def cnf_pysat_satcheck(cnf_instance: cnf.CNF) -> bool:
    """Use the `pysat` library's Minisat22 solver to sat-check a CNF.

    Args:
       cnf_instance (:obj:`cnf.CNF`)

    Return:
       If the CNF is Satisfiable return ``True`` else return ``False``.
    """
    from pysat.solvers import Minisat22  # type: ignore

    try:
        return cast(bool, Minisat22(cnf_instance).solve())
    except ValueError:
        # The CNF was probably not in reduced form.
        # Reduce and try again
        cnf_reduced: cnf.CNF
        cnf_reduced = cnf.tautologically_reduce_cnf(cnf_instance)

        if cnf_reduced == cnf.TRUE_CNF:
            return True
        if cnf_reduced == cnf.FALSE_CNF:
            return False
        return cast(bool, Minisat22(cnf_reduced).solve())


def cnf_to_dimacs(cnf_instance: cnf.CNF) -> str:
    """Convert a CNF to DIMACS format.

    The CNF is tautologically reduced first so as to not contain TRUE or FALSE literals.
    Args:
       cnf_instance (:obj:`cnf.CNF`)

    Return:
       A string which consists of lines. Each line is a Clause of the CNF ending with zero.
       Each literal in the Clause is written with a space delimiter.

       After tautological reduction, if the CNF reduced to TRUE or FALSE then return a
       string that will be correctly interpreted as such.
    """
    cnf_reduced: cnf.CNF
    cnf_reduced = cnf.tautologically_reduce_cnf(cnf_instance)

    if cnf_reduced == cnf.TRUE_CNF:
        return ''  # A Clause that is always satisfied
    if cnf_reduced == cnf.FALSE_CNF:
        return '0'  # A Clause that can never be satisfied

    clause_strs: Iterator[Iterator[str]]
    clause_strs = map(lambda clause: map(str, clause), cnf_reduced)

    clause_strs_with_tails: Iterator[str]
    clause_strs_with_tails = map(lambda clause_str: ' '.join(clause_str) + ' 0', clause_strs)

    return '\n'.join(clause_strs_with_tails)


def cnf_minisat_satcheck(cnf_instance: cnf.CNF) -> bool:
    """Use the `subprocess` library to call minisat.c solver to sat-check a CNF.

    minisat.c should be correctly installed for this to work.

    Args:
       cnf_instance (:obj:`cnf.CNF`)

    Return:
       If the CNF is Satisfiable return ``True`` else return ``False``.
    """
    import subprocess
    cnf_dimacs: str
    cnf_dimacs = cnf_to_dimacs(cnf_instance)

    output: str = subprocess.run(['minisat', '-rnd-init', '-verb=0'],
                                 input=cnf_dimacs,
                                 text=True,
                                 capture_output=True,
                                 shell=True).stdout

    result: str = output.split()[-1]
    if result == 'SATISFIABLE':
        return True
    if result == 'UNSATISFIABLE':
        return False
    raise RuntimeError('Unexpected output from minisat.', output)


# Functions for generating CNFs from MHGraphs
# ===========================================


def literals_from_vertex(vertex: graph.Vertex) -> Tuple[cnf.Literal, cnf.Literal]:
    """Return a Literal as well as its negation from a Vertex.

    Args:
       vertex (:obj:`graph.Vertex`)

    Returns:
       ``vertex`` and ``cnf.neg(vertex)`` after casting each to cnf.Literal.

    """
    positive_literal: cnf.Literal = cnf.literal(vertex)
    return positive_literal, cnf.neg(positive_literal)


def clauses_from_hedge(hedge: mhgraph.HEdge) -> Iterator[cnf.Clause]:
    r"""Return all Clauses supported on a HEdge.

    Args:
       hedge (:obj:`mhgraph.HEdge`)

    Return:
       An iterator of cnf.Clause consisting of the :math:`2^{|\texttt{hedge}|}` Clauses
       that are supported on ``hedge``.
    """
    literals_positive_and_negative: Iterator[Tuple[cnf.Literal, cnf.Literal]]
    literals_positive_and_negative = map(literals_from_vertex, hedge)

    literal_combinations: Iterator[Tuple[cnf.Literal, ...]]
    literal_combinations = it.product(*literals_positive_and_negative)

    return map(cnf.clause, literal_combinations)


def cnfs_from_hedge(hedge: mhgraph.HEdge, multiplicity: int) -> Iterator[cnf.CNF]:
    r"""Return all CNFs supported on a HEdge with multiplicity.

    Args:
       hedge (:obj:`mhgraph.HEdge`)
       multiplicity (:obj:`int`): an integer in the range :math:`\{1, \ldots, 2^{|hedge|}\}`.

    Returns:
       An iterator of cnf.CNF consisting of the :math:`\binom{2^{|hedge|}}{multiplicity}`
       CNFs supported on a HEdge ``hedge`` with multiplicity ``multiplicity``.

    Raises:
       ValueError: If ``multiplicity`` is not within the range :math:`\{1, \ldots,
          2^{|hedge|}\}`.

    """
    if not (1 <= multiplicity <= 2**len(hedge)):  # pylint: disable=superfluous-parens
        raise ValueError('Multiplicity value not within permissible range.')

    clause_possibilities: Iterator[cnf.Clause]
    clause_possibilities = clauses_from_hedge(hedge)

    clause_tuples: Iterable[Tuple[cnf.Clause, ...]]
    clause_tuples = it.combinations(clause_possibilities, r=multiplicity)

    return map(cnf.cnf, clause_tuples)


def cnfs_from_mhgraph(mhgraph_instance: mhgraph.MHGraph) -> Iterator[cnf.CNF]:
    r"""Return all CNFs supported on a MHGraph.

    Args:
       mhgraph_instance (:obj:`mhgraph.MHGraph`)

    Returns:
       An iterator of cnf.CNF consisting of the
       :math:`\displaystyle\prod_{hedge}\binom{2^{|hedge|}}{multiplicity}` CNFs supported
       on the MHGraph ``mhgraph_instance``.

    """
    cnf_iterators: Iterator[Iterator[cnf.CNF]]
    cnf_iterators = it.starmap(cnfs_from_hedge, mhgraph_instance.items())

    cnf_tuples: Iterator[Tuple[cnf.CNF, ...]]  # <: Iterator[Tuple[FrozenSet[cnf.Clause], ...]]
    cnf_tuples = it.product(*cnf_iterators)

    clause_frozensets: Iterator[FrozenSet[cnf.Clause]]
    clause_frozensets = it.starmap(frozenset.union, cnf_tuples)

    return map(cnf.cnf, clause_frozensets)


# Functions for Checking Satisfiability of MHGraphs
# =================================================


def mhgraph_bruteforce_satcheck(mhgraph_instance: mhgraph.MHGraph) -> bool:
    """Use brute-force to check satisfiability of a MHGraph.

    .. note::
       Brute-forcing is the most sub-optimal strategy possible. Do not use this function
       on large MHGraphs. (Anything more than 6 Vertices or 6 HEdges is large.)

    Args:
       mhgraph_instance (:obj:`mhgraph.MHGraph`)

    Return:
       ``True`` if ``mhgraph_instance`` is satisfiable, else return ``False``.
    """
    return all(map(cnf_bruteforce_satcheck, cnfs_from_mhgraph(mhgraph_instance)))


def mhgraph_pysat_satcheck(mhgraph_instance: mhgraph.MHGraph) -> bool:
    """Use the `pysat` library's Minisat22 solver to check satisfiability of a MHGraph.

    Args:
       mhgraph_instance (:obj:`mhgraph.MHGraph`)

    Return:
       ``True`` if ``mhgraph_instance`` is satisfiable, else return ``False``.
    """
    return all(map(cnf_pysat_satcheck, cnfs_from_mhgraph(mhgraph_instance)))


def mhgraph_minisat_satcheck(mhgraph_instance: mhgraph.MHGraph) -> bool:
    """Use the `subprocess` library to launch `minisat.c` and sat-check a MHGraph.

    Args:
       mhgraph_instance (:obj:`mhgraph.MHGraph`)

    Return:
       ``True`` if ``mhgraph_instance`` is satisfiable, else return ``False``.
    """
    return all(map(cnf_minisat_satcheck, cnfs_from_mhgraph(mhgraph_instance)))


# Function for generating MHGraphs from CNFs
# ==========================================


def mhgraph_from_cnf(cnf_instance: cnf.CNF) -> mhgraph.MHGraph:
    """Return the MHGraph that supports a given CNF.

    This function first tautologically reduces the CNF using
    :obj:`cnf.tautologically_reduce_cnf()`.
    This ensures no self-loops or collapsed HEdges in the final MHGraph.

    Args:
       cnf_instance (:obj:`cnf.CNF`): a CNF that does not tautologically reduce to
          ``cnf.cnf([[cnf.TRUE]])`` or ``cnf.cnf([[cnf.FALSE]])``.

    Return:
       The MHGraph that supports ``cnf_instance``.

    Raises:
       ValueError: If ``cnf_instance`` is trivially `True` or trivially `False` after
          performing tautological reductions.

    """
    reduced_cnf: cnf.CNF = cnf.tautologically_reduce_cnf(cnf_instance)

    if reduced_cnf in {cnf.TRUE_CNF, cnf.FALSE_CNF}:
        raise ValueError('CNF reduced to trivial True/False and has no supporting MHGraph.')

    cnf_with_abs_variables: Iterator[FrozenSet[cnf.Literal]]  # <: Iterator[Collection[int]]
    cnf_with_abs_variables = map(lambda clause: frozenset(map(cnf.absolute_value, clause)),
                                 reduced_cnf)

    return mhgraph.mhgraph(list(cnf_with_abs_variables))


if __name__ == '__main__':
    logger.info(f'Running {__file__} as a stand-alone script.')
    logger.info('We have several different sat-solvers implemented here.')
    logger.info(">>> cnf_bruteforce_satcheck(cnf.cnf([[1, 2], [-1, 2], [1, -2]]))")
    logger.success(cnf_bruteforce_satcheck(cnf.cnf([[1, 2], [-1, 2], [1, -2]])))
    logger.info('\n')
    logger.info('An example which is unsatisfiable:')
    logger.info(">>> cnf_bruteforce_satcheck(cnf.cnf([[1, 2], [1, -2], [-1, 2], [-1, -2]]))")
    logger.info(cnf_bruteforce_satcheck(cnf.cnf([[1, 2], [1, -2], [-1, 2], [-1, -2]])))
    logger.info('\n')
    logger.info('mhgraph_bruteforce_satcheck() finds all CNFs supported on a given MHGraph\n'
                + ' '*61 + 'and then sat-checks them using a brute-force sat-checker.')
    logger.info('>>> mhgraph_bruteforce_satcheck()(mhgraph.mhgraph([[1, 2], [2, 3]]))')
    logger.info(mhgraph_bruteforce_satcheck((mhgraph.mhgraph([[1, 2], [2, 3]]))))
    logger.info('The True output indicates that this MHGraph only supports satisfiable CNFs.')
    logger.info('\n')
    logger.info('Given a CNF we can also ask for its supporting MHGraph.')
    logger.info('>>> mhgraph_from_cnf(cnf.cnf([[1, -2], [2, 3, 4], [1, 2]]))')
    logger.info(mhgraph_from_cnf(cnf.cnf([[1, -2], [2, 3, 4], [1, 2]])))
