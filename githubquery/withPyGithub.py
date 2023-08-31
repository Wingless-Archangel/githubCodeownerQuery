from github import Github, Auth
import os


GITHUB_PAT = os.getenv("GITHUB_PAT", "")


def main():
    auth = Auth.Token(GITHUB_PAT)
    gh = Github(auth=auth)
    query = "org:tink-ab useSSL=true verifyServerCertificate=false"

    codeSearch = gh.search_code(query=query)

    print(f"total result is: {codeSearch.totalCount}")

    for result in codeSearch:
        print(result)


if __name__ == "__main__":
    main()
