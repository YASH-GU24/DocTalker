import pandas as pd
from datetime import datetime
import time
from user.import_data.make_chunks import make_chunks
import warnings
warnings.filterwarnings("ignore")
import os,json
from tqdm import tqdm
import openai
from dotenv import load_dotenv
import pinecone 
import uuid
from ..models import Namespaces
load_dotenv()

openai.api_key=os.environ.get("OPENAI_API_KEY")

pinecone.init(
    api_key=os.environ.get("PINECONE_API_KEY"),
    environment=os.environ.get("PINECONE_ENVIRONMENT")
)
index_name = os.environ.get("PINECONE_INDEX_NAME")
# check if the extractive-question-answering index exists
if index_name not in pinecone.list_indexes():
    # create the index if it does not exist
    pinecone.create_index(
        index_name,
        dimension=1536,
        metric="cosine"
    )
index = pinecone.Index(index_name)


def add_data_from_files(folder_path,chunk_size_words,namespace,request):
    user = request.user

    # The is a debug print to check the files_selected_count, which should be the number of files of the valid type being passed in
    files_selected_count = request.session.get('files_selected_count', 0)
    print(f"files_selected_count in add_data_from_files at the start: {files_selected_count}")
    upserted_count = request.session.get('upserted_count', 0)
    print(f"upserted_count in add_data_from_files at the start: {upserted_count}")

    mydata = Namespaces.objects.filter(creator=user,name_to_user=namespace).values()
    if mydata:
        namespace_in_db = mydata[0]['name_to_pinecone']
    else:
        namespace_in_db = str(uuid.uuid4())
        obj = Namespaces(index=index_name,name_to_pinecone=namespace_in_db, name_to_user=namespace,creator=user)
        obj.save()
    for filename in os.listdir(folder_path):
        f = os.path.join(folder_path , filename)
        # checking if it is a file
        if os.path.isfile(f):
            filepath=f
            filename=os.path.basename(f)
        if filename[-5:]=='.docx' or filename[-4:]=='.pdf' or filename[-5:]=='.html':
            chunk_size_chars=chunk_size_words * 7  # Convert chunk size to characters
            df_of_chunks_from_a_file=make_chunks(filepath,chunk_size_chars)
            df_of_chunks_from_a_file['file_name']=filename
            print(f"The file '{filename}' has been converted to a dataframe of {df_of_chunks_from_a_file.shape[0]} rows and {df_of_chunks_from_a_file.shape[1]} columns and is being sent to the add_to_pinecone function.")
            add_to_pinecone(df_of_chunks_from_a_file,index,namespace_in_db,request)
        else:
            print(filename," Is not the supported type")
        os.remove(filepath)

def add_from_csv(namespace,text_column,meta_fields,file_path,request):
    user = request.user
    df_of_chunks_from_a_CSV = pd.read_csv(file_path,encoding='utf-8')
    print(df_of_chunks_from_a_CSV.columns)  # Print the column names seen in CSV (for debuging)
    if text_column not in meta_fields:   # Fix of keyerror when text_column was not appearing in df meta_fields
        meta_fields.append(text_column)  # Fix continued
    df_of_chunks_from_a_CSV = df_of_chunks_from_a_CSV[meta_fields]
    df_of_chunks_from_a_CSV.rename(columns={text_column:"Text Segment"},inplace=True)
    print(df_of_chunks_from_a_CSV.columns)  # Print the column names in dataframe after renaming one to Text Segment (for debug)
    mydata = Namespaces.objects.filter(creator=user,name_to_user=namespace).values()
    if mydata:
        namespace_in_db = mydata[0]['name_to_pinecone']
    else:
        namespace_in_db = str(uuid.uuid4())
        obj = Namespaces(index=index_name,name_to_pinecone=namespace_in_db, name_to_user=namespace,creator=user)
        obj.save()
    os.remove(file_path)
    add_to_pinecone(df_of_chunks_from_a_CSV,index,namespace_in_db,request)

def add_to_pinecone(dataframe_input_to_upsert,index,namespace,request):
    files_selected_count = request.session.get('files_selected_count', 0)
    print(f"files_selected_count in add_to_pinecone at the start: {files_selected_count}")
    upserted_count = request.session.get('upserted_count', 0)
    print(f"upserted_count in add_to_pinecone at the start: {upserted_count}")
    last_used_id_counter = request.session.get('last_used_id_counter', 0)
    print(f"last_used_id_counter: {last_used_id_counter}")
    last_id = last_used_id_counter

    # Print information about the received dataframe
    print(f"/n Received dataframe: {dataframe_input_to_upsert.shape[0]} rows, {dataframe_input_to_upsert.shape[1]} columns")


    # This is where the original started
    # we will use batches of 64
    batch_size = 64
    MODEL = "text-embedding-ada-002"
    for i in tqdm(range(0, len(dataframe_input_to_upsert), batch_size)):
        # find end of batch
        i_end = min(i+batch_size, len(dataframe_input_to_upsert))
        # extract batch
        batch = dataframe_input_to_upsert.iloc[i:i_end]
        # create unique IDs
        if "Unnamed: 0" in batch.columns:
            batch.drop(["Unnamed: 0"], axis=1,inplace = True)
        if "id" in batch.columns:
            batch["id"] = batch["id"].astype(str)
            ids = batch["id"].tolist()
            batch.drop(['id'], axis=1,inplace = True)
        else:
            # ids = [f"{idx}" for idx in range(i, i_end)] # this was the original before using last_used_id_counter
            ids = [f"{idx}" for idx in range(last_id + i, last_id + i_end)]        
        
        # Update the session with the last used ID
        request.session['last_used_id_counter'] += len(dataframe_input_to_upsert)
        
        # generate embeddings for batch
        batch["Text Segment"].replace({r'[^\x00-\x7F]+':''}, regex=True, inplace=True)
        for col in batch.columns:
            batch[col] = batch[col].astype(str)
        # print(batch["Text Segment"].tolist()[0])
        res = openai.Embedding.create(input=batch["Text Segment"].tolist(), engine=MODEL)
        emb = [record['embedding'] for record in res['data']]
        # get metadata
        meta = batch.to_dict(orient='records')
        to_upsert = list(zip(ids, emb, meta))
        # upsert/insert these records to pinecone
        _ = index.upsert(vectors=to_upsert,namespace=namespace)
        # Print information about the upserted batch
        print(f"/n Upserting batch from dataframe: {dataframe_input_to_upsert.shape[0]} rows, {dataframe_input_to_upsert.shape[1]} columns")
        print(f"/n Batch size: {len(batch)} items")
    

    # Return the updated upserted_count
    return upserted_count