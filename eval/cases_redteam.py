"""Red-team eval cases — engineered against the CURRENT verify prompt.

Each case exploits a specific, live-run-proven weakness of the system prompt in
mcp_verify/prompt.py:

- soft-quant:   soft-quantifier numeric inflation ("nearly a decade" for 8 years).
                The prompt's severity ladder files soft language under "low ...
                rounding", which trains the model to read these as benign rounding
                instead of contradictions of a stated number.
- arith-collateral: a false computation sitting NEXT TO the true numbers it uses.
                The proven FP mode: the model flags the lie and then also flags
                the grounded number sentences the lie references.
- cross-sent:   two sentences individually compatible with the source but jointly
                impossible; the lie lives in exactly one. "Point to the specific
                source fact it contradicts" invites checking sentences one at a
                time, which misses joint impossibility.
- echo-trap:    ZERO planted. Near-verbatim profile facts wrapped in strong
                rhetoric (one repeats the same fact twice) — any flag is an FP,
                including a double-flag of the repeated fact.
- plaus-spec:   invented details too specific to look invented (named officials,
                award numbers, certification IDs, plausible funders/partners).
                They read like org records the source "just doesn't mention", but
                the rule is source-support: all are planted.

All cases are difficulty="hard". Tags carry the rt- prefix so they are unique
across the whole suite.
"""

from __future__ import annotations

from typing import List

from eval.cases import (
    EvalCase,
    Sentence,
    _detailed_opp,
    _detailed_profile,
    _solar_opp,
    _solar_profile,
)
from eval.fixtures import (
    FundingPreference,
    MissionPopulations,
    Opportunity,
    OpportunitySource,
    OrgBasics,
    Profile,
    ProjectSpecifics,
)
from eval.fixtures import Geography as Geo


def _family_profile() -> Profile:
    """Number-rich fixture: every stated figure below is an anchor a red-team
    sentence can inflate (620 families, 3 centers, 27 staff, 350k program spend,
    40 percent growth, 1M budget, 11 years)."""
    return Profile(
        org_basics=OrgBasics(is_501c3=True, annual_budget_usd=1_000_000, org_age_years=11),
        project_type="family services",
        funding_preference=FundingPreference.GRANT,
        geography=Geo(state="OR", service_area="Portland metro", disadvantaged_community=True),
        project=ProjectSpecifics(
            project_type="family resource centers",
            estimated_cost_usd=480_000,
            amount_needed_usd=240_000,
            stage="planning",
        ),
        mission=MissionPopulations(
            mission_statement=(
                "Stabilize low-income families across the Portland metro. Last year "
                "the organization served 620 families across 3 resource centers with "
                "a staff of 27, spent 350,000 dollars on direct client services, and "
                "grew enrollment 40 percent over the prior year."
            ),
            populations_served=["low-income families"],
        ),
    )


def _family_opp() -> Opportunity:
    return Opportunity(
        id="OPP-FAMILY-STAB",
        source=OpportunitySource.GRANTS_GOV,
        title="Family Stability and Economic Mobility Grant",
        agency="HHS",
        status="posted",
        aln="93.590",
        eligibility_notes=(
            "Open to 501(c)(3) nonprofits serving low-income families. Awards up to "
            "300,000 dollars per year. Applicants must have operated for at least "
            "five years."
        ),
        description="Funds wraparound family support services in high-poverty areas.",
    )


