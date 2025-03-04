import os
import boto3
import streamlit as st
from langchain.llms.bedrock import Bedrock
from langchain.embeddings import BedrockEmbeddings
from langchain.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from dotenv import load_dotenv


load_dotenv()

aws_access_key_id = os.getenv("aws_access_key_id")
aws_secret_access_key = os.getenv("aws_secret_access_key")
region_name = os.getenv("region_name")

prompt_template = """

Human: Use the following pieces of context to provide a 
concise answer to the question at the end but use atleast summarize with 
250 words with detailed explantions. If you don't know the answer, 
just say that you don't know, don't try to make up an answer.
<context>
{context}
</context

Question: {question}

Assistant:"""

bedrock = boto3.client(
    service_name = "bedrock-runtime",
    region_name = "us-east-1",
    aws_access_key_id = aws_access_key_id,
    aws_secret_access_key = aws_secret_access_key,
)

bedrock_embedding = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1", client= bedrock)



def load_data():
    loader = PyPDFDirectoryLoader("data")
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=500)
    docs = text_splitter.split_documents(documents)
    return docs

def get_vector_store(docs):
    vector_store_FAISS = FAISS.from_documents(docs,bedrock_embedding)
    vector_store_FAISS.save_local("faiss_local")

def get_llm():
    llm = Bedrock(model_id = "meta.llama3-8b-instruct-v1:0", client = bedrock)
    return llm

prompt = PromptTemplate(
        input_variables=['context','question'],
        template= prompt_template
    )

def get_llm_response(llm, vectorstore_faiss, query):
    qa = RetrievalQA.from_chain_type(
        llm = llm,
        chain_type = 'stuff',
        retriever = vectorstore_faiss.as_retriever(
            search_type="similarity", search_kwargs={"k": 3}
        ),
        return_source_documents = True,
        chain_type_kwargs={"prompt": prompt})
    
    response = qa({"query": query})
    return response['result']

def main():
    st.set_page_config("RAG")
    st.header("End to end RAG using Bedrock")

    user_question = st.text_input("Ask a question from the PDF file")

    with st.sidebar:
        st.title("Update & create vectore store")

        if st.button("Store vector"):
            with st.spinner("Processing....."):
                docs = load_data()
                get_vector_store(docs)
                st.success("Done")

        if st.button("Send"):
            with st.spinner("Processing.."):
               faiss_index = FAISS.load_local("faiss_local", bedrock_embedding, allow_dangerous_deserialization=True) 
               llm = get_llm()
               st.write(get_llm_response(llm,faiss_index,  user_question))

if __name__ == "__main__":
    main()

    
