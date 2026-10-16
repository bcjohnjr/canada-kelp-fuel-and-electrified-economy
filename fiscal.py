"""Prices, taxes and corporate profit when Canadian pump prices are held constant.

Rule
  Users keep paying the same price per unit of transport energy service as now: the price per litre before sales
  tax for liquid fuels, and the same amount per kilometre for electric vehicles (electricity plus a road-use
  charge). Sales taxes (GST/HST, QST, PST) therefore raise the same revenue as now. Governments keep the full
  statutory per-unit fuel taxes (federal excise, provincial fuel taxes, Quebec cap-and-trade, transit levies), on
  renewable fuels and, through the road-use charge, on electric kilometres. What remains of the price after the
  per-unit taxes, the supply cost and the vehicle purchase premia is an economic rent. Most of it arises on electric
  kilometres and exists only if an instrument (a distance-based road-use charge, a concession fee or a regulated
  tariff) collects it; `capture` sets the share collected, the rest stays with users as lower prices.
Corporate accounts
  The supply cost from the optimiser includes a normal return on capital at the case's cost of capital. Operating
  profit before royalties (EBIT) = collected economic rent + return on capital,
  where the return on capital is the share of each levelised capital charge that is not depreciation
  (optimise.cost_items, optimise.f_ret).
Comparison with oil and gas
  The pre-royalty operating surplus of oil and gas extraction and petroleum refining is royalties and land sales
  (CAD 17.6 bn yr-1, 2019-2023 average) plus operating profit after royalties (CAD 49.2 bn in 2025; 88.6 bn at the
  first-half-2026 rate). A renewable system that earns at least this surplus can pay the same royalties, the same
  corporate income tax and the same after-tax profit.
"""
import economy as E


def pool(d, period):
    sp = E.segment_prices(period)
    return dict(pool_bn=sum((sp[k]["q"] - sp[k]["t"]) * d[k] for k in d) / 1000,
                fuel_tax_bn=sum(sp[k]["t"] * d[k] for k in d) / 1000,
                fuel_tax_now_bn=sum((sp[k]["q"] - sp[k]["p"]) * d[k] for k in d) / 1000,
                sales_tax_bn=sum(E.SALES_TAX * sp[k]["q"] * d[k] for k in ("ldv_gasoline", "ldv_diesel")) / 1000,
                fossil_pretax_bn=sum(sp[k]["p"] * d[k] for k in d) / 1000,
                user_spend_pre_sales_tax_bn=sum(sp[k]["q"] * d[k] for k in d) / 1000)


def efficiency_surplus(s, period="oct2026"):
    """Part of the economic rent created on electrified kilometres: what users of battery-electric vehicles, trucks and
    trains pay under the constant-price rule (before statutory per-unit taxes) less the cost of the electricity at its
    marginal value, its delivery and the vehicle premium. It exists only if an instrument (a distance-based road-use
    charge, a concession fee or a regulated tariff) collects it; in a competitive electricity market it stays with users."""
    import optimise as o
    sp = E.segment_prices(period)
    lam = s["marginal_cad_mwh"].get("el_direct", 0.0)
    vp = s.get("vehicle_premium_per_mwh", {})
    tot, pay, cost = 0.0, 0.0, 0.0
    for k, u in s["end_use_twh"].items():
        sg, op = k.split("|")
        car, ratio, _, extra, _ = o.OPTIONS[sg][op]
        if car != "el_direct":
            continue
        pay += u * (sp[sg]["q"] - sp[sg]["t"])
        cost += u * (ratio * (lam + extra) + vp.get(k, 0.0))
        if k == "hdv|ers":
            cost += u * s["ers"]["cad_per_mwh_diesel"]
    return dict(ev_service_twh=sum(u for k, u in s["end_use_twh"].items() if k.split("|")[0] in o.OPTIONS
                                   and o.OPTIONS[k.split("|")[0]][k.split("|")[1]][0] == "el_direct"),
                ev_payments_bn=pay / 1000, ev_cost_bn=cost / 1000, efficiency_surplus_bn=(pay - cost) / 1000)