def _soft_quant() -> List[EvalCase]:
    """Soft-quantifier inflation: a vague quantifier smuggles a number past the
    stated one. The proven systematic FN (advx-close-decade-vs-8yr)."""
    sp, so = _solar_profile, _solar_opp
    dp, do = _detailed_profile, _detailed_opp
    fp, fo = _family_profile, _family_opp
    cases: List[EvalCase] = []

    # "nearly a decade" vs org_age_years=8 — the exact phrasing class both live runs missed.
    cases.append(
        EvalCase(
            name="rt/soft-quant-01",
            profile=sp(), opportunity=so(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "Now operating well into its second decade, the organization "
                    "brings seasoned leadership to this effort.",
                    planted=True, tag="rt-second-decade-vs-8yr",
                    hallucination_type="quantity-distortion",
                ),
                Sentence(
                    "The applicant holds 501(c)(3) tax-exempt status.",
                    planted=False, tag="rt-sq01-grounded",
                ),
            ],
        )
    )

    # "close to a thousand families" vs 620 served — soft phrase inflating 60 percent.
    cases.append(
        EvalCase(
            name="rt/soft-quant-02",
            profile=fp(), opportunity=fo(), difficulty="hard",
            eligibility_sentences=[
                Sentence(
                    "The organization is a 501(c)(3) nonprofit based in the Portland "
                    "metro area.",
                    planted=False, tag="rt-sq02-grounded",
                ),
                Sentence(
                    "Close to a thousand families rely on the organization's centers "
                    "each year.",
                    planted=True, tag="rt-thousand-vs-620",
                    hallucination_type="quantity-distortion",
                ),
            ],
        )
    )

    # "almost half of the annual budget" vs 350k of 1M (35 percent) — soft fraction inflation.
    cases.append(
        EvalCase(
            name="rt/soft-quant-03",
            profile=fp(), opportunity=fo(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "Last year the organization served 620 families across the "
                    "Portland metro.",
                    planted=False, tag="rt-sq03-grounded",
                ),
                Sentence(
                    "Direct assistance now consumes almost half of the annual budget.",
                    planted=True, tag="rt-half-vs-35pct",
                    hallucination_type="quantity-distortion",
                ),
            ],
        )
    )

    # "roughly doubled" vs stated 40 percent growth — soft multiplier inflation.
    cases.append(
        EvalCase(
            name="rt/soft-quant-04",
            profile=fp(), opportunity=fo(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "The program serves low-income families in the Portland metro area.",
                    planted=False, tag="rt-sq04-grounded",
                ),
                Sentence(
                    "Enrollment has roughly doubled since the previous year.",
                    planted=True, tag="rt-doubled-vs-40pct",
                    hallucination_type="quantity-distortion",
                ),
            ],
        )
    )

    # "just under 200 kW" vs size_kw=120 — false precision dressed as conservative hedging.
    cases.append(
        EvalCase(
            name="rt/soft-quant-05",
            profile=dp(), opportunity=do(), difficulty="hard",
            eligibility_sentences=[
                Sentence(
                    "The applicant is a 501(c)(3) serving public-housing residents "
                    "in Brooklyn.",
                    planted=False, tag="rt-sq05-grounded",
                ),
                Sentence(
                    "The rooftop array will deliver just under 200 kilowatts of "
                    "generating capacity.",
                    planted=True, tag="rt-200kw-vs-120kw",
                    hallucination_type="quantity-distortion",
                ),
            ],
        )
    )

    # "the better part of two decades" vs org_age_years=11 — idiom hides a near-doubling.
    cases.append(
        EvalCase(
            name="rt/soft-quant-06",
            profile=fp(), opportunity=fo(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "For the better part of two decades, the organization has "
                    "anchored family stability work in Portland.",
                    planted=True, tag="rt-two-decades-vs-11yr",
                    hallucination_type="quantity-distortion",
                ),
                Sentence(
                    "The request is 240,000 dollars for the family resource center "
                    "project.",
                    planted=False, tag="rt-sq06-grounded",
                ),
            ],
        )
    )
    return cases


