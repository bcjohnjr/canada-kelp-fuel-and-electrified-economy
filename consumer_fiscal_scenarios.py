"""Conditional distribution and fiscal-continuity screen for the Canadian transport optimizer.

Not a macroeconomic forecast, oil demand forecast, equilibrium model, or household income simulation.
Transparent allocations of a fixed solved system under alternative price levels.
The additional tax effects are deliberately conservative with respect to rebates:
* statutory fuel and road-use charges are not reduced;
* pre-sales-tax user rebates reduce the (proxy) sales-tax base on household light-vehicle use;
* no incremental revenue is credited from captured producer rent, oil export sales, or biofuel exports;
* petroleum fiscal receipts and exportability can be stressed separately;
* oil royalties are counted once, and an explicitly assumed shortfall in receipts is debited.
"""
import csv
import json
from pathlib import Path
import fiscal as F
import economy as E

OUT=Path(__file__).resolve().parent/'outputs'
LEVELS=(('2025 reference',0.0),('Intermediate 50/50',0.5),('October 2026 reference',1.0),('Elevated: 125% of October 2026',None))
REBATE_SHARES=(0.0,0.10,0.25,0.50,1.0)
EXPORT_FRACTIONS=(0.,.5,1.)
PETROLEUM_RECEIPT_FACTORS=(0.75,1.0,1.25)
# Not a land-user property or household forecast. Fraction of modelled user-spend associated with light vehicles.
LDV_SEGMENTS=('ldv_gasoline','ldv_diesel')


