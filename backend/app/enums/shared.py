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
    OTHER = "other"
