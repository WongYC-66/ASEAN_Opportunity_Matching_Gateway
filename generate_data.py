import json
from pathlib import Path

opps = json.loads(Path("backend/app/data/opportunities.json").read_text())
startups = json.loads(Path("backend/app/data/startups.json").read_text())

providers = ["Accelerator Hub", "Grant Council", "Corporate Ventures", "Ecosystem Fund", "Innovation Agency", "Tech Park", "Foundation", "Venture Studio"]
countries_list = [["Malaysia"], ["Singapore"], ["Indonesia"], ["Thailand"], ["Vietnam"], ["Philippines"], ["ASEAN-wide"], ["Malaysia","Singapore"], ["Thailand","Vietnam"]]
stages = [["Pre-seed"],["Seed"],["Seed","Growth"],["Pre-seed","Seed"],["Growth"],["Idea","Pre-seed"]]
industries = [["Fintech"],["Artificial Intelligence"],["Software / SaaS"],["Climate / Clean Energy"],["Healthcare"],["Education"],["Agriculture / Food"],["E-commerce / Retail"],["Logistics / Mobility"],["Manufacturing"],["Any"]]
goals_list = [["Funding"],["Mentorship"],["Funding","Mentorship"],["Market access"],["Partnership"],["Incubation & workspace","Mentorship"],["Talent & hiring"]]
cats = ["Funding","Support","Partnership"]

for i in range(12, 112):
    opps.append({
        "id": f"demo-fund-{i:02d}",
        "name": f"ASEAN Innovation Programme {i} (Demo)",
        "provider": providers[i % len(providers)],
        "category": cats[i % len(cats)],
        "description": "Demo programme supporting early-stage teams across ASEAN with resources and opportunities for growth and market expansion.",
        "countries": countries_list[i % len(countries_list)],
        "targetStages": stages[i % len(stages)],
        "targetIndustries": industries[i % len(industries)],
        "goals": goals_list[i % len(goals_list)],
        "eligibility": None,
        "applicationDeadline": None,
        "deadlineNote": None,
        "dataStatus": "demo",
        "sourceUrl": None,
        "lastVerifiedDate": None,
        "notes": "Fictional example written for the hackathon. Not a real programme, provider, deadline, or eligibility rule."
    })

names = ["Nexora","BloomTech","Arka","JalanAI","Teras","LautNet","HutanAI","KotaPay","SambalSoft","Mentari","BumiData","Cerita","Pelangi","Ruang","Zeno"]
suffixes = ["Labs","Co.","Tech","AI","Digital"]
bmodels = ["B2B SaaS subscription","Marketplace commission","Freemium with paid plans","Enterprise licence","Per-transaction fees","Platform subscription"]
rev = ["Revenue-generating","Pre-revenue"]
strats = [["Revenue-generating businesses"],["Deep technology"],["Impact / ESG"],["Market expansion"],["Early-stage growth"],["Revenue-generating businesses","Market expansion"],None]
funding = [50000,80000,100000,150000,200000,250000,300000,350000,500000,None]
curr = ["USD","MYR","SGD",None]
ind_list = ["Fintech","Artificial Intelligence","Software / SaaS","Climate / Clean Energy","Healthcare","Education","Agriculture / Food","E-commerce / Retail","Logistics / Mobility","Manufacturing"]
countries = ["Malaysia","Singapore","Indonesia","Thailand","Vietnam","Philippines"]
stages_s = ["Idea","Pre-seed","Seed","Growth / Established business","Series A"]

for i in range(8, 108):
    f = funding[i % len(funding)]
    c = curr[i % len(curr)] if f is not None else None
    startups.append({
        "id": f"demo-startup-{i+1:02d}",
        "name": f"{names[i % len(names)]} {suffixes[i % len(suffixes)]} (Demo Startup)",
        "description": f"A fictional startup building innovative solutions to address real challenges in the {ind_list[i % len(ind_list)].lower()} sector across ASEAN markets.",
        "country": countries[i % len(countries)],
        "industry": ind_list[i % len(ind_list)],
        "stage": stages_s[i % len(stages_s)],
        "businessModel": bmodels[i % len(bmodels)] if i % 3 != 0 else None,
        "revenueStatus": rev[i % len(rev)] if i % 4 != 0 else None,
        "fundingSought": f,
        "fundingCurrency": c,
        "strategyTags": strats[i % len(strats)],
        "dataStatus": "demo",
        "sourceUrl": None,
        "lastVerifiedDate": None,
        "notes": "Fictional startup written for the hackathon. Not a real company, team, metric, or investment opportunity."
    })

Path("backend/app/data/opportunities.json").write_text(json.dumps(opps, indent=2))
Path("backend/app/data/startups.json").write_text(json.dumps(startups, indent=2))
print(len(opps), len(startups))
