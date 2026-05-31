def josa_ko(name, pair):
    has_final = (ord(name[-1]) - 0xAC00) % 28 != 0
    return name + (pair[0] if has_final else pair[1])


def josa_ja(name, pair):
    return name + pair[1]


def josa_en(name, pair):
    return name + " "


JOSA = {
    "ko": josa_ko,
    "ja": josa_ja,
    "en": josa_en,
}