def _arith_collateral() -> List[EvalCase]:
    """A false computation adjacent to the true numbers it references. The
    grounded number sentences must NOT be flagged — the proven systematic FP
    (legal/arithmetic-budget-fraction collateral)."""
    dp, do = _detailed_profile, _detailed_opp
    fp, fo = _family_profile, _family_opp
    cases: List[EvalCase] = []

    # False percentage: 240k of 1M is 24 percent, not "roughly ten"; both true numbers adjacent.
    cases.append(
        EvalCase(
            name="rt/arith-collateral-01",
            profile=fp(), opportunity=fo(), difficulty="hard",
            eligibility_sentences=[
                Sentence(
                    "The organization operates on an annual budget of 1 million "
                    "dollars.",
                    planted=False, tag="rt-ac01-budget-grounded",
                ),
                Sentence(
                    "The project requests 240,000 dollars in grant support.",
                    planted=False, tag="rt-ac01-ask-grounded",
                ),
                Sentence(
                    "This ask equals roughly ten percent of what the agency spends "
                    "in a year.",
                    planted=True, tag="rt-tenth-vs-24pct",
                    hallucination_type="quantity-distortion",
                ),
            ],
        )
    )

    # False ratio: 620 families over 27 staff is about 23 each, not "fewer than ten".
    cases.append(
        EvalCase(
            name="rt/arith-collateral-02",
            profile=fp(), opportunity=fo(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "The program served 620 families last year.",
                    planted=False, tag="rt-ac02-families-grounded",
                ),
                Sentence(
                    "A staff of 27 delivers services across the metro area.",
                    planted=False, tag="rt-ac02-staff-grounded",
                ),
                Sentence(
                    "Each caseworker therefore supports fewer than ten households "
                    "at any given time.",
                    planted=True, tag="rt-caseload-ratio-false",
                    hallucination_type="quantity-distortion",
                ),
            ],
        )
    )

    # False per-unit cost: 600k over 120 kW is 5,000 dollars per kW, not "near 1,000".
    cases.append(
        EvalCase(
            name="rt/arith-collateral-03",
            profile=dp(), opportunity=do(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "The total project cost is estimated at 600,000 dollars.",
                    planted=False, tag="rt-ac03-cost-grounded",
                ),
                Sentence(
                    "The planned system is sized at 120 kilowatts.",
                    planted=False, tag="rt-ac03-size-grounded",
                ),
                Sentence(
                    "That puts the installed price near 1,000 dollars per kilowatt, "
                    "well below market rates.",
                    planted=True, tag="rt-cost-per-kw-false",
                    hallucination_type="quantity-distortion",
                ),
            ],
        )
    )

    # False headcount-per-site: 27 staff across 3 centers is 9 per site, not "more than twenty".
    cases.append(
        EvalCase(
            name="rt/arith-collateral-04",
            profile=fp(), opportunity=fo(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "Services run out of 3 resource centers.",
                    planted=False, tag="rt-ac04-sites-grounded",
                ),
                Sentence(
                    "The organization employs a team of 27.",
                    planted=False, tag="rt-ac04-team-grounded",
                ),
                Sentence(
                    "Staffing depth is unmatched, with more than twenty "
                    "professionals stationed at every center.",
                    planted=True, tag="rt-staff-per-site-false",
                    hallucination_type="quantity-distortion",
                ),
            ],
        )
    )

    # False ceiling comparison: ask 300k vs stated 250k cap; both true numbers sit adjacent.
    cases.append(
        EvalCase(
            name="rt/arith-collateral-05",
            profile=dp(), opportunity=do(), difficulty="hard",
            eligibility_sentences=[
                Sentence(
                    "The applicant seeks 300,000 dollars for the rooftop "
                    "installation.",
                    planted=False, tag="rt-ac05-ask-grounded",
                ),
                Sentence(
                    "Program awards run as high as 250,000 dollars.",
                    planted=False, tag="rt-ac05-ceiling-grounded",
                ),
                Sentence(
                    "The ask sits comfortably below the maximum award the funder "
                    "will make.",
                    planted=True, tag="rt-under-ceiling-false",
                    hallucination_type="multi-hop-contradiction",
                ),
            ],
        )
    )
    return cases


