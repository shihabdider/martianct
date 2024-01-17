# MartianCT
Explore clinical trials from clinicaltrials.gov using GPT.

# Installation
1. Install all dependencies (recommend using a conda env):
`pip install -r requirements.txt`

2. Add env variables (add your OPENAI_API_KEY to .env after copying):
`cp example.env .env`
`export $(grep -v '^#' .env | xargs)`

3. Run steamlit app:
`python -m streamlit run Filter_Trials.py --server.port 1976`
