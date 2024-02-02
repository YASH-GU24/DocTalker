from ..models import Namespaces

from langchain.chains import ConversationalRetrievalChain
from langchain.chains.conversational_retrieval.base import BaseConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.prompts import PromptTemplate
import pinecone
import os,json

# Initialize a global list to store the chat history
chat_history_global = []

CONDENSE_PROMPT ="""Given the following conversation and a follow up question, rephrase the follow up question or task to be a standalone instruction.

Chat History:
{chat_history}
Follow Up Input: {question}
Standalone question:"""

QA_PROMPT = """You are a helpful AI assistant. Use the following pieces of context to answer the question or complete the task at the end.
If you don't know the answer, just say you don't know. Provide long, detailed answers. DO NOT try to make up an answer.
If the question is not related to the context, politely respond that you are tuned to only answer questions that are related to the context.

{context}

Question: {question}
Helpful answer in markdown:"""
SUPPORT_PROMPT = PromptTemplate(
    template=QA_PROMPT, input_variables=["context", "question"]
)
CONDENSE_QUESTION_PROMPT =  PromptTemplate(
    template=CONDENSE_PROMPT, input_variables=["chat_history", "question"]
)

embeddings = OpenAIEmbeddings()
llm = ChatOpenAI(
    model_name="gpt-3.5-turbo-16k",
    temperature=0,
    openai_api_key=os.environ.get("OPENAI_API_KEY"),
)
pinecone.init(
    api_key=os.environ.get("PINECONE_API_KEY"),
    environment=os.environ.get("PINECONE_ENVIRONMENT")
)
index_name= os.environ.get("PINECONE_INDEX_NAME")

def get_chat_answer(question,chat_history,namespace,user):  # ToDo rename this to 'create_a_chain' after checking it is not used elsewhere
    mydata = Namespaces.objects.filter(creator=user,name_to_user=namespace).values()
    namespace_in_db = mydata[0]['name_to_pinecone']
    docsearch = Pinecone.from_existing_index(index_name, embeddings,namespace=namespace_in_db,text_key="Text Segment")
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=docsearch.as_retriever(search_kwargs={"k": 3}),
        return_source_documents=True,
        condense_question_prompt=CONDENSE_QUESTION_PROMPT,
    )
    return generate_response(chain,question,chat_history)

def generate_response(support_qa: BaseConversationalRetrievalChain, prompt,chat_history):
    history = json.loads(chat_history)
    chat_history =[]
    for obj in history:
        chat_history.append((obj['question'],obj['response']))
    response = support_qa({"question": prompt, "chat_history": chat_history})
    res = {'text':response['answer'], 'sourceDocuments':[doc.__dict__ for doc in response['source_documents']]}
    
    # Print the question, response, and source documents
    print(f'Question: {prompt}')
    print(f'Response: {response["answer"]}')
    
    print('Source Documents:')
    for i, doc in enumerate(response['source_documents']):
        print(f'Document {i + 1}:')
        for key, value in doc.__dict__.items():
            if key == 'page_content':
                value = value.replace('\n', ' ')  # remove line breaks from page_content
            print(f'  {key}: {value}')

    # Clean up the source documents and add the question, response, and source documents to the chat_history_global list.
    
    # ToDo - This is going to be memory intensive with lots of users, so switch to using a Django model 
    # to represent a chat message, and then use Django's database API to store and retrieve chat messages.
    # ToDo - check that sourceDocuments variable is not being mis-reused here creating potential unexpected results
    chat_entry = {
        'question': prompt,
        'response': response['answer'],
        'sourceDocuments': []
    }
    for i, doc in enumerate(response['source_documents']):
        cleaned_text_segments = {}
        for key, value in doc.__dict__.items():
            if key == 'page_content':
                value = value.replace('\n', ' ')  # remove line breaks from page_content
            cleaned_text_segments[key] = value
        chat_entry['sourceDocuments'].append(cleaned_text_segments)
    chat_history_global.append(chat_entry)
    
    return json.dumps(res)