def compute(result=None,jobs=None):
    if result is None: result=json.load(open(OUT/'results.json'))['central']
    if jobs is None: jobs=json.load(open(OUT/'jobs_fiscal_balance.json'))
    a25=F.pool(result['demand_twh'],'avg2025')
    a26=F.pool(result['demand_twh'],'oct2026')
    spend25=a25['user_spend_pre_sales_tax_bn']
    spend26=a26['user_spend_pre_sales_tax_bn']
    stat_tax=a26['fuel_tax_bn']
    sp26=E.segment_prices('oct2026')
    share_ldv=sum(sp26[k]['q']*result['demand_twh'][k] for k in LDV_SEGMENTS)/sum(sp26[k]['q']*result['demand_twh'][k] for k in result['demand_twh'])
    redirect=jobs and json.load(open(OUT/'employment_fiscal.json'))['crude_redirection']['domestic_crude_redirected_mbd']
    total_crude_proxy=E.OIL_EXPORTS_2025['crude_mbd']+1.29
    redirect_prod_share=redirect/total_crude_proxy
    baseline=jobs['cases']['A_capacity_maintained']['public_revenue_status_quo_bn']
    cases=[]
    for name,w in LEVELS:
        spend=(spend25+(spend26-spend25)*w) if w is not None else 1.25*spend26
        rent=spend-stat_tax-result['objective_bn']
        for rebate_share in REBATE_SHARES:
            rebate=max(0.,rent)*rebate_share
            # Assume proportional discount over segments; proxy sales tax applies only on LDV spend.
            lost_general_sales_tax=rebate*share_ldv*E.SALES_TAX
            reserve=max(0.,-rent)  # optional public backstop to keep suppliers whole
            for refinery,basecase in jobs['cases'].items():
                for exp_frac in EXPORT_FRACTIONS:
                    for pet_factor in PETROLEUM_RECEIPT_FACTORS:
                        # A common crude-price/royalty shock affects the status quo and transition equally.
                        # Only lost tax receipts on transition-displaced crude without export buyers
                        # are incremental to the transition-versus-status-quo comparison.
                        lost_oil_receipts=E.OIL_GOV['upstream']*pet_factor*redirect_prod_share*(1-exp_frac)
                        government_delta=(basecase['net_public_revenue_bn']-lost_general_sales_tax-lost_oil_receipts-reserve)
                        cases.append(dict(price_scenario=name,spend_pre_sales_tax_bn=spend,
                            modelled_cost_bn=result['objective_bn'],statutory_transport_taxes_bn=stat_tax,
                            unallocated_rent_bn=rent,consumer_relief_fraction=rebate_share,
                            consumer_relief_bn=rebate,ldv_spending_fraction=share_ldv,
                            retail_sales_tax_reduction_bn=lost_general_sales_tax,
                            royalty_retention_factor=pet_factor,redirected_domestic_crude_exported_fraction=exp_frac,
                            upstream_receipts_stress_bn=lost_oil_receipts,
                            negative_margin_public_backstop_bn=reserve,
                            refinery_case=refinery,
                            public_revenue_status_quo_bn=baseline,
                            public_revenue_change_bn=government_delta,
                            public_revenue_after_bn=baseline+government_delta,
                            simultaneous_consumer_and_public_gain=bool(rebate>0 and government_delta>0)))
    # Internal consistency: common oil-price shifts do not create a transition effect
    # when all redirected crude finds buyers. At zero export access, only that flow matters.
    for r in cases:
        expected=E.OIL_GOV['upstream']*r['royalty_retention_factor']*redirect_prod_share*(1-r['redirected_domestic_crude_exported_fraction'])
        assert abs(r['upstream_receipts_stress_bn']-expected)<1e-10
        if r['redirected_domestic_crude_exported_fraction']==1:
            assert abs(r['upstream_receipts_stress_bn'])<1e-10
    # Additional biofuel export v. 1-year holding reserve: quantities conditional on high-yield model.
    sens=json.load(open(OUT/'kelp_productivity_export_sensitivity.json'))
    export_row=next(x for x in sens['rows'] if x.get('pacific_yield_t_dry_ha')==12 and x.get('system')=='least_cost' and x.get('export_price_cad_mwh')==400)
    qty=export_row.get('exports_twh',export_row.get('export_twh'))
    if qty is None:
        for k in export_row:
            if 'export' in k: print('EXPORT ATTR',k,export_row[k])
        raise ValueError('Export quantity field not found')
    inventory=[]
    for reserve_share in (0,.1,.25,.5):
        r=qty*reserve_share
        inventory.append(dict(hypothetical_total_biofuel_surplus_twh=qty,reserve_fraction=reserve_share,
           sales_twh=qty-r,one_year_fuel_inventory_twh=r,
           gross_revenue_foregone_bn=r*400/1000,
           annual_inventory_service_cost_bn=r*20/1000,
           premise='High-yield demonstration/market access not established. Acquisition production costs and inventory capex excluded.'))
    return dict(model='consumer/public revenue and crude-export contingency screen',
       methodology='Downstream screen; no change to optimization decisions. Price points are scenarios, not probabilities. No assumption that prices revert to 2025 or remain at October 2026 levels.',
       limitations=['Public-revenue base uses screening labour and tax ratios, not a forecast or a Canadian provincial budget.',
          'Government changes need not be realized: all key investments, activity, and taxes are modelled.',
          'No direct profit tax is imputed on the remaining modelled economic rent (which may accrue to producers, consumers, lenders, or other parties); gross exports are not fiscal receipts. An omitted profit-tax effect cannot be assumed positive without separate tax accounting.',
          'A common petroleum receipts shock affects fossil and transition baselines together; only lost receipts on redirected crude lacking foreign buyers enter the transition difference.',
          'Retail sales-tax sensitivity applies the average light-duty share and a national proxy tax rate; provincial rates vary.',
          'A price scenario with negative transport margin is assessed with a public backstop, which is optional and conservative.',
          'Inventory service costs and foregone sales are not an actual reserve acquisition budget or reliability study.',
          'Household transport savings differ by vehicle ownership, province, travel, household and government policy.',
          'This screen excludes the approximately 138 Mt CO2/year foreign combustion emissions of fully additional exported redirected crude in the fiscal balance; exporting them can reduce modelled global net avoided CO2 from 253 to 115 Mt/year.'],
       assumptions=dict(reference_fuel_tax_bn=stat_tax,ldv_spending_fraction=share_ldv,
           national_retail_sales_tax_proxy=E.SALES_TAX,upstream_petroleum_fiscal_baseline_bn=E.OIL_GOV['upstream'],
           redirected_crude_mbd=redirect,production_proxy_mbd=total_crude_proxy,
           redirected_share_of_production_proxy=redirect_prod_share,
           high_yield_surplus_biofuel_twh=qty,illustrative_export_price_cad_mwh=400,
           inventory_service_cost_cad_mwh_year=20),
       inventory=inventory,rows=cases)


def main():
    out=compute()
    with open(OUT/'consumer_fiscal_scenarios.json','w') as f:json.dump(out,f,indent=2)
    with open(OUT/'consumer_fiscal_scenarios.csv','w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(out['rows'][0]));writer.writeheader();writer.writerows(out['rows'])
    with open(OUT/'renewable_fuel_reserve_screen.csv','w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(out['inventory'][0]));writer.writeheader();writer.writerows(out['inventory'])
    print('scenarios',len(out['rows']))
    for scenario in LEVELS:
        for refinery in ('A_capacity_maintained','B_domestic_refining_closes'):
            x=next(r for r in out['rows'] if r['price_scenario']==scenario[0] and r['refinery_case']==refinery and r['consumer_relief_fraction']==0.25 and r['redirected_domestic_crude_exported_fraction']==1 and r['royalty_retention_factor']==1)
            print(f"{scenario[0]}, {refinery}: consumers {x['consumer_relief_bn']:.2f} bn; govt {x['public_revenue_change_bn']:+.2f} bn")

if __name__=='__main__':main()
