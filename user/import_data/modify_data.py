from ..models import Namespaces
from .add_data import add_to_pinecone as add_to_pinecone_original
import pinecone 
import uuid,os
import pandas as pd
from tqdm.auto import tqdm

pinecone.init(
    api_key=os.environ.get("PINECONE_API_KEY"),
    environment=os.environ.get("PINECONE_ENVIRONMENT")
)
index_name= os.environ.get("PINECONE_INDEX_NAME")
index = pinecone.Index(index_name) 


def add_to_pinecone(df,index,namespace):
    # we will use batches of 64
    batch_size = 100

    for i in tqdm(range(0, len(df), batch_size)):
        # find end of batch
        i_end = min(i+batch_size, len(df))
        # extract batch
        batch = df.iloc[i:i_end].to_dict(orient="records")
        # upsert/insert these records to pinecone
        _ = index.upsert(vectors=(batch),namespace=namespace)

# The function takes two parameters: library_name and user
def get_data_from_namespace(library_name,user):
    # Query a table called Namespaces in my Django database and return the rows matching creator and name_to_user from the parameters
    mydata = Namespaces.objects.filter(creator=user,name_to_user=library_name).values()
    # Assign the variable namespace_in_db the value of the name_to_pinecone in the first row returned (and there should only be one row returned)
    namespace_in_db = mydata[0]['name_to_pinecone']
    # For the purposes of this function the name_to_pinecone will be called CURRENT_NAMESPACE_NAME...
    CURRENT_NAMESPACE_NAME  = namespace_in_db 
    # ... and NEW_NAMESPACE_NAME will be a new random UUID.
    NEW_NAMESPACE_NAME = str(uuid.uuid4())
    # Create empty lists
    all_data=[]
    csv_data=[]
    # This section runs an infinite loop finding the best 100 matches for the null vector and until (the if condition) no more matches are found.
    while True:
        query_response = index.query(
        namespace=CURRENT_NAMESPACE_NAME,
        top_k=100,
        include_values=True,
        include_metadata=True,
        vector=[0 for i in range(0,1536)]
        )
        # This 'if' loop exit is triggered when there are no more matches.  It deletes the NEW_NAMESPACE. It creates a dataframe from csv_data and another from all_data.
        # It then calls add_to_pinecone to upsert the all_data dataframe to the CURRENT_NAMESPACE_NAME
        if len(query_response['matches'])==0:
            # Tell Pinecone to delete NEW_NAMESPACE_NAME
            index.delete(delete_all=True, namespace=NEW_NAMESPACE_NAME)
            df = pd.DataFrame.from_dict(csv_data)
            df2 = pd.DataFrame.from_dict(all_data)
            # Add back into the CURRENT_NAMESPACE_NAME all of the data that we just moved over the temporary namespace and deleted!
            add_to_pinecone(df2,index,CURRENT_NAMESPACE_NAME)
            # Return a dataframe of all the metadata.  WHY?
            return df
        # The loop process (when the loop exit isn't triggered) continues here.
        # First it calls the process_query function (below) and feeds it the index.query (see above) of Top 100 mataches. 
        # The return will be 3 dictionaries: dict (containing IDs, texts, and metadata), id_list (containing just IDs), and csv_dict (containing just metadata)
        # ToDo - Change the 'dict' name.  And see why data_dict (the return name) gets renamed csv_dict.  Are they used elsewhere? 
        dict,id_list,csv_dict = process_query(query_response)
        # into the all_data list created above will be added the dict (i.e. all) content
        all_data = all_data + dict
        # into csa_data will be added the csv_dict (i.e. metadata) content
        csv_data = csv_data + csv_dict
        # send pinecone the instruction to upsert the dict content to the (temporary) pinecone namespace NEW_NAMESPACE_NAME
        index.upsert(vectors=(dict),
                    namespace=NEW_NAMESPACE_NAME)
        # send pinecone the instruction to delete all Top 100 vectors just matched in the namespace being queried (based on their IDs)
        index.delete(ids=id_list, namespace=CURRENT_NAMESPACE_NAME)


def process_query(query_response):
    dict=[]
    data_dict = []
    id_list=[]
    for match in query_response['matches']:
        dict.append({
            'id':match['id'],
            'values':match['values'],
            'metadata':match['metadata']
        })
        match['metadata']['id']=match['id']
        data_dict.append(match['metadata'])
        id_list.append(match['id'])
    return dict, id_list,data_dict


def update_data(namespace,user,file_path):
    mydata = Namespaces.objects.filter(creator=user,name_to_user=namespace).values()
    namespace_in_db = mydata[0]['name_to_pinecone']
    df = pd.read_csv(file_path,encoding='utf-8')
    os.remove(file_path)
    add_to_pinecone_original(df,index,namespace_in_db)