from code_loader import GithubCodeLoader

def main():
    # Get the code from the Github repository
    loader = GithubCodeLoader(repository_url='git@github.com:plivo/plivo-examples-python.git', 
                              local_dir='data/git_repos', 
                              branch='master')
    documents = loader.load()
    for doc in documents:
        print(doc.metadata) # metadata of the file

if __name__ == '__main__':
    main()
