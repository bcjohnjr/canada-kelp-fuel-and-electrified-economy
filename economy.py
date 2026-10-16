"""Canadian transport-fuel volumes, prices, taxes and the oil-and-gas fiscal and profit baselines (CAD 2026).

Volumes (2025)
  Statistics Canada, End use of refined petroleum products, 2024 (The Daily, 7 Nov 2025): sales to end users of
    motor gasoline 43.7, diesel fuel oil 29.6 and aviation turbo fuel 8.7 million m3; grown to 2025 with the
    domestic-sales changes in "Another record year of production for refined petroleum in 2025" (gasoline +2.7%,
    distillate +2.2%, jet +8.0%).
  Statistics Canada, Motor vehicle fuel sales, 2025 (The Daily, 2 Oct 2026): net road diesel 17.9 billion litres.
  NRCan Comprehensive Energy Use Database, transportation, 2023: rail 88.0 PJ (2.2 GL diesel), marine 62.3 PJ
    (heavy fuel oil 27.3 PJ, the rest diesel), propane 12.4 PJ, natural gas 4.4 PJ.
  Diesel not used on roads, rails or ships is split between off-road machinery (agriculture, construction,
    mining, forestry, oil and gas field work; 7.0 GL, transport scope) and stationary uses (heating, remote
    power, industrial boilers; 2.25 GL, outside scope).
Prices
  Gasoline: September 2026 national average from Natural Resources Canada fuel-price data, 187.6 c/L;
    2025 average of NRCan weekly prices, 147.5 c/L.
  Diesel: NRCan national average 2 October 2026, 260.7 c/L; 2025 average 157.9 c/L.
  Jet: IATA Jet Fuel Price Monitor, latest weekly global average accessed 14 October 2026, US$190.18/bbl; 2025
    average US$90/bbl (IATA).
  Marine: marine gas oil at the pre-tax diesel price; heavy fuel oil at 0.9 x Brent per unit energy (Brent
    US$107.29/bbl on 13 October 2026; 2025 average US$69/bbl).
  Exchange rate: 1.4249 CAD/USD (October 2026 to date) and 1.398 (2025 average).
Taxes (statutory, per litre)
  Federal excise: gasoline 10 c/L, diesel and aviation fuel 4 c/L; suspended from 20 April 2026 to 31 January
    2027. Alberta's 13 c/L fuel tax is suspended from 1 October 2026 (WTI above US$90/bbl).
  Provincial fuel taxes, Quebec cap-and-trade and transit levies: national averages of the Canadian Taxpayers
    Federation Gas Tax Honesty Report 2026 (provincial excise 12.9 c/L, Quebec carbon 2.8 c/L, transit 1.4 c/L);
    sales taxes 18.5 c/L on a 166 c/L pump price (12.54% of the pre-sales-tax price).
  The federal consumer fuel charge was removed on 1 April 2025 (17.61 c/L gasoline, 21.39 c/L diesel in
    covered provinces); the 2025 averages include it for one quarter.
Oil-and-gas baselines
  Government revenue from the petroleum sector, 2019-2023 average: CAD 24.0 billion yr-1 (royalties, income taxes,
    land sales; NRCan Energy Fact Book, spring 2026; total energy sector 24.4: royalties 17.2, income taxes 6.9,
    land sales 0.4).
  Operating profit, 2025: oil and gas extraction ~CAD 36.0 billion, petroleum and coal product manufacturing
    ~CAD 13.2 billion (sums of quarterly values derived from Statistics Canada Quarterly financial statistics for
    enterprises releases); first half of 2026 at an annual rate: 57.6 and 31.0.
"""
TWH_PER_PJ = 1 / 3.6
KWH_PER_L = {"gasoline": 34.0 / 3.6, "diesel": 38.6 / 3.6, "jet": 34.7 / 3.6}
FX = {"oct2026": 1.4249, "avg2025": 1.398}
FX_COST = 1.40            # CAD per USD used to convert international cost data (2025-2026 average)

VOL_GL = {"gasoline": 43.7 * 1.027, "diesel_total": 29.6 * 1.022, "road_diesel": 17.9, "rail_diesel": 2.2,
          "marine_diesel": (62.3 - 27.3) / 38.6, "offroad_diesel": 7.0, "jet": 8.7 * 1.08}
