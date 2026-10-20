# What this submission says, in plain language

*One page, written for the people this is actually about: the child's family, and anyone on a
care team who has not spent the week inside the mitosis literature. Everything here is stated
more precisely, with its sources, in `REPORT.md`. Where the two disagree, the report is right.*

## The short version

**We did not find a treatment. We found one existing medicine that we think is worth testing in
a laboratory dish, and we wrote down in advance what result would prove us wrong.** That
distinction is the whole submission. The hackathon asked for hypotheses for follow-up, not
evidence that a medicine works, and this is a hypothesis.

## What goes wrong in this condition

Every time a cell divides, it has to hand each daughter cell exactly one copy of each
chromosome. The cell runs a checkpoint before it commits — a pause that asks "is everything
lined up?" A protein called BubR1 is a core part of that checkpoint. This child has changes in
both copies of the gene that makes BubR1, so there is less working BubR1 than there should be.
The checkpoint becomes easy to slip past, cells divide with the wrong number of chromosomes, and
different cells end up with different wrong numbers. That is what "mosaic variegated aneuploidy"
means: patchy, varied, wrong chromosome counts.

## What we looked for, and what we found

We asked a narrow question on purpose: **is there an already-approved medicine that could push
BubR1 back up, and that would be safe to try in this particular child?** We assembled 17 entries
and put every one through the same rule. Most were ruled out, and we recorded why each one fell.

One came through, and only conditionally: **niacin**, a prescription form of vitamin B3. The
reasoning is a chain. Niacin raises a cell's level of a molecule called NAD+. NAD+ switches on an
enzyme called SIRT2. SIRT2 has been shown, in mice and in cells, to keep BubR1 from being broken
down. So raising NAD+ might raise BubR1.

## What this is not

**Nobody should start niacin because of this document.** We mean that plainly, and here is why.

- **Nobody has ever tested a NAD+-raising medicine in this condition**, in a patient or in cells
  carrying this kind of gene change. Every link in the chain above was measured in some other
  setting. Chains like that break in practice more often than they hold.
- **We do not know whether the protein this child makes is simply too scarce, or whether it is
  also broken.** If it is scarce but working, raising the amount could help. If what is there is
  broken, raising the amount cannot help, and our candidate is wrong. Nobody has measured which.
  We treat that as the pivot it is, and the first experiment is designed to answer it.
- **Niacin at the doses this idea would need is not a gentle vitamin.** In the largest randomised
  trial of this exact product, in adults, it did not help the condition it was given for and it
  caused real harm: worse blood-sugar control, more new diabetes, more infections, more bleeding.
  In the one published series of children given these doses for a different reason, most had side
  effects and about a third stopped. There is no approved paediatric labelling.
- **The tumour direction is genuinely unresolved.** The same biology that could stabilise this
  checkpoint has been argued both to protect against cancer and to help existing cancer cells.
  For a child who already has a cancer history, that is not a detail. We record it as unresolved
  rather than as reassuring, and our own screening tool prints it as a risk it could not judge.

## The honest headline

**The strongest biological idea we found has no approved medicine attached to it at all.** The
two most promising NAD+ molecules are sold as supplements rather than approved medicines, so they
are outside what this hackathon asked for, and the protein itself has no drug in development
anywhere. We report that emptiness as a result, because knowing where the cupboard is bare tells
the next researcher where to look.

## What would actually move this forward

One staged laboratory experiment, in cells from the child, in this order:

1. Does NAD+ actually rise inside the cells? If not, nothing after this means anything, and the
   problem is delivery rather than biology.
2. Does BubR1 protein rise, and does the specific chemical mark the mechanism predicts change?
3. Does the checkpoint start working again?
4. Throughout: do we count cells and follow their descendants, so that fewer wrong-count cells
   because they died is never mistaken for cells being repaired?

Stage 2 and stage 3 are worth doing even if the medicine turns out to be useless, because they
would be the first direct measurement of how this child's own checkpoint behaves.

## Questions a family could reasonably take to their own team

These are questions, not recommendations, and the answers belong to the clinicians who know the
child.

- Has anyone measured how well the checkpoint actually works in this child's cells?
- Is there a published cancer-surveillance schedule for this condition, and are we on it? (There
  is one; `SAFETY_ANNEX.md` points to it.)
- Are there medicine classes that would make the checkpoint problem worse, and does everyone
  prescribing know about them? (`SAFETY_ANNEX.md` lists the ones we could find, with sources.)
- If a research team wanted to try the experiment above, what would it take to get cells to them?

## Where to read the real thing

| If you want | Read |
|---|---|
| The full argument, with every source and every limitation | `REPORT.md` |
| What a care team should know now, independent of our candidate | `SAFETY_ANNEX.md` |
| Whether we built our screening tool to produce the answer we wanted | `ROBUSTNESS.md` |
| The one-sentence decision rule this all rests on | `PRIMARY_HYPOTHESIS.md` |

*No genomic coordinate, genotype, sample identifier or individual clinical detail appears in this
file or anywhere else in this repository.*
