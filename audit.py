#!/usr/bin/env python3
"""Audit script to understand current state"""
import json
from pathlib import Path

# Load data
opps = json.loads(Path('backend/app/data/opportunities.json').read_text())
startups = json.loads(Path('backend/app/data/startups.json').read_text())

print(f"Opportunities: {len(opps)}")
print(f"Startups: {len(startups)}")
print()

# Check opportunities
countries = set()
industries = set()
stages = set()
goals = set()
for o in opps:
    for c in o.get('countries', []):
        countries.add(c)
    for i in o.get('targetIndustries') or []:
        industries.add(i)
    for s in o.get('targetStages') or []:
        stages.add(s)
    for g in o.get('goals', []):
        goals.add(g)

print("Opp countries:", sorted(countries))
print("Opp industries:", sorted(industries))
print("Opp stages:", sorted(stages))
print("Opp goals:", sorted(goals))
print()

# Check startups
scountries = set()
sindustries = set()
sstages = set()
strategies = set()
for s in startups:
    scountries.add(s.get('country'))
    sindustries.add(s.get('industry'))
    sstages.add(s.get('stage'))
    for st in s.get('strategyTags') or []:
        strategies.add(st)

print("Startup countries:", sorted(scountries))
print("Startup industries:", sorted(sindustries))
print("Startup stages:", sorted(sstages))
print("Startup strategies:", sorted(strategies))