VOL_GL["stationary_diesel"] = (VOL_GL["diesel_total"] - VOL_GL["road_diesel"] - VOL_GL["rail_diesel"]
                               - VOL_GL["marine_diesel"] - VOL_GL["offroad_diesel"])
LDV_DIESEL_SHARE = 0.10          # light-duty pick-ups and vans; remainder trucks and buses
PJ_OTHER = {"propane": 12.4, "natural_gas": 4.4, "hfo_marine": 27.3}


def demand(scope="all"):
    gl = lambda v, f: v * KWH_PER_L[f]   # GL x kWh/L = TWh
    rd = gl(VOL_GL["road_diesel"], "diesel")
    d = {"ldv_gasoline": gl(VOL_GL["gasoline"], "gasoline") + PJ_OTHER["propane"] * TWH_PER_PJ,
         "ldv_diesel": LDV_DIESEL_SHARE * rd,
         "hdv": (1 - LDV_DIESEL_SHARE) * rd + PJ_OTHER["natural_gas"] * TWH_PER_PJ,
         "rail": gl(VOL_GL["rail_diesel"], "diesel"),
         "offroad": gl(VOL_GL["offroad_diesel"], "diesel"),
         "aviation": gl(VOL_GL["jet"], "jet"),
         "shipping": gl(VOL_GL["marine_diesel"], "diesel") + PJ_OTHER["hfo_marine"] * TWH_PER_PJ}
    if scope == "domestic":
        d["aviation"] *= 0.35
    return d


SEGMENTS = ("ldv_gasoline", "ldv_diesel", "hdv", "rail", "offroad", "aviation", "shipping")
FUEL_OF = {"ldv_gasoline": "gasoline", "ldv_diesel": "diesel", "hdv": "diesel", "rail": "diesel", "offroad": "diesel",
           "aviation": "jet", "shipping": "diesel"}
CO2_T_PER_MWH = {"ldv_gasoline": 0.249, "ldv_diesel": 0.267, "hdv": 0.267, "rail": 0.267, "offroad": 0.267,
                 "aviation": 0.257, "shipping": 0.275}

# ------------------------------------------------------------------ prices and taxes (c/L unless noted)
SALES_TAX = 0.1254
RETAIL = {"oct2026": {"gasoline": 187.6, "diesel": 260.7}, "avg2025": {"gasoline": 147.5, "diesel": 157.9}}
JET_USD_BBL = {"oct2026": 190.18, "avg2025": 90.0}
BRENT_USD_BBL = {"oct2026": 107.29, "avg2025": 69.0}
AB_SHARE = {"gasoline": 0.145, "diesel": 0.22}        # Alberta share of national sales
PROV = {"gasoline": 12.9, "diesel": 13.0}
QC_CARBON = {"gasoline": 2.8, "diesel": 3.0}
TRANSIT = 1.4
FED = {"gasoline": 10.0, "diesel": 4.0, "jet": 4.0}
FUEL_CHARGE_Q1_2025 = {"gasoline": 17.61 * 0.78 * 0.25, "diesel": 21.39 * 0.78 * 0.25}
JET_DOMESTIC_SHARE, JET_PROV = 0.35, 2.5
RAIL_PROV = 3.0


def per_unit_tax(fuel, period, statutory=False):
    """Per-litre taxes (federal excise, provincial fuel tax, Quebec carbon, transit) in force in a period."""
    if fuel == "jet":
        fed = 0.0 if (period == "oct2026" and not statutory) else FED["jet"]
        return JET_DOMESTIC_SHARE * (fed + JET_PROV)
    fed = 0.0 if (period == "oct2026" and not statutory) else FED[fuel]
    prov = PROV[fuel] * (1 - AB_SHARE[fuel]) if (period == "oct2026" and not statutory) else PROV[fuel]
    t = fed + prov + QC_CARBON[fuel] + TRANSIT
    if period == "avg2025" and not statutory:
        t += FUEL_CHARGE_Q1_2025[fuel]
    return t


def pretax_cl(fuel, period):
    """Pre-tax supply price, c/L."""
    if fuel == "jet":
        return JET_USD_BBL[period] * FX[period] / 158.987 * 100
    return RETAIL[period][fuel] / (1 + SALES_TAX) - per_unit_tax(fuel, period)