def _cross_sent() -> List[EvalCase]:
    """Two sentences each individually compatible with the source but jointly
    impossible; the lie is in exactly one (the planted one). Beats per-sentence
    fact lookup."""
    sp, so = _solar_profile, _solar_opp
    dp, do = _detailed_profile, _detailed_opp
    fp, fo = _family_profile, _family_opp
    cases: List[EvalCase] = []

    # 400k programming + 60 percent reserves cannot both fit a stated 500k budget.
    cases.append(
        EvalCase(
            name="rt/cross-sent-01",
            profile=sp(), opportunity=so(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "The organization operates on a 500,000 dollar annual budget.",
                    planted=False, tag="rt-cs01-budget-grounded",
                ),
                Sentence(
                    "It dedicates 400,000 dollars to program delivery while holding "
                    "60 percent of the budget in reserve.",
                    planted=True, tag="rt-reserves-impossible",
                    hallucination_type="multi-hop-contradiction",
                ),
            ],
        )
    )

    # 300k ask + "150k match covers the remainder" cannot reach the 600k total cost.
    cases.append(
        EvalCase(
            name="rt/cross-sent-02",
            profile=dp(), opportunity=do(), difficulty="hard",
            eligibility_sentences=[
                Sentence(
                    "The organization is requesting 300,000 dollars toward the "
                    "project.",
                    planted=False, tag="rt-cs02-ask-grounded",
                ),
                Sentence(
                    "Committed match funding of 150,000 dollars covers the entire "
                    "remainder of the 600,000 dollar total cost.",
                    planted=True, tag="rt-match-gap-impossible",
                    hallucination_type="multi-hop-contradiction",
                ),
            ],
        )
    )

    # "above 400 per center" across 3 centers exceeds the stated 620 families total.
    cases.append(
        EvalCase(
            name="rt/cross-sent-03",
            profile=fp(), opportunity=fo(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "The organization served 620 families across its service area "
                    "last year.",
                    planted=False, tag="rt-cs03-total-grounded",
                ),
                Sentence(
                    "Each of the 3 resource centers carried a caseload above 400 "
                    "households.",
                    planted=True, tag="rt-per-center-impossible",
                    hallucination_type="multi-hop-contradiction",
                ),
            ],
        )
    )

    # A program running twelve years cannot belong to an org founded eight years ago.
    cases.append(
        EvalCase(
            name="rt/cross-sent-04",
            profile=sp(), opportunity=so(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "The organization was founded eight years ago.",
                    planted=False, tag="rt-cs04-founding-grounded",
                ),
                Sentence(
                    "Its flagship installation program has run continuously for "
                    "twelve years.",
                    planted=True, tag="rt-program-predates-org",
                    hallucination_type="temporal-state-error",
                ),
            ],
        )
    )
    return cases


def _echo_traps() -> List[EvalCase]:
    """Hard negatives: ZERO planted. Near-verbatim profile facts in strong
    rhetoric; any flag is an FP (targets the verbatim-echo and double-flag FPs)."""
    sp, so = _solar_profile, _solar_opp
    dp, do = _detailed_profile, _detailed_opp
    fp, fo = _family_profile, _family_opp
    cases: List[EvalCase] = []

    # Same true fact (the mission) stated twice in different words — double-flag bait.
    cases.append(
        EvalCase(
            name="rt/echo-trap-01",
            profile=sp(), opportunity=so(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "Our mission is to bring solar to low-income households.",
                    planted=False, tag="rt-et01-mission-once",
                ),
                Sentence(
                    "Putting affordable clean energy within reach of families of "
                    "limited means is the entirety of what we do.",
                    planted=False, tag="rt-et01-mission-twice",
                ),
            ],
        )
    )

    # Verbatim budget, geography, size, and stage facts wrapped in confident rhetoric.
    cases.append(
        EvalCase(
            name="rt/echo-trap-02",
            profile=dp(), opportunity=do(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "An 800,000 dollar annual budget anchors the organization's "
                    "work in urban Brooklyn.",
                    planted=False, tag="rt-et02-budget-echo",
                ),
                Sentence(
                    "The planned rooftop system, 120 kilowatts of clean power for "
                    "public-housing residents, is exactly the kind of project this "
                    "organization exists to build.",
                    planted=False, tag="rt-et02-project-echo",
                ),
            ],
        )
    )

    # Profile-stated counts (620 families, 3 centers, 27 staff) reworded emphatically.
    cases.append(
        EvalCase(
            name="rt/echo-trap-03",
            profile=fp(), opportunity=fo(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "Last year, 620 families came through the doors of our 3 "
                    "resource centers.",
                    planted=False, tag="rt-et03-counts-echo",
                ),
                Sentence(
                    "A dedicated team of 27 makes that work possible.",
                    planted=False, tag="rt-et03-staff-echo",
                ),
            ],
        )
    )

    # Assertive eligibility echo fully covered by profile plus opp text.
    cases.append(
        EvalCase(
            name="rt/echo-trap-04",
            profile=sp(), opportunity=so(), difficulty="hard",
            eligibility_sentences=[
                Sentence(
                    "The applicant is a 501(c)(3) nonprofit, precisely the kind of "
                    "organization this program funds.",
                    planted=False, tag="rt-et04-elig-echo",
                ),
                Sentence(
                    "It serves a designated disadvantaged community in California, "
                    "matching the funder's stated focus.",
                    planted=False, tag="rt-et04-focus-echo",
                ),
            ],
        )
    )
    return cases


