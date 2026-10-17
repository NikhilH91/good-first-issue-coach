import os
import re
import requests
import streamlit as st
from google import genai

st.set_page_config(page_title="Good First Issue Coach", page_icon="🌱", layout="wide")

st.title("🌱 Good First Issue Coach")
st.caption("AI-powered guide to help beginners conquer their first open-source PR.")

# 1. Automatic Key Retrieval: Checks secrets/environment first, falls back to sidebar if missing
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key and "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]

github_token = os.environ.get("GITHUB_TOKEN")
if not github_token and "GITHUB_TOKEN" in st.secrets:
    github_token = st.secrets["GITHUB_TOKEN"]

# Only show sidebar if API key is not pre-configured
if not api_key:
    with st.sidebar:
        st.header("Settings")
        api_key = st.text_input("Enter Gemini API Key:", type="password")
        github_token = st.text_input("GitHub Token (Optional):", type="password")

repo_url = st.text_input(
    "Paste a public GitHub repo link:", 
    placeholder="https://github.com/pallets/flask"
)

def extract_owner_repo(url):
    # Matches github.com/owner/repo even with trailing slashes or subpages
    match = re.search(r"github\.com/([^/]+)/([^/\s?#]+)", url.strip())
    if match:
        owner = match.group(1)
        repo = match.group(2).replace(".git", "")
        return owner, repo
    return None, None

def fetch_issues(owner, repo, token=None):
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
        
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    params = {"state": "open", "per_page": 5, "sort": "updated"}
    
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code == 200:
        return [i for i in resp.json() if "pull_request" not in i]
    elif resp.status_code == 403:
        st.error("GitHub API rate limit reached. Add a GitHub Token to continue.")
    elif resp.status_code == 404:
        st.error(f"Repository '{owner}/{repo}' not found or is private.")
    return []

def analyze_issue(client, issue_title, issue_body, repo_name):
    prompt = f"""
    You are a friendly senior open-source mentor helping a first-time contributor.
    
    Repository: {repo_name}
    Issue Title: {issue_title}
    Issue Description:
    \"\"\"{issue_body or "No description provided."}\"\"\"

    Please respond with:
    1. **Plain Language Summary**: Explain the issue simply in 2-3 sentences.
    2. **Difficulty Rating**: Score 1 to 5 (1=typo/docs, 5=complex system change) and why.
    3. **Where to Look**: Likely files or directories.
    4. **Step-by-Step Action Plan**: 4-5 numbered beginner instructions.
    5. **Drafted Pull Request Body**: Ready-to-copy PR description.
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

if st.button("Find & Coach Issues", type="primary"):
    if not api_key:
        st.error("Please provide a Gemini API Key to run the coach.")
    elif not repo_url.strip():
        st.warning("Please type or paste a GitHub repository link.")
    else:
        owner, repo = extract_owner_repo(repo_url)
        if not owner or not repo:
            st.error("Please enter a full repository link, e.g., https://github.com/pallets/flask (not just a user profile).")
        else:
            with st.spinner(f"Fetching open issues from {owner}/{repo}..."):
                issues = fetch_issues(owner, repo, github_token)
            
            if issues:
                client = genai.Client(api_key=api_key)
                st.success(f"Found {len(issues)} open issues in **{owner}/{repo}**!")
                
                for idx, issue in enumerate(issues, start=1):
                    with st.expander(f"#{issue['number']}: {issue['title']}", expanded=(idx == 1)):
                        st.markdown(f"[🔗 View original issue on GitHub]({issue['html_url']})")
                        with st.spinner("Analyzing this issue..."):
                            advice = analyze_issue(client, issue['title'], issue['body'], f"{owner}/{repo}")
                            st.markdown(advice)
            elif issues == []:
                st.info("No open issues found in this repository.")