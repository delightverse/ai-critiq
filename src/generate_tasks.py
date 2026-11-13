"""Generate the eval tasks. Every expected answer is computed in code, never typed by hand.

Each scenario produces two tasks:
  - "correct": a fully correct explanation  -> expected verdict CORRECT
  - "error":   the same explanation with ONE realistic expert-level mistake -> expected verdict INCORRECT

Run:  python src/generate_tasks.py   (writes tasks/tasks.jsonl)
"""
import calendar
import json
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# US Federal Reserve holiday calendar (used as "New York banking days")
# --------------------------------------------------------------------------
def nth_weekday(year, month, weekday, n):
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def last_weekday(year, month, weekday):
    d = date(year, month, calendar.monthrange(year, month)[1])
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def fed_holidays(year):
    """Federal Reserve rule: a fixed-date holiday on Sunday is observed Monday;
    one on Saturday is not observed on a weekday."""
    out = {}
    fixed = {
        date(year, 1, 1): "New Year's Day",
        date(year, 6, 19): "Juneteenth",
        date(year, 7, 4): "Independence Day",
        date(year, 11, 11): "Veterans Day",
        date(year, 12, 25): "Christmas Day",
    }
    for d, name in fixed.items():
        if d.weekday() == 6:
            out[d + timedelta(days=1)] = f"{name} (observed)"
        elif d.weekday() < 5:
            out[d] = name
    out[nth_weekday(year, 1, 0, 3)] = "Martin Luther King Jr. Day"
    out[nth_weekday(year, 2, 0, 3)] = "Washington's Birthday"
    out[last_weekday(year, 5, 0)] = "Memorial Day"
    out[nth_weekday(year, 9, 0, 1)] = "Labor Day"
    out[nth_weekday(year, 10, 0, 2)] = "Columbus Day"
    out[nth_weekday(year, 11, 3, 4)] = "Thanksgiving Day"
    return out


def holiday(d):
    return fed_holidays(d.year).get(d)


def is_bd(d):
    return d.weekday() < 5 and holiday(d) is None


def fmt(d):
    return f"{d:%A}, {d:%B} {d.day}, {d.year}"


def fmt_short(d):
    return f"{d:%B} {d.day}, {d.year}"


def why_not_bd(d):
    if d.weekday() >= 5:
        return f"{fmt_short(d)} is a {d:%A}"
    return f"{fmt(d)} is {holiday(d)}, a US federal holiday when New York banks are closed"


def roll(d, step):
    skipped = []
    while not is_bd(d):
        skipped.append(d)
        d += timedelta(days=step)
    return d, skipped


def adjust(d, bdc):
    if bdc == "Following":
        return roll(d, 1)[0]
    if bdc == "Preceding":
        return roll(d, -1)[0]
    if bdc == "Modified Following":
        f = roll(d, 1)[0]
        return f if f.month == d.month else roll(d, -1)[0]
    raise ValueError(bdc)


# --------------------------------------------------------------------------
# Day counts
# --------------------------------------------------------------------------
def thirty360_bond_basis(s, e):
    """ISDA 2006 Section 4.16(f) 30/360 (Bond Basis)."""
    d1 = 30 if s.day == 31 else s.day
    d2 = 30 if (e.day == 31 and d1 > 29) else e.day
    return 360 * (e.year - s.year) + 30 * (e.month - s.month) + (d2 - d1), d1, d2


DENOM = {"ACT/360": 360, "ACT/365 Fixed": 365, "30/360 (Bond Basis)": 360}


def interest(principal, rate_pct, days, denom):
    x = Decimal(principal) * Decimal(rate_pct) / 100 * days / denom
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def money(x):
    return f"{x:,.2f}"


def rate_str(rate_pct):
    return str((Decimal(rate_pct) / 100).normalize())


