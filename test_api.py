import requests

res = requests.post(
    "http://127.0.0.1:8000/analyze_text",
    json={
        "contract_text": "This is a dummy contract. Payment is due in 30 days. Late fee is 5% per month.",
        "question": "Summarize this contract and highlight key risks.",
        "run_all_agents": True
    }
)

print(res.status_code)
print(res.text)
