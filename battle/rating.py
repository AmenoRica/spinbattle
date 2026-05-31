K_FACTOR = 32


def expected_score(rating_a, rating_b):
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def compute_new_ratings(rating_a, rating_b, result):
    ea = expected_score(rating_a, rating_b)
    eb = expected_score(rating_b, rating_a)
    if result == "a":
        sa, sb = 1.0, 0.0
    elif result == "b":
        sa, sb = 0.0, 1.0
    else:
        sa, sb = 0.5, 0.5
    new_a = round(rating_a + K_FACTOR * (sa - ea))
    new_b = round(rating_b + K_FACTOR * (sb - eb))
    return new_a, new_b
