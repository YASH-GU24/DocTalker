from ..models import Namespaces
import json

def get_user_namespaces(user):
    mydata = Namespaces.objects.filter(creator=user).values()
    namespaces = []
    for data in mydata:
        namespaces.append(data['name_to_user'])
    return json.dumps(namespaces)