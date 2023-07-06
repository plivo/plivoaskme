import os
import pickle
from langchain.vectorstores.faiss import FAISS
from langchain.vectorstores.redis import Redis
from langchain.vectorstores.chroma import Chroma
from qdrant_client import QdrantClient
from langchain.vectorstores.qdrant import Qdrant
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter


class BaseEngine(object):
    def __init__(self, vector_url):
        self.vector_url = vector_url
        self.embeddings = OpenAIEmbeddings()
        self.engine_name = "faiss"
        if self.vector_url.startswith("redis://"):
            self.engine_name = "redis"
        elif self.vector_url.startswith("chroma://"):
            self.engine_name = "chroma"
        elif self.vector_url.startswith("qdrant://"):
            self.engine_name = "qdrant"
        elif self.vector_url in ('mock', 'dummy') or self.vector_url is None:
            self.engine_name = "mock"

    def _ingest(self, **kwargs):
        print(f"Using engine: {self.engine_name}")
        ingest_func = getattr(self, f"_ingest_{self.engine_name}", None)
        if not ingest_func:
            raise ValueError(f"Unknown engine: {self.engine_name}")
        return ingest_func(**kwargs)

    def _load(self, **kwargs):
        print(f"Using engine: {self.engine_name}")
        load_func = getattr(self, f"_load_{self.engine_name}", None)
        if not load_func:
            raise ValueError(f"Unknown engine: {self.engine_name}")
        return load_func(**kwargs)



class Ingestor(BaseEngine):
    def __init__(self, vector_url, docs):
        super().__init__(vector_url)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=10,
        )
        self.docs = text_splitter.split_documents(docs)

    def _ingest_mock(self, **kwargs):
        while len(self.docs) > 0:
            print(f"Total chunks left to process: {len(self.docs)}")
            docs = self._pop()
            print(f"Processing {len(docs)} chunks...")
            print(f"Loaded chunks: processed: {len(docs)}, unprocessed: 0")
        return True

    def _ingest_redis(self, **kwargs):
        db = None
        while len(self.docs) > 0:
            print(f"Total chunks left to process: {len(self.docs)}")
            docs = self._pop()
            print(f"Processing {len(docs)} chunks...")
            if db is None:
                db = Redis.from_documents(docs, self.embeddings, redis_url=self.vector_url, index_name='plivoaskme')
                print(f"Loaded chunks: processed: {len(docs)}, unprocessed: 0")
            else:
                try:
                    db.add_documents(documents=docs, embedding=self.embeddings)
                    processed = len(docs)
                    unprocessed = 0
                except ValueError as e:
                    print(f"ERROR: {e}")
                    processed = 0
                    unprocessed = 0
                    for doc in docs:
                        try:
                            db.add_documents(documents=[doc], embedding=self.embeddings)
                            processed += 1
                        except ValueError as e:
                            unprocessed += 1
                            print(f"ERROR: {e}")
                            print(f"SKIPPING: {doc}")
                print(f"Loaded chunks: processed: {processed}, unprocessed: {unprocessed}")
        db = None
        return True

    def _ingest_qdrant(self, **kwargs):
        url = self.vector_url.replace("qdrant://", "") or None
        api_key = os.environ.get("QDRANT_API_KEY", None)
        if not url:
            raise ValueError("Qdrant URL is required")
        db = None
        while len(self.docs) > 0:
            print(f"Total chunks left to process: {len(self.docs)}")
            docs = self._pop()
            print(f"Processing {len(docs)} chunks...")
            if db is None:
                db = Qdrant.from_documents(
                    docs, self.embeddings,
                    url=url, api_key=api_key,
                    prefer_grpc=True,
                    collection_name="plivoaskme",
                )
                print(f"Loaded chunks: processed: {len(docs)}, unprocessed: 0")
            else:
                try:
                    db.add_documents(documents=docs, embedding=self.embeddings)
                    processed = len(docs)
                    unprocessed = 0
                except ValueError as e:
                    print(f"ERROR: {e}")
                    processed = 0
                    unprocessed = 0
                    for doc in docs:
                        try:
                            db.add_documents(documents=[doc], embedding=self.embeddings)
                            processed += 1
                        except ValueError as e:
                            unprocessed += 1
                            print(f"ERROR: {e}")
                            print(f"SKIPPING: {doc}")
                print(f"Loaded chunks: processed: {processed}, unprocessed: {unprocessed}")

        db = None
        return True

    def _ingest_chroma(self, **kwargs):
        directory = self.vector_url.replace("chroma://", "") or None
        if not directory:
            raise ValueError("Chroma directory is required")
        try:
            os.makedirs(directory)
        except:
            pass
        db = None
        while len(self.docs) > 0:
            print(f"Total chunks left to process: {len(self.docs)}")
            docs = self._pop()
            print(f"Processing {len(docs)} chunks...")
            if db is None:
                db = Chroma.from_documents(chunks=docs, embedding=self.embeddings, 
                                   persist_directory=directory)
                print(f"Loaded chunks: processed: {len(docs)}, unprocessed: 0")
            else:
                try:
                    db.add_documents(documents=docs, embedding=self.embeddings)
                    processed = len(docs)
                    unprocessed = 0
                except ValueError as e:
                    print(f"ERROR: {e}")
                    processed = 0
                    unprocessed = 0
                    for doc in docs:
                        try:
                            db.add_documents(documents=[doc], embedding=self.embeddings)
                            processed += 1
                        except ValueError as e:
                            unprocessed += 1
                            print(f"ERROR: {e}")
                            print(f"SKIPPING: {doc}")
                print(f"Loaded chunks: processed: {processed}, unprocessed: {unprocessed}")

        if db is not None:
            db.persist()
        db = None
        return True

    def _retry_ingest_faiss(self, docs):
        print(f"DEBUG: _retry_ingest_faiss start processing {len(docs)}")
        # re-init embeddings
        self.embeddings = OpenAIEmbeddings()
        db = None
        _db = None
        prev_doc = None
        processed = 0
        for doc in docs:
            try:
                _db = FAISS.from_documents([doc], self.embeddings)
            except ValueError as e:
                print(f"# ERROR: FAISS.from_documents: {e}")
                print(f"# ACTION: skipping document CURRENT_DOC")
                print(f"# CURRENT_DOC:\n{doc}\n\n")
                print(f"# PREVIOUS_DOC:\n{prev_doc}\n\n")
                print("#"*10)
                continue
            try:
                if db is None:
                    db = _db
                else:
                    db.merge_from(_db)
                processed += 1
            except Exception as e:
                print(f"# ERROR db.merge_from: {e}")
                print(f"# ACTION: skipping document CURRENT_DOC")
                print(f"# CURRENT_DOC:\n{doc}\n\n")
                print(f"# PREVIOUS_DOC:\n{prev_doc}\n\n")
                print("#"*10)
                continue
            prev_doc = doc

        unnprocessed = len(docs) - processed
        print(f"DEBUG: _retry_ingest_faiss done: processed:{processed}, unprocessed:{unnprocessed}")
        return db

    def _ingest_faiss(self, **kwargs):
        overwrite = kwargs.get("overwrite", True)
        ingest_size = kwargs.get("ingest_size", 500)
        idx = 1
        print(f"Total chunks to process: {len(self.docs)}")
        while len(self.docs) > 0:
            print(f"Total chunks left to process: {len(self.docs)}")
            docs = self._pop(size=ingest_size)
            print(f"Processing {len(docs)} chunks...")
            try:
                db = FAISS.from_documents(docs, self.embeddings)
            except ValueError as e:
                print(f"ERROR FAISS.from_documents: {e}")
                db = self._retry_ingest_faiss(docs)
            vector_url = self.vector_url + f".{idx}"
            print(f"Saving {len(docs)} chunks into FAISS {vector_url}")
            with open(vector_url, "wb") as f:
                pickle.dump(db, f)
            idx += 1
            print(f"Saved {len(docs)} chunks into FAISS {vector_url}")
            print(f"Processed {len(docs)} chunks...")
        
        orig_vector_url = self.vector_url + '.1'
        if not os.path.exists(orig_vector_url):
            print(f"No FAISS file {orig_vector_url} created, stopping...")
            return False

        db = Loader.load(orig_vector_url)
        for i in range(2, idx):
            vector_url = self.vector_url + f".{i}"
            if not os.path.exists(vector_url):
                print(f"No FAISS file {vector_url} created, skipping...")
                continue
            print(f"Merging {vector_url} into {orig_vector_url}")
            db.merge_from(Loader.load(vector_url))
            os.remove(vector_url)
            print(f"Merged {vector_url} into {orig_vector_url}")

        try: os.remove(orig_vector_url)
        except: pass

        if overwrite is True or not os.path.exists(self.vector_url):
            print(f"New FAISS file created {self.vector_url}, saving...")
            with open(self.vector_url, "wb") as f:
                pickle.dump(db, f)
            print(f"Saved data into {self.vector_url}")
            return True
        else:
            print(f"Found existing FAISS file {self.vector_url}, merging...")
            src_db = Loader.load(self.vector_url)
            src_db.merge_from(db)
            with open(self.vector_url, "wb") as f:
                pickle.dump(src_db, f)
            print(f"Merged data into {self.vector_url}")
            return True
    
    def run(self, **kwargs):
        return self._ingest(**kwargs)

    def _pop(self, size=500):
        docs = []
        i = 0
        while i < size:
            try:
                doc = self.docs.pop()
                docs.append(doc)
                i += 1
            except IndexError:
                break
        return docs

    @classmethod
    def ingest(cls, vector_url, docs, **kwargs):
        return cls(vector_url, docs).run(**kwargs)
        