# --------------------------------------------------------------------------
# Scenarios: each targets one expert-level rule interaction
# --------------------------------------------------------------------------
SCENARIOS = [
    dict(id="S1", category="business-day convention",
         title="Modified Following month-end rollback across Labor Day",
         principal=1_000_000, rate="5.00", dc="ACT/360", bdc="Modified Following", accrual="adjusted",
         start=date(2024, 2, 29), sched=date(2024, 8, 31), error="following_instead_of_mf"),
    dict(id="S2", category="accrual basis",
         title="Adjusted accrual after a Modified Following rollback",
         principal=2_000_000, rate="4.75", dc="ACT/365 Fixed", bdc="Modified Following", accrual="adjusted",
         start=date(2024, 11, 29), sched=date(2025, 5, 31), error="counted_to_unadjusted"),
    dict(id="S3", category="accrual basis",
         title="Unadjusted accrual with an adjusted payment date",
         principal=1_000_000, rate="5.00", dc="ACT/360", bdc="Modified Following", accrual="unadjusted",
         start=date(2024, 2, 29), sched=date(2024, 8, 31), error="counted_to_payment_date"),
    dict(id="S4", category="holiday calendar",
         title="Following convention over Thanksgiving",
         principal=5_000_000, rate="6.10", dc="ACT/360", bdc="Following", accrual="adjusted",
         start=date(2024, 5, 28), sched=date(2024, 11, 28), error="missed_holiday"),
    dict(id="S5", category="business-day convention",
         title="Preceding convention over Martin Luther King Jr. Day",
         principal=750_000, rate="7.25", dc="ACT/365 Fixed", bdc="Preceding", accrual="adjusted",
         start=date(2024, 10, 17), sched=date(2025, 1, 20), error="following_instead_of_preceding"),
    dict(id="S6", category="day count",
         title="Leap day inside an ACT/365 Fixed period",
         principal=2_500_000, rate="4.25", dc="ACT/365 Fixed", bdc="Modified Following", accrual="adjusted",
         start=date(2023, 11, 30), sched=date(2024, 5, 31), error="feb_28_in_leap_year"),
    dict(id="S7", category="day count",
         title="ACT/365 Fixed denominator in a leap year",
         principal=3_000_000, rate="5.50", dc="ACT/365 Fixed", bdc="Modified Following", accrual="adjusted",
         start=date(2024, 1, 31), sched=date(2024, 7, 31), error="denominator_366"),
    dict(id="S8", category="day count",
         title="30/360 Bond Basis with a February month-end date",
         principal=10_000_000, rate="3.875", dc="30/360 (Bond Basis)", bdc="Modified Following",
         accrual="unadjusted", start=date(2023, 8, 31), sched=date(2024, 2, 29), error="feb_end_as_30"),
]

ERROR_NOTES = {
    "following_instead_of_mf": "Applies plain Following and ignores Modified Following's month-end rule, which "
                               "moves the date back to the preceding business day when rolling forward changes the month.",
    "counted_to_unadjusted": "Terms say interest accrues to the adjusted payment date, but the explanation counts "
                             "days to the unadjusted scheduled date.",
    "counted_to_payment_date": "Terms say interest accrues to the unadjusted scheduled date, but the explanation "
                               "counts days only to the adjusted payment date.",
    "missed_holiday": "Treats a US federal holiday as a business day, so no adjustment is made.",
    "following_instead_of_preceding": "Rolls the date forward although the Preceding convention rolls backward.",
    "feb_28_in_leap_year": "Counts February 2024 as 28 days although 2024 is a leap year.",
    "denominator_366": "Uses 366 as the denominator in a leap year, but ACT/365 Fixed always uses 365.",
    "feb_end_as_30": "Treats February 29 as day 30. Under 30/360 Bond Basis only day 31 is adjusted; the "
                     "February month-end rule belongs to other 30/360 variants (e.g. 30E/360 ISDA).",
}