def segment_prices(period):
    """Per segment (CAD/MWh of fossil energy): q = price before sales tax as paid now; t = statutory per-unit
    taxes to be kept; p = pre-tax supply price now."""
    out = {}
    for sg in SEGMENTS:
        f = FUEL_OF[sg]
        kwh = KWH_PER_L["jet" if f == "jet" else f]
        if sg in ("ldv_gasoline", "ldv_diesel", "hdv"):
            p = pretax_cl(f, period)
            q = p + per_unit_tax(f, period)
            t = per_unit_tax(f, period, statutory=True)
        elif sg in ("offroad", "rail"):
            p = pretax_cl("diesel", period)
            stat = FED["diesel"] + (RAIL_PROV if sg == "rail" else 0.0)
            now = (0.0 if period == "oct2026" else FED["diesel"]) + (RAIL_PROV if sg == "rail" else 0.0)
            q, t = p + now, stat
        elif sg == "aviation":
            p = pretax_cl("jet", period)
            q, t = p + per_unit_tax("jet", period), per_unit_tax("jet", period, statutory=True)
        else:  # shipping: MGO at pre-tax diesel price, HFO at 0.9 x Brent; no per-unit tax assumed
            mgo = pretax_cl("diesel", period) * 10 / kwh
            hfo = 0.9 * BRENT_USD_BBL[period] * FX[period] / 1.78
            w = 35.0 / 62.3
            pm = w * mgo + (1 - w) * hfo
            out[sg] = dict(p=pm, q=pm, t=0.0)
            continue
        out[sg] = dict(p=p * 10 / kwh, q=q * 10 / kwh, t=t * 10 / kwh)
    return out


# ------------------------------------------------------------------ oil-and-gas baselines (CAD bn/yr)
# Historical petroleum-sector public-revenue screen used for the fiscal-transition analysis.
# The Energy Fact Book reports about CAD 24 bn/yr for petroleum overall in the 2019-2023 average;
# about CAD 20 bn/yr is attributable to upstream oil and gas.  The upstream value is the appropriate
# retained baseline when domestic-serving refining is assumed to close or convert.
OIL_GOV = {"royalties_land": 17.6, "income_tax": 6.9, "total": 24.0, "upstream": 20.0}
OIL_PROFIT = {"avg2025": {"extraction": 36.0, "refining": 13.2}, "h1_2026": {"extraction": 57.6, "refining": 31.0}}
CIT_RATE = 0.26                  # federal 15% + typical provincial 11%
INTEREST_SHARE = 0.5             # share of the capital return paid as interest (deductible)
OIL_EXPORTS_2025 = {"crude_value_bn": 140.0, "crude_mbd": 4.3, "products_mbd": 0.40, "energy_exports_bn": 197.8,
                    "energy_imports_bn": 54.4}
OIL_GAS_EMISSIONS_2024_MT = 208.0
TRANSPORT_EMISSIONS_2024_MT = 151.0


def oil_pie(profit_year="avg2025"):
    """Pre-royalty operating surplus of oil and gas extraction and refining: royalties and land sales plus
    operating profit after royalties. Income taxes are paid out of operating profit."""
    pr = sum(OIL_PROFIT[profit_year].values())
    return dict(royalties_land=OIL_GOV["royalties_land"], operating_profit=pr, pie=OIL_GOV["royalties_land"] + pr,
                income_tax=OIL_GOV["income_tax"], government=OIL_GOV["total"])


if __name__ == "__main__":
    d = demand()
    print({k: round(v, 2) for k, v in d.items()}, round(sum(d.values()), 1), "stationary GL", round(VOL_GL["stationary_diesel"], 2))
    for per in ("oct2026", "avg2025"):
        sp = segment_prices(per)
        print(per, {k: {a: round(b, 1) for a, b in v.items()} for k, v in sp.items()})
        pool = sum((sp[k]["q"] - sp[k]["t"]) * d[k] for k in d) / 1000
        bill = sum(sp[k]["p"] * d[k] for k in d) / 1000
        tax = sum(sp[k]["t"] * d[k] for k in d) / 1000
        print(per, "pre-tax bill", round(bill, 1), "pool after statutory taxes", round(pool, 1), "statutory per-unit taxes", round(tax, 2))
    print(oil_pie(), oil_pie("h1_2026"))