class Loader(BaseEngine):
    def __init__(self, vector_url):
        super().__init__(vector_url)

    def _load_redis(self, **kwargs):
        db = Redis.from_existing_index(self.embeddings, 
                                      redis_url=self.vector_url, 
                                      index_name='plivoaskme')
        return db 

    def _load_qdrant(self, **kwargs):
        url = self.vector_url.replace("qdrant://", "") or None
        api_key = os.environ.get("QDRANT_API_KEY", None)
        if not url:
            raise Exception(f"Qdrant URL not found: {url}")
        client = QdrantClient(
            url=url, api_key=api_key,
            prefer_grpc=True
        )
        db = Qdrant(
            client=client, collection_name="plivoaskme",
            embeddings=self.embeddings
        )
        return db

    def _load_chroma(self, **kwargs):
        directory = self.vector_url.replace("chroma://", "") or None
        if not directory:
            raise Exception(f"Chroma directory not found: {directory}")
        db = Chroma(persist_directory=self.vector_url, 
                    embedding_function=self.embeddings)
        return db

    def _load_faiss(self, **kwargs):
        if not os.path.exists(self.vector_url):
            raise Exception(f"FAISS file not found: {self.vector_url}")
        with open(self.vector_url, "rb") as f:
            db = pickle.load(f)
        return db

    def run(self, **kwargs):
        return self._load(**kwargs)

    @classmethod
    def load(cls, vector_url, **kwargs):
        return cls(vector_url).run(**kwargs)

