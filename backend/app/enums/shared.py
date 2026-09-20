from enum import StrEnum

class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class Specialty(StrEnum):
    PHYSIOTHERAPY = "physiotherapy"
    CHIROPRACTIC = "chiropractic"
    OSTEOPATHY = "osteopathy"
    MASSAGE = "massage"
    ACUPUNCTURE = "acupuncture"
    ORTHO = "ortho"
    NEURO = "neuro"
    CARDIOPULM = "cardiopulm"
    SPORTS = "sports"
    PAEDS = "paeds"
    GENERAL = "general"
    OTHER = "other"
