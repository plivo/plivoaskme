import sys
import os
from langchain.document_loaders.sitemap import SitemapLoader
from code_loader import GithubCodeLoader
from sitemapchunk_loader import SitemapChunkLoader
from vectordb import Ingestor
import settings

def ingest_docs_from_github_repos():
    """Ingest all docs."""
    repos = set()
    ingested_docs = 0
    if not settings.INGEST_GIT_REPO_URLS:
        print("No repos specified in settings.CODEBOT_GIT_REPO_URLS")
        return ingested_docs

    for repo in settings.INGEST_GIT_REPO_URLS:
        try:
            repo_url, branch = repo
            repos.add((repo_url, branch))
        except:
            print(f"Invalid repo {repo}. Format should be (repo_url, branch)")
            continue

    repos = list(repos)
    for repo_url, branch in repos:
        print(f"Loading {repo_url} with branch {branch}")
        loader = GithubCodeLoader(repo_url, branch=branch, debug=True)
        docs = loader.load()
        if docs:
            print(f"Loaded {len(docs)} documents from {repo_url}")
            ingested_docs += len(docs)
            Ingestor.ingest(settings.VECTOR_DATABASE, docs, overwrite=False)
            continue
    return ingested_docs


def ingest_docs_from_sitemaps():
    ingested_docs = 0
    if not settings.INGEST_SITEMAP_URLS:
        print("No sitemap urls specified in settings.INGEST_SITEMAP_URLS")
        return ingested_docs
    try:
        filter_urls = settings.INGEST_SITEMAP_URLS_FILTERS
    except:
        print("No filters specified in settings.INGEST_SITEMAP_URLS_FILTERS")
        filter_urls = None 

    print(f"Loading sitemaps from {settings.INGEST_SITEMAP_URLS}")
    for sitemap_url in settings.INGEST_SITEMAP_URLS:
        print(f"Loading {sitemap_url} START")
        loader = SitemapChunkLoader(web_path=sitemap_url, 
                                    filter_urls=filter_urls,
                                    )
        while True:
            docs = loader.load_chunks(chunk_size=200)
            if len(docs) > 0:
                print(f"Loaded {len(docs)} documents from {sitemap_url}")
                ingested_docs += len(docs)
                Ingestor.ingest(settings.VECTOR_DATABASE, docs, overwrite=False, ingest_size=200)
                continue
            print(f"Loading {sitemap_url} NO MORE DOCUMENTS TO LOAD")
            break
        print(f"Loading {sitemap_url} DONE")
    return ingested_docs


def ingest_all_docs():
    """Ingest all docs."""
    ingested_docs = ingest_docs_from_github_repos() 
    ingested_docs += ingest_docs_from_sitemaps()
    print(f"Ingested total {ingested_docs} documents")


if __name__ == "__main__":
    if not settings.OPENAI_API_KEY:
        print("OPENAI_API_KEY not set")
        sys.exit(1)
    if not settings.VECTOR_DATABASE:
        print("VECTOR_DATABASE not set")
        sys.exit(1)
    if os.path.exists(settings.VECTOR_DATABASE):
        print(f"Database {settings.VECTOR_DATABASE} already exists. Delete it first if you want to re-ingest")
        sys.exit(1)
    ingest_all_docs()