# --------------------------------------------------------------------------
# Computation (truthful or with one injected error)
# --------------------------------------------------------------------------
def compute(sc, err=None):
    sched, bdc = sc["sched"], sc["bdc"]
    if err == "following_instead_of_mf" or err == "following_instead_of_preceding":
        pay = roll(sched, 1)[0]
    elif err == "missed_holiday":
        pay = sched
    else:
        pay = adjust(sched, bdc)

    accrual_end = pay if sc["accrual"] == "adjusted" else sched
    if err == "counted_to_unadjusted":
        accrual_end = sched
    if err == "counted_to_payment_date":
        accrual_end = pay

    d1 = d2 = None
    if sc["dc"].startswith("30/360"):
        days, d1, d2 = thirty360_bond_basis(sc["start"], accrual_end)
        if err == "feb_end_as_30":
            d2 = 30
            days = 360 * (accrual_end.year - sc["start"].year) + 30 * (accrual_end.month - sc["start"].month) + (d2 - d1)
    else:
        days = (accrual_end - sc["start"]).days
        if err == "feb_28_in_leap_year":
            days -= 1

    denom = DENOM[sc["dc"]]
    if err == "denominator_366":
        denom = 366
    return dict(pay=pay, accrual_end=accrual_end, days=days, denom=denom, d1=d1, d2=d2,
                interest=interest(sc["principal"], sc["rate"], days, denom))


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
def month_breakdown(s, e, feb28=False):
    """Actual days excluding start, including end, described month by month."""
    parts = []
    y, m = s.year, s.month
    first = True
    while (y, m) <= (e.year, e.month):
        dim = calendar.monthrange(y, m)[1]
        if m == 2 and dim == 29 and feb28:
            dim = 28
        lo = s.day if first else 0
        hi = e.day if (y, m) == (e.year, e.month) else dim
        n = hi - lo
        name = calendar.month_name[m]
        if n > 0:
            if first and lo > 0:
                parts.append(f"{n} remaining {'day' if n == 1 else 'days'} in {name}")
            elif hi < dim:
                parts.append(f"{n} {'day' if n == 1 else 'days'} in {name}")
            else:
                leap = " (2024 is a leap year)" if (m == 2 and dim == 29) else ""
                parts.append(f"{name} has {dim} days{leap}")
        first = False
        m += 1
        if m == 13:
            y, m = y + 1, 1
    if len(parts) > 1:
        return ", ".join(parts[:-1]) + ", and " + parts[-1]
    return parts[0]


def render_payment_step(sc, err):
    sched, bdc = sc["sched"], sc["bdc"]
    if is_bd(sched) or err == "missed_holiday":
        return (f"First, check the scheduled payment date. {fmt(sched)} is a regular New York business "
                f"day, so no adjustment is needed under {bdc}.")
    text = (f"First, check the scheduled payment date. {why_not_bd(sched)}, so it is not a business day "
            f"and must be adjusted under {bdc}.")
    fwd, fwd_skipped = roll(sched, 1)
    back, back_skipped = roll(sched, -1)
    if bdc == "Preceding" and err != "following_instead_of_preceding":
        extra = [why_not_bd(d) for d in back_skipped[1:]]
        if extra:
            text += " Moving backward, " + "; ".join(extra) + "."
        return text + f" The preceding business day is {fmt(back)}, which becomes the payment date."
    extra = [why_not_bd(d) for d in fwd_skipped[1:]]
    if extra:
        text += " Moving forward, " + "; ".join(extra) + "."
    if bdc == "Modified Following" and err != "following_instead_of_mf" and fwd.month != sched.month:
        return text + (f" The next business day is therefore {fmt(fwd)}. However, Modified Following requires "
                       f"that if the next business day falls in a different calendar month, the date moves to the "
                       f"preceding business day instead. {fmt_short(fwd)} is in a different month, so the payment "
                       f"date is {fmt(back)}.")
    if bdc == "Modified Following" and err != "following_instead_of_mf":
        return text + f" The next business day is {fmt(fwd)}, in the same calendar month, so it becomes the payment date."
    return text + f" The first business day after the scheduled date is therefore {fmt(fwd)}, which becomes the payment date."


def render_accrual_step(sc, r, err):
    s = sc["start"]
    if err == "counted_to_unadjusted":
        lead = (f"Interest is calculated through the scheduled period end, so the accrual period runs from "
                f"{fmt_short(s)} to {fmt_short(r['accrual_end'])}.")
    elif err == "counted_to_payment_date":
        lead = (f"Interest is calculated to the payment date, so the accrual period runs from "
                f"{fmt_short(s)} to {fmt_short(r['accrual_end'])}.")
    elif sc["accrual"] == "adjusted":
        lead = (f"Because interest accrues to the adjusted payment date, the accrual period runs from "
                f"{fmt_short(s)} to {fmt_short(r['accrual_end'])}.")
    else:
        lead = (f"Because interest accrues to the unadjusted scheduled period end date, the accrual period ends on "
                f"{fmt_short(r['accrual_end'])}, regardless of when payment is made.")

    if sc["dc"].startswith("30/360"):
        e = r["accrual_end"]
        d1_note = f"D1 = {s.day}" + (" is changed to 30" if s.day == 31 else "")
        if err == "feb_end_as_30":
            d2_note = (f"D2 = {e.day}; because February 29 is the last day of the month, it is treated as day 30 "
                       f"under the 30/360 month-end rule, so D2 = 30")
        elif r["d2"] != e.day:
            d2_note = f"D2 = {e.day} is changed to 30 because D1 is 30 or more"
        else:
            d2_note = f"D2 = {e.day} stays as is, since only a D2 of 31 is adjusted (and only when D1 is 30 or more)"
        count = (f"Under 30/360 (Bond Basis), {d1_note}, and {d2_note}. Days = 360 × (Y2 − Y1) + 30 × (M2 − M1) "
                 f"+ (D2 − D1) = 360 × {e.year - s.year} + 30 × ({e.month} − {s.month}) + ({r['d2']} − {r['d1']}) "
                 f"= {r['days']} days.")
    else:
        count = (f"Counting the actual days, excluding the start date and including the end date: "
                 f"{month_breakdown(s, r['accrual_end'], feb28=(err == 'feb_28_in_leap_year'))}, "
                 f"giving {r['days']} days.")
    return lead + " " + count


