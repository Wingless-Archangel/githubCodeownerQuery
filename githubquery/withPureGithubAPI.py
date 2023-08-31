from datetime import datetime, timedelta
import itertools
import json
import os
from time import sleep

import requests

GITHUB_BASE_URL = "https://api.github.com"
GITHUB_PAT = os.getenv("GITHUB_PAT", "")
CODEOWNERS_DEFAULT_LOCATION = ["", ".github/", "doc/"]
GITHUB_ORG = os.getenv("GITHUB_ORG", "")

DEFAULT_HEADER = {
    "Accept": "application/vnd.github.text-match+json",
    "Authorization": f"Bearer {GITHUB_PAT}",
    "X-GitHub-Api-Version": "2022-11-28",
}
DEFAULT_PARAM = {}


def fetchOwner(header: dict, path: str, repo: str, rateLimit: int = 999) -> str:
    """
    find the CODEOWNERS file based on the CODEOWNERS_DEFAULT_LOCATION
    write the result content of code owner to file at /tmp folder.
    """
    targetFile = f"tmp/{repo}-owner.txt"

    try:
        ownerList = CODEOWNERS_DEFAULT_LOCATION
        ownerPath = ownerList.pop() + "CODEOWNERS"
        ownerURL = GITHUB_BASE_URL + f"/repos/{GITHUB_ORG}/{repo}/contents/{ownerPath}"

        if rateLimit <= 1:
            print("Hit rate limit sleep for a while!")
            sleep(5)

        with requests.session() as s:
            res = s.get(ownerURL, headers=header)
            rateLimit = int(res.headers["X-RateLimit-Remaining"])
            print(f"remaining call: {rateLimit}")

            if res.status_code != 200 and CODEOWNERS_DEFAULT_LOCATION:
                return fetchOwner(header, path, repo, rateLimit)

        with open(targetFile, "w") as f:
            f.write(res.text)

    except requests.HTTPError as err:
        raise SystemExit(err)
    except IndexError as err:
        print(f"CODEOWNERs file not found on {repo} repo")
        raise SystemExit(err)

    return res.text


def findOwner(
    header: dict,
    path: str,
    repo: str,
) -> list:
    owners = []
    team = []
    targetFile = f"tmp/{repo}-owner.txt"

    if not os.path.isfile(targetFile) or (
        datetime.fromtimestamp(os.path.getmtime(targetFile))
        < (datetime.now() - timedelta(hours=1))
    ):
        print(f"{targetFile} not found or too old. Fetch from Github.\n")
        fetchOwner(header, path, repo)

    # the path in CODEOWNERS file is not contain / at the beginning
    # which could cause the substring search not found
    fixPath = "/" + path

    with open(targetFile, "r") as f:
        if "{" in f.read():
            print(f"The {targetFile} is not what we want! Fetch from Github again.")
            fetchOwner(header, path, repo)

    with open(targetFile, "r") as f:
        for line in f:
            # skipped comment
            if "#" in line or line == os.linesep:
                continue

            ownedPath, *team = line.split()

            # handling wildcard
            if "*" in ownedPath[0]:
                owners += team

            if ownedPath in fixPath:
                owners += team

    if not owners:
        print(f"owners is {owners} for {path} path on {repo}!!!!!\n")

    return owners


def searchCode(
    url: str,
    headers: dict = DEFAULT_HEADER,
    params: dict = DEFAULT_PARAM,
    accumulator: list = [],
    rateLimit: int = 999,
) -> list:
    try:
        if rateLimit <= 1:
            print("Hit rate limit sleep for a while!")
            sleep(5)

        with requests.Session() as s:
            res = s.get(f"{url}", headers=headers, params=params, timeout=30)
            rateLimit = int(res.headers["X-RateLimit-Remaining"])

        resHeader = res.headers
        items = res.json()["items"]
        result = list(itertools.chain(accumulator, items))

        if "Link" in resHeader and 'rel="next"' in resHeader["Link"]:
            params["page"] += 1
            return searchCode(url, headers, params, result, rateLimit)

    except requests.exceptions.HTTPError as err:
        raise (err)

    return result


def main():
    searchParams = {
        "q": "org:tink-ab useSSL=true&verifyServerCertificate=false",
        "type": "code",
        "page": 1,
    }

    searchUrl = GITHUB_BASE_URL + "/search/code"
    result = searchCode(searchUrl, DEFAULT_HEADER, searchParams)

    selectField = []

    # Filter to only interested fields.
    # TODO: move this operation to function
    for item in result:
        selectField.append(
            {
                "path": item["path"],
                "repo": item["repository"]["name"],
                "text_matches": item["text_matches"],
                "url": item["html_url"],
            }
        )

    with open("tmp/tmpResult.json", "w") as f:
        json.dump(selectField, f, indent=2)

    ownerHeaders = DEFAULT_HEADER
    ownerHeaders["Accept"] = "application/vnd.github.raw"

    for item in selectField:
        owner = findOwner(ownerHeaders, item["path"], item["repo"])
        item["owner"] = owner

    with open("./Result.json", "w") as f:
        json.dump(selectField, f, indent=2)


if __name__ == "__main__":
    main()