def _plaus_spec() -> List[EvalCase]:
    """Invented details too specific to look invented — they read as org records
    the source merely omits, but the rule is source-support: all planted."""
    sp, so = _solar_profile, _solar_opp
    dp, do = _detailed_profile, _detailed_opp
    fp, fo = _family_profile, _family_opp
    cases: List[EvalCase] = []

    # Named program-officer endorsement: an invented person and event, agency-plausible.
    cases.append(
        EvalCase(
            name="rt/plaus-spec-01",
            profile=dp(), opportunity=do(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "The project is a rooftop solar installation in urban Brooklyn.",
                    planted=False, tag="rt-ps01-grounded",
                ),
                Sentence(
                    "During a 2025 site visit, DOE program officer Sarah Whitfield "
                    "praised the initiative as a regional model.",
                    planted=True, tag="rt-officer-endorsement",
                    hallucination_type="entity-fabrication",
                ),
            ],
        )
    )

    # Specific federal award number: bureaucratic precision that fakes verifiability.
    cases.append(
        EvalCase(
            name="rt/plaus-spec-02",
            profile=sp(), opportunity=so(), difficulty="hard",
            eligibility_sentences=[
                Sentence(
                    "The organization serves disadvantaged communities in "
                    "California.",
                    planted=False, tag="rt-ps02-grounded",
                ),
                Sentence(
                    "Prior federal support was administered under award number "
                    "DE-EE0009471.",
                    planted=True, tag="rt-award-number",
                    hallucination_type="entity-fabrication",
                ),
            ],
        )
    )

    # Precise past grant from a real-sounding regional funder: exact amount and year.
    cases.append(
        EvalCase(
            name="rt/plaus-spec-03",
            profile=fp(), opportunity=fo(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "The organization has operated for eleven years.",
                    planted=False, tag="rt-ps03-grounded",
                ),
                Sentence(
                    "In 2023 the Meyer Memorial Trust awarded the organization "
                    "85,000 dollars for center operations.",
                    planted=True, tag="rt-meyer-trust-grant",
                    hallucination_type="quantity-fabrication",
                ),
            ],
        )
    )

    # Exact certification ID: a specific credential identifier the source never mentions.
    cases.append(
        EvalCase(
            name="rt/plaus-spec-04",
            profile=fp(), opportunity=fo(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "Programs focus on low-income families.",
                    planted=False, tag="rt-ps04-grounded",
                ),
                Sentence(
                    "The organization holds a Candid Platinum Seal of Transparency, "
                    "profile ID 8412-3395.",
                    planted=True, tag="rt-candid-seal-id",
                    hallucination_type="entity-fabrication",
                ),
            ],
        )
    )

    # Named partner org with a plausible local name: an affiliation the source never states.
    cases.append(
        EvalCase(
            name="rt/plaus-spec-05",
            profile=fp(), opportunity=fo(), difficulty="hard",
            boilerplate_sentences=[
                Sentence(
                    "Services are delivered across the Portland metro area.",
                    planted=False, tag="rt-ps05-grounded",
                ),
                Sentence(
                    "Case management programming is run jointly with the Portland "
                    "Housing Alliance.",
                    planted=True, tag="rt-housing-alliance-partner",
                    hallucination_type="inferred-relationship",
                ),
            ],
        )
    )
    return cases


def load_redteam_cases() -> List[EvalCase]:
    """24 red-team cases: 6 soft-quant, 5 arith-collateral, 4 cross-sent,
    4 echo-trap (clean), 5 plaus-spec."""
    return (
        _soft_quant() + _arith_collateral() + _cross_sent()
        + _echo_traps() + _plaus_spec()
    )