def render_interest_step(sc, r, err):
    p = f"{sc['principal']:,}"
    calc = f"{p} × {rate_str(sc['rate'])} × {r['days']} / {r['denom']} = USD {money(r['interest'])}."
    if sc["dc"] == "ACT/365 Fixed":
        if err == "denominator_366":
            return ("Because the accrual period falls in 2024, a leap year, the ACT/365 Fixed denominator becomes "
                    f"366. Interest equals principal times rate times days divided by 366: {calc}")
        # Only the scenario that tests the denominator mentions leap years here, so other tasks get no hint.
        note = ", even in a leap year" if sc["error"] == "denominator_366" else ""
        return (f"Under ACT/365 Fixed, the denominator is always 365{note}. Interest equals principal "
                f"times rate times days divided by 365: {calc}")
    return f"Under {sc['dc']}, interest equals principal times rate times days divided by 360: {calc}"


def render_prompt(sc, r, err):
    accrual_term = ("Interest accrues to the adjusted payment date" if sc["accrual"] == "adjusted" else
                    "Interest accrues to the unadjusted scheduled period end date; only the payment date is adjusted")
    explanation = "\n\n".join([
        render_payment_step(sc, err),
        render_accrual_step(sc, r, err),
        render_interest_step(sc, r, err),
        f"Final answer: the payment date is {fmt(r['pay'])}, and the interest due is USD {money(r['interest'])}.",
    ])
    return f"""You are reviewing an explanation of an interest calculation. Determine whether the explanation is fully correct.

Loan terms:
- Principal: USD {sc['principal']:,}
- Fixed rate: {sc['rate']}% per year
- Day count convention: {sc['dc']}
- Business day convention: {sc['bdc']}
- Holiday calendar: US (New York banking days)
- Interest period start: {fmt(sc['start'])}
- Scheduled period end and payment date: {fmt_short(sc['sched'])}
- {accrual_term}

Question: What is the payment date, and how much interest is due on it?

Explanation:
{explanation}

Is this explanation fully correct? Give your reasoning, then end your response with exactly "VERDICT: CORRECT" or "VERDICT: INCORRECT"."""


def summary(r):
    return dict(payment_date=r["pay"].isoformat(), accrual_end=r["accrual_end"].isoformat(),
                days=r["days"], denominator=r["denom"], interest=money(r["interest"]))


def build():
    tasks = []
    for sc in SCENARIOS:
        truth = compute(sc)
        wrong = compute(sc, sc["error"])
        assert summary(truth) != summary(wrong), f"{sc['id']}: injected error changes nothing"
        for version, err, expected in [("correct", None, "CORRECT"), ("error", sc["error"], "INCORRECT")]:
            shown = truth if err is None else wrong
            tasks.append(dict(
                id=f"{sc['id']}_{version}", scenario=sc["id"], title=sc["title"], category=sc["category"],
                version=version, error_type=sc["error"] if err else None,
                error_note=ERROR_NOTES[sc["error"]] if err else None,
                expected_verdict=expected, ground_truth=summary(truth), explanation_claims=summary(shown),
                prompt=render_prompt(sc, shown, err)))
    return tasks


if __name__ == "__main__":
    tasks = build()
    out = ROOT / "tasks" / "tasks.jsonl"
    out.parent.mkdir(exist_ok=True)
    with out.open("w") as f:
        for t in tasks:
            f.write(json.dumps(t) + "\n")
    print(f"Wrote {len(tasks)} tasks to {out}")
    for t in tasks:
        print(f"  {t['id']:<12} expected={t['expected_verdict']:<9} truth={t['ground_truth']}")
