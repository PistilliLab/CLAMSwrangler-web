import requests


def get_latest_version():
    """Fetches the latest release tag from Github repo."""
    repo_owner = 'PistilliLab'
    repo_name = 'CLAMSwrangler-web'  # Replace with your actual repo name
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest'

    response = requests.get(url)
    if response.status_code == 200:
        latest_release = response.json()
        latest_version = latest_release['tag_name']

        return latest_version

    else:
        print("Could not fetch version tag from Github.")
        return "Version unknown."