def accounts(s, period="oct2026", profit_year="avg2025", royalty_bn=None, price_mult=1.0, capture=1.0):
    """Corporate and government accounts of the renewable system at constant (or scaled) pump prices.

    royalty_bn: resource royalty paid out of EBIT; default = the oil-and-gas royalties and land sales it replaces,
    capped at EBIT. price_mult scales the pre-sales-tax price q of every segment (1 = hold today's prices).
    capture: share of a positive economic rent that is actually collected (by suppliers, or by government through a
    distance charge or concession fee); the rest stays with users as lower prices. A negative rent is always borne
    by suppliers. The allocable economic surplus is rent + return on capital; EBIT is the captured part of it."""
    d = s["demand_twh"]
    P = pool(d, period)
    base = P["user_spend_pre_sales_tax_bn"] * price_mult - P["fuel_tax_bn"]
    rent_full = base - s["objective_bn"]
    rent = rent_full if rent_full < 0 else capture * rent_full
    ret = s["capital_return_bn"]
    ebit = rent + ret
    oil = E.oil_pie(profit_year)
    roy = min(oil["royalties_land"], max(ebit, 0.0)) if royalty_bn is None else royalty_bn
    interest = E.INTEREST_SHARE * ret
    cit = E.CIT_RATE * max(ebit - roy - interest, 0.0)
    profit = ebit - roy
    gov_resource = roy + cit
    return dict(period=period, profit_year=profit_year, price_mult=price_mult, capture=capture, **P, pool_at_price_bn=base,
                renewable_cost_bn=s["objective_bn"], rent_full_bn=rent_full, rent_bn=rent, capital_return_bn=ret,
                allocable_surplus_bn=rent_full + ret, allocable_coverage=(rent_full + ret) / oil["pie"],
                user_saving_bn=rent_full - rent, ebit_bn=ebit,
                lake_cleanup_payment_bn=s.get("lake_cleanup_payment_bn", 0.0),
                royalty_bn=roy, cit_bn=cit, operating_profit_bn=profit, after_tax_profit_bn=profit - cit,
                gov_resource_bn=gov_resource, gov_total_bn=gov_resource + P["fuel_tax_bn"] - s.get("lake_cleanup_payment_bn", 0.0),
                oil_pie_bn=oil["pie"], oil_profit_bn=oil["operating_profit"], oil_gov_bn=oil["government"],
                oil_gov_total_bn=oil["government"] + P["fuel_tax_bn"],
                pie_coverage=ebit / oil["pie"], profit_gap_bn=profit - oil["operating_profit"],
                gov_gap_bn=gov_resource - oil["government"])


def price_needed(s, period="oct2026", profit_year="avg2025", target="oil"):
    """Uniform multiplier on today's pre-sales-tax prices at which EBIT equals the oil-and-gas surplus
    (target='oil') or at which the economic rent is zero (target='breakeven': costs, normal returns and full
    statutory fuel taxes are covered)."""
    d = s["demand_twh"]
    P = pool(d, period)
    need = s["objective_bn"] + P["fuel_tax_bn"]
    if target == "oil":
        need += E.oil_pie(profit_year)["pie"] - s["capital_return_bn"]
    return need / P["user_spend_pre_sales_tax_bn"]


def pump_price(mult, period="oct2026"):
    """Retail pump prices (c/L incl. all taxes) when pre-sales-tax prices are scaled by mult and statutory
    per-unit taxes are restored."""
    out = {}
    for f in ("gasoline", "diesel"):
        q = E.pretax_cl(f, period) + E.per_unit_tax(f, period)
        out[f] = q * mult * (1 + E.SALES_TAX)
    return out


def decomposition(s, period="oct2026", profit_year="avg2025", captures=(0.0, 0.5, 1.0)):
    """Where the value of today's transport-energy spending goes under the constant-price policy, in four columns:
    consumer savings (rent left with users as lower prices), government fuel-tax and road-charge revenue (statutory
    per-unit taxes), producer return (normal return on capital inside the supply cost) and residual economic rent
    (the collected part of the rent, available for royalties, concession fees or profit). Only the last two are
    comparable with the oil-and-gas benchmark, which is the pre-royalty operating surplus of extraction and
    refining and includes activity serving exports (about 80% of crude production is exported)."""
    oil = E.oil_pie(profit_year)
    rows = []
    for c in captures:
        a = accounts(s, period, profit_year, capture=c)
        rows.append(dict(capture=c, consumer_savings_bn=a["user_saving_bn"], government_fuel_tax_bn=a["fuel_tax_bn"],
                         producer_return_bn=a["capital_return_bn"], residual_rent_bn=a["rent_bn"],
                         benchmark_share=(a["capital_return_bn"] + a["rent_bn"]) / oil["pie"]))
    return dict(rows=rows, benchmark_bn=oil["pie"], benchmark_royalties_bn=oil["royalties_land"],
                benchmark_operating_profit_bn=oil["operating_profit"], period=period)
