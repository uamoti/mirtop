import traceback
import os.path as op
import os
import re
import shutil
import pandas as pd
import pysam
from collections import defaultdict
from mirtop.mirna.realign import hits, cigar_correction
from mirtop.libs import do
from mirtop.libs.utils import file_exists
import mirtop.libs.logger as mylog

logger = mylog.getLogger(__name__)


def tune(seq, precursor, start, cigar):
    """
    The actual fn that will realign the sequence
    """
    seq, mature = cigar_correction(cigar, seq, precursor[start:])
    if seq.startswith("-"):
        seq = seq[1:]
    # print [cigar, seq, mature]
    logger.debug("Alignment: %s %s %s" % (cigar, seq, mature))
    error = set()
    pattern_addition = [[1, 1, 0], [1, 0, 1], [0, 1, 0], [0, 1, 1], [0, 0, 1], [1, 1, 1]]
    for pos in range(0, len(seq)):
        if seq[pos] != mature[pos]:
            error.add(pos)

    subs, add = [], []
    for e in error:
        if e < len(seq) - 3:
            subs.append([e, seq[e], mature[e]])

    pattern, error_add = [], []
    for e in range(len(seq) - 3, len(seq)):
        if e in error:
            pattern.append(1)
            error_add.append(e)
        else:
            pattern.append(0)
    for p in pattern_addition:
        if pattern == p:
            add = seq[error_add[0]:]
            break
    if not add and error_add:
        for e in error_add:
            subs.append([e, seq[e], mature[e]])

    return subs, add, len(mature)

def clean_hits(reads):
    """
    Select only best matches
    """
    new_reads = defaultdict(hits)
    for r in reads:
        world = {}
        sc = 0
        for p in reads[r].precursors:
            world[p] = reads[r].precursors[p].get_score(len(reads[r].sequence))
            if sc < world[p]:
                sc = world[p]
        new_reads[r] = reads[r]
        for p in world:
            logger.debug("score %s %s %s" % (r, p, world[p]))
            if sc != world[p]:
                logger.debug("remove %s %s %s" % (r, p, world[p]))
                new_reads[r].remove_precursor(p)

    return new_reads


