import random

CITIES = [
    {"key": "seoul", "name_ko": "서울", "name_en": "Seoul", "latitude": 37.57, "longitude": 126.98},
    {"key": "tokyo", "name_ko": "도쿄", "name_en": "Tokyo", "latitude": 35.68, "longitude": 139.69},
    {"key": "new_york", "name_ko": "뉴욕", "name_en": "New York", "latitude": 40.71, "longitude": -74.01},
    {"key": "london", "name_ko": "런던", "name_en": "London", "latitude": 51.51, "longitude": -0.13},
    {"key": "paris", "name_ko": "파리", "name_en": "Paris", "latitude": 48.86, "longitude": 2.35},
    {"key": "sydney", "name_ko": "시드니", "name_en": "Sydney", "latitude": -33.87, "longitude": 151.21},
    {"key": "cairo", "name_ko": "카이로", "name_en": "Cairo", "latitude": 30.04, "longitude": 31.24},
    {"key": "moscow", "name_ko": "모스크바", "name_en": "Moscow", "latitude": 55.76, "longitude": 37.62},
    {"key": "rio", "name_ko": "리우데자네이루", "name_en": "Rio de Janeiro", "latitude": -22.91, "longitude": -43.17},
    {"key": "dubai", "name_ko": "두바이", "name_en": "Dubai", "latitude": 25.20, "longitude": 55.27},
    {"key": "beijing", "name_ko": "베이징", "name_en": "Beijing", "latitude": 39.90, "longitude": 116.40},
    {"key": "bangkok", "name_ko": "방콕", "name_en": "Bangkok", "latitude": 13.76, "longitude": 100.50},
    {"key": "mumbai", "name_ko": "뭄바이", "name_en": "Mumbai", "latitude": 19.08, "longitude": 72.88},
    {"key": "singapore", "name_ko": "싱가포르", "name_en": "Singapore", "latitude": 1.35, "longitude": 103.82},
    {"key": "reykjavik", "name_ko": "레이캬비크", "name_en": "Reykjavik", "latitude": 64.15, "longitude": -21.94},
    {"key": "helsinki", "name_ko": "헬싱키", "name_en": "Helsinki", "latitude": 60.17, "longitude": 24.94},
    {"key": "toronto", "name_ko": "토론토", "name_en": "Toronto", "latitude": 43.65, "longitude": -79.38},
    {"key": "buenos_aires", "name_ko": "부에노스아이레스", "name_en": "Buenos Aires", "latitude": -34.60, "longitude": -58.38},
    {"key": "nairobi", "name_ko": "나이로비", "name_en": "Nairobi", "latitude": -1.29, "longitude": 36.82},
    {"key": "oslo", "name_ko": "오슬로", "name_en": "Oslo", "latitude": 59.91, "longitude": 10.75},
]


def random_city(rng=None):
    r = rng if rng else random
    return r.choice(CITIES)