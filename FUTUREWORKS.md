# Future Works

## Graph RAG
I thought graph database experience was a super specific job requirement they were looking for. I am wondering if we should use something like https://github.com/hkuds/lightrag. My only concern is that graph rag would slow down test iteration speed. Maybe it is best to start with vanilla rag, build the full thing firstm, then we can tack on graph rag once it is working. Could be a great "before and after" demo that really sells my cross-discipline experience in both data science and engineering.

## Amazon Bedrock for Production LLM Calls

The proof of concept sends book metadata to a public LLM API endpoint (OpenAI or Anthropic). That is fine for demo purposes because no student data is in the prompts. But for a real district deployment, procurement and legal teams will still ask about data residency and provider agreements.

Amazon Bedrock is the directionally right answer for production:

- LLM inference stays within AWS infrastructure; no training on customer data by default
- Bedrock supports Claude and several other foundation models behind the same API contract, so model selection stays flexible without changing the integration
- IAM-based access control integrates cleanly with whatever VPC and identity model the district already runs on AWS
- Aligns with Qvest's existing AWS practice and client familiarity with AWS enterprise agreements

Why not in the POC: Bedrock adds authentication surface area, requires an AWS account and region selection, and slows down iteration in a local demo context. Start with the direct API, ship the POC, then swap the LLM client to Bedrock when moving toward pilot infrastructure.