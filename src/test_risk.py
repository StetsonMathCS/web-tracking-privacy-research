
""""

def classify_risk(cookie_risk, fingerprint_detected):
    if cookie_risk == "Red":
        return "Red"
    elif cookie_risk == "Orange":
        return "Orange"
    elif cookie_risk == "Green" and fingerprint_detected:
        return "Orange"
    elif cookie_risk == "Green":
        return "Green"
    else:
        return "Unknown"


tests = [
    ("Green", False, "Green"),
    ("Green", True, "Orange"),
    ("Orange", False, "Orange"),
    ("Orange", True, "Orange"),
    ("Red", False, "Red"),
    ("Red", True, "Red"),
    ("Unknown", False, "Unknown"),
]

for cookie_risk, fingerprint_detected, expected in tests:
    actual = classify_risk(cookie_risk, fingerprint_detected)
    assert actual == expected, (
        f"Expected {expected}, got {actual}"
    )
    print(f"PASS: {cookie_risk}, fingerprint={fingerprint_detected} -> {actual}")

print("\nAll classification tests passed!")

"""