const fetch = require('node-fetch');

async function test() {
  const res = await fetch('http://127.0.0.1:8000/analyze_text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contract_text: "LEGAL SERVICES AGREEMENT. This is a dummy agreement. Liability is capped. Termination within 30 days.",
      question: "what are the compliance terms present ??",
      run_all_agents: false
    })
  });
  console.log(res.status);
  const text = await res.text();
  console.log(text.substring(0, 1000));
}
test();
