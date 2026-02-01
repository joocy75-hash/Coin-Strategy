import requests

try:
    url = "http://127.0.0.1:8080/api/strategies"
    params = {"grade": "B", "limit": 10, "sort": "total_score", "order": "desc"}
    print(f"Testing {url} with {params}")
    r = requests.get(url, params=params, timeout=5)
    print(f"Status Code: {r.status_code}")
    print(f"Response Text: '{r.text}'")
    print(f"JSON: {r.json()}")
except Exception as e:
    print(f"Error: {e}")
