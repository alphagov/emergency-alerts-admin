import math

SMARTPHONE_OWNERSHIP_BY_AGE_RANGE = {
    # If no children have a phone when they’re born but 100% of
    # children have a phone by age 16 then 50% is a rough
    # approximation of how many children have phones
    (0, 15): 0.50,
    # https://www.finder.com/uk/mobile-internet-statistics
    (16, 24): 1.00,
    (25, 34): 0.97,
    (35, 44): 0.91,
    (45, 54): 0.88,
    (55, 64): 0.73,
    (65, math.inf): 0.40,
}

MEDIAN_AGE_UK = 40

for min, max in SMARTPHONE_OWNERSHIP_BY_AGE_RANGE.keys():
    if min <= MEDIAN_AGE_UK <= max:
        MEDIAN_AGE_RANGE_UK = (min, max)


class CITY_OF_LONDON:
    WARDS = (
        "E05009288",
        "E05009289",
        "E05009290",
        "E05009291",
        "E05009292",
        "E05009293",
        "E05009294",
        "E05009295",
        "E05009296",
        "E05009297",
        "E05009298",
        "E05009299",
        "E05009300",
        "E05009301",
        "E05009302",
        "E05009303",
        "E05009304",
        "E05009305",
        "E05009306",
        "E05009307",
        "E05009308",
        "E05009309",
        "E05009310",
        "E05009311",
        "E05009312",
    )
    # https://data.london.gov.uk/blog/daytime-population-of-london-2014/
    DAYTIME_POPULATION = 553_000
    # Exact area of the polygons we’re storing, which matches the 2.9km²
    # given by https://en.wikipedia.org/wiki/City_of_London
    AREA_SQUARE_METRES = 2_885_598


class BRYHER:
    WD23_CODE = "E05011090"
    POPULATION = 84


POLICE_FORCE_AREAS = {
    # Estimated by calculating the overlap with electoral wards
    "pfa23-E23000001": 5517388,  # Metropolitan Police
    "pfa23-E23000002": 354402,  # Cumbria
    "pfa23-E23000003": 1166837,  # Lancashire
    "pfa23-E23000004": 1067017,  # Merseyside
    "pfa23-E23000005": 2168460,  # Greater Manchester
    "pfa23-E23000006": 825927,  # Cheshire
    "pfa23-E23000007": 1072422,  # Northumbria
    "pfa23-E23000008": 468765,  # Durham
    "pfa23-E23000009": 623984,  # North Yorkshire
    "pfa23-E23000010": 1759386,  # West Yorkshire
    "pfa23-E23000011": 1030290,  # South Yorkshire
    "pfa23-E23000012": 679111,  # Humberside
    "pfa23-E23000013": 417438,  # Cleveland
    "pfa23-E23000014": 2195745,  # West Midlands
    "pfa23-E23000015": 867787,  # Staffordshire
    "pfa23-E23000016": 981758,  # West Mercia
    "pfa23-E23000017": 477813,  # Warwickshire
    "pfa23-E23000018": 803403,  # Derbyshire
    "pfa23-E23000019": 870605,  # Nottinghamshire
    "pfa23-E23000020": 492067,  # Lincolnshire
    "pfa23-E23000021": 845016,  # Leicestershire
    "pfa23-E23000022": 591008,  # Northamptonshire
    "pfa23-E23000023": 383211,  # Cambridgeshire
    "pfa23-E23000024": 668357,  # Norfolk
    "pfa23-E23000025": 551565,  # Suffolk
    "pfa23-E23000026": 534825,  # Bedfordshire
    "pfa23-E23000027": 853966,  # Hertfordshire
    "pfa23-E23000028": 1519509,  # Essex
    "pfa23-E23000029": 1904724,  # Thames Valley
    "pfa23-E23000030": 1488297,  # Hampshire
    "pfa23-E23000031": 915403,  # Surrey
    "pfa23-E23000032": 1359696,  # Kent
    "pfa23-E23000033": 889827,  # Sussex
    "pfa23-E23000034": 530154,  # London, City of
    "pfa23-E23000035": 1386440,  # Devon & Cornwall
    "pfa23-E23000036": 1293970,  # Avon and Somerset
    "pfa23-E23000037": 472878,  # Gloucestershire
    "pfa23-E23000038": 545357,  # Wiltshire
    "pfa23-E23000039": 558286,  # Dorset
    "pfa23-W15000001": 494828,  # North Wales
    "pfa23-W15000002": 431486,  # Gwent
    "pfa23-W15000003": 982699,  # South Wales
    "pfa23-W15000004": 374541,  # Dyfed-Powys
}


def estimate_number_of_smartphones_for_population(population):
    smartphone_ownership_for_area_by_age_range = {}

    for range, ownership in SMARTPHONE_OWNERSHIP_BY_AGE_RANGE.items():
        min, max = range
        smartphone_ownership_for_area_by_age_range[range] = (
            sum(people for age, people in population if min <= age <= max) * ownership
        )

    total_population = sum(dict(population).values())
    total_phones = sum(smartphone_ownership_for_area_by_age_range.values())

    print(f"    Population:{total_population: 11,.0f}    Phones:{total_phones: 11,.0f}")  # noqa: T201

    return total_phones
