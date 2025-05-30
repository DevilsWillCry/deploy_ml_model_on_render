data = {
    "name": {"first": "John", "last": "Doe"},
    "age": {"years": 30, "months": 6},
    "city": {"city": "New York", "state": "NY"}
    }

for key, value in data.items():
    print(key)
    for subkey, subvalue in value.items():
        print(f"  {subkey}: {subvalue}")
