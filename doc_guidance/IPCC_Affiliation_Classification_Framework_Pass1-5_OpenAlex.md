# IPCC Affiliation Classification Framework (Passes 1–4)

## Overview

This document describes a four-pass workflow for classifying and normalizing institutional affiliations for IPCC bibliometric analyses.

---

# Pass 1 – Rule-based Keyword Classification

Assign affiliations to one of seven sectors:

1. Academic sector
2. Research sector
3. Government & Intergovernmental sector
4. Civil society
5. Private sector
6. Independent
7. Unknown

Use keywords such as:

- **Academic:** university, college, polytechnic, institute of technology, faculty, school
- **Research:** institute, laboratory, observatory, academy of sciences, research center
- **Government:** ministry, department, agency, authority, administration, bureau, commission
- **Civil society:** foundation, association, society, network, alliance, federation
- **Private:** Ltd, Inc, LLC, GmbH, BV, Consulting, Advisors, Associates
- **Independent:** independent researcher, consultant, freelance

---

# Pass 2 – Acronym Recognition and Priority Rules

## Common acronym lookup

Research:
- IIASA
- CNRS
- CSIRO
- PIK
- CMCC
- LSCE
- IPSL
- Deltares
- TNO
- CGIAR
- CIFOR
- IWMI
- ICIMOD
- TUBITAK

Government & Intergovernmental:
- UNEP
- UNDP
- UNESCO
- WHO
- FAO
- WMO
- OECD
- NASA
- NOAA
- IPCC TSU
- European Commission

Civil society:
- WRI
- SEI
- WWF
- ICLEI
- C40
- Climate Analytics
- Future Earth

Academic:
- MIT
- ETH Zurich
- EPFL
- TU Delft
- NUS
- NTU
- IIT
- IISc
- KAUST
- HKU
- FGV EAESP

## Priority order

1. Independent
2. Academic
3. Research
4. Government & Intergovernmental
5. Civil society
6. Private
7. Unknown

Example:
- State University → Academic
- Academy of Sciences → Research
- UN Environment Programme → Government & Intergovernmental

---

# Pass 3 – Curated Organization Dictionary

Maintain a lookup table mapping aliases to canonical names.

Example:

| Alias | Canonical organization | Sector |
|------|------------------------|--------|
| Oxford Univ. | University of Oxford | Academic |
| ETH | ETH Zurich | Academic |
| LSCE | Laboratoire des Sciences du Climat et de l’Environnement | Research |
| WRI | World Resources Institute | Civil society |

Split multiple affiliations joined by ";", "/", or "and", and classify each organization independently.

---

# Pass 4 – Entity Normalization (Recommended)

## 1. Canonical organization names

Normalize all spelling variants to one canonical institution.

Example:

- Oxford University
- University of Oxford
- Oxford Univ.

↓

University of Oxford

---

## 2. Parent–child hierarchy

Separate organizational levels.

Example:

Department of Earth Sciences

↓

Institution: University of Cambridge

Department: Earth Sciences

Similarly:

NASA Goddard Space Flight Center

↓

Parent: NASA

Subunit: Goddard Space Flight Center

---

## 3. Multi-label affiliations

Store each organization separately instead of assigning one label.

Example:

University of Oxford & Met Office

↓

- University of Oxford → Academic
- UK Met Office → Government

---

## 4. Separate Governments and IGOs

Government:
- Ministries
- National agencies
- Meteorological services

Intergovernmental:
- UNEP
- WMO
- WHO
- FAO
- UNESCO
- OECD
- World Bank
- Asian Development Bank
- IPCC TSU

---

## 5. Separate Think Tanks from NGOs

NGOs:
- WWF
- Greenpeace
- Conservation International

Think tanks:
- World Resources Institute
- Stockholm Environment Institute
- Resources for the Future

Scientific networks:
- Future Earth
- PAGES
- START
- IPBES

---

## 6. Research-performing vs Funding Organizations

Research performers:
- Universities
- National laboratories
- Research institutes

Funding organizations:
- NSF
- UKRI
- Horizon Europe
- Wellcome Trust

---

## 7. Country-aware disambiguation

Use country to resolve ambiguous acronyms.

Example:

NUS + Singapore → National University of Singapore

NUST + Pakistan → National University of Sciences and Technology

---

## 8. Confidence score

Assign confidence to every classification.

| Confidence | Method |
|------------|--------|
| 1.00 | Exact lookup |
| 0.95 | Alias |
| 0.90 | Acronym |
| 0.80 | Strong rule |
| 0.60 | Weak rule |
| <0.60 | Manual review |

Review only low-confidence records.

---

## 9. Persistent Organization IDs

Assign every canonical organization a unique identifier.

Example:

| Organization ID | Canonical name |
|----------------|----------------|
| ORG000001 | University of Oxford |
| ORG000002 | NASA |
| ORG000003 | IIASA |

---

## 10. Recommended Output Schema

| Field | Description |
|------|-------------|
| Original affiliation | Raw affiliation |
| Canonical organization | Normalized organization |
| Parent organization | Parent institution |
| Department/Subunit | Optional |
| Sector | High-level category |
| Subsector | University, Ministry, NGO, Think Tank, etc. |
| Country | Normalized country |
| Acronym | Standard acronym |
| Organization ID | Persistent identifier |
| Confidence | 0–1 |
| Classification method | Lookup, Alias, Acronym, Rule, Manual |

---

# Expected Outcome

Using all four passes should:

- Normalize institutional names across spelling variants.
- Correctly classify >95% of affiliations.
- Reduce unknown affiliations to below 5%.
- Enable reproducible institutional analyses, collaboration networks, and diversity assessments suitable for IPCC and bibliometric research.


---

# Pass 5 – External Registry Matching (OpenAlex + ROR)

To maximize reproducibility and interoperability, enrich the normalized affiliations by matching them to external organization registries.

## Recommended matching order

1. Curated internal lookup table
2. OpenAlex Institutions
3. ROR (Research Organization Registry)
4. Wikidata (fallback for governments, NGOs, and international organizations)
5. Manual review

## Why OpenAlex?

OpenAlex provides a continuously updated global registry of research institutions and includes:

- Persistent OpenAlex Institution ID
- Canonical institution name
- Alternative names and aliases
- Country
- Institution type
- Geographic coordinates
- Links to ROR, Wikidata, and other identifiers
- Publication and citation metadata

Because OpenAlex already resolves many spelling variants and aliases, it is well suited for large bibliometric datasets such as IPCC author affiliations.

Example:

| Raw affiliation | Canonical organization | OpenAlex ID |
|----------------|------------------------|-------------|
| Oxford Univ. | University of Oxford | I137902535 |
| ETH Zürich | ETH Zurich | I134323982 |
| CSIRO | Commonwealth Scientific and Industrial Research Organisation | I4210144444 |

## Additional output fields

| Field | Description |
|--------|-------------|
| OpenAlex Institution ID | Persistent institution identifier |
| ROR ID | Research Organization Registry identifier |
| Wikidata ID | Optional fallback identifier |
| Match source | Internal lookup, OpenAlex, ROR, Wikidata, Manual |
| Match confidence | Confidence score for entity resolution |

## Benefits

Using OpenAlex enables:

- Robust institution normalization across spelling variants.
- Persistent identifiers for longitudinal analyses.
- Direct integration with publication metadata and citation analyses.
- Easier comparison with other bibliometric studies.
- Improved interoperability with research infrastructure and FAIR data principles.
