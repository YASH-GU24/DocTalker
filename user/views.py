from django.http import HttpResponse
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from .forms import UserForm
from .forms import EmailResetForm
from django.contrib import messages, auth
import pandas as pd
import io,json,os
from django.conf import settings
from django import forms
from user.import_data.add_data import add_from_csv,add_data_from_files
from user.import_data.modify_data import get_data_from_namespace, update_data
from user.chat_apis.make_chain import get_chat_answer
from user.chat_apis.make_chain import chat_history_global
from user.chat_apis.get_namespaces import get_user_namespaces
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView
from .models import User

# Create your views here.

def register(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in!")
        return redirect("dashboard")
    elif request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            # Create the user using the form
            password = form.cleaned_data["password"]
            user = form.save(commit=False)
            user.set_password(password)
            user.is_active = True
            user.save()

            return redirect("login")
        else:
            print("invalid form")
            print(form.errors)
    else:
        form = UserForm()
    context = {
        "form": form,
    }
    return render(request, "user/register.html", context)


def login(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in!")
        return redirect("dashboard")
    elif request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        user = auth.authenticate(email=email, password=password)

        if user is not None:
            auth.login(request, user)
            messages.success(request, "You are now logged in.")
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid login credentials")
            return redirect("login")
    return render(request, "user/login.html")


def logout(request):
    auth.logout(request)
    messages.info(request, "You are logged out.")
    return redirect("login")


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect("login")
    return render(request, "user/dashboard.html")


def add_data_from_csv(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if "GET" == request.method:
        return render(request, "user/upload_from_csv.html")
    namespace = request.POST["namespace"]
    text_column = request.POST["text_column"]
    meta_fields = request.POST.getlist("meta_fields")
    file_path = "{}{}/data.csv".format(settings.MEDIA_ROOT,request.user.username)
    user = request.user
    add_from_csv(namespace,text_column,meta_fields,file_path,request)
    return redirect("get_answer")
    
def upload_from_csv(request):
    if not request.user.is_authenticated:
        return redirect("login")
    data = {}
    if "GET" == request.method:
        return render(request, "user/upload_from_csv.html", data)
    # if not GET, then proceed
    csv_file = request.FILES["csv_file"]
    # Remove BOM by specifying the encoding as "utf-8-sig"
    csv_data = pd.read_csv(io.StringIO(csv_file.read().decode("utf-8-sig")))
    print(csv_file.name)
    
    try:
        os.mkdir("{}{}".format(settings.MEDIA_ROOT,request.user.username))
    except Exception as e:
        print(e)

    csv_data.to_csv("{}{}/data.csv".format(settings.MEDIA_ROOT,request.user.username))
    CHOICES = (
        [(col,col) for i,col in enumerate(csv_data.columns)]
    )

    class MyForm(forms.Form):
        meta_fields = forms.MultipleChoiceField(
                choices=CHOICES, 
                label="Choose columns you want to keep as meta data", 
                required=True) 
        text_column = forms.CharField(label='Select the column where content is present', widget=forms.Select(choices=CHOICES))
        namespace = forms.CharField(max_length=25)
    choose_form = MyForm()
    return render(request, "user/choose_columns.html",{
        "form": choose_form,
    })

def add_from_files(request):
    if not request.user.is_authenticated:
        return redirect("login")
    data = {}
    
    # Initialize a counter for the desired file types
    files_selected_count = 0
    request.session['upserted_count'] = 0
    request.session['last_used_id_counter'] = 0
    
    if "GET" == request.method:
        class MyForm(forms.Form):
            namespace = forms.CharField(max_length=25, label="Library name")
            chunk_size = forms.IntegerField(label="Number of words per text segment")
        choose_form = MyForm()
        choose_form.fields['chunk_size'].initial = 500
        return render(request, "user/add_from_files.html",{
            "form": choose_form,
        })
    # if not GET, then proceed
    try:
        os.mkdir("{}{}".format(settings.MEDIA_ROOT,request.user.username))
    except Exception as e:
        print(e)
    for x in request.FILES.getlist("files"):
        
        # This little section is an addition to move on the datafram_count for each file of the correct format 
        file_extension = os.path.splitext(str(x))[1].lower()  # Extract file extension and convert to lowercase
        if file_extension in ['.pdf', '.docx', '.html']:
            files_selected_count += 1
            request.session['files_selected_count'] = files_selected_count
            
        # back to original main process
        def process(f):
            with open("{}{}/{}".format(settings.MEDIA_ROOT,request.user.username,str(x)), 'wb+') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)
        process(x)

    namespace = request.POST["namespace"]
    chunk_size = int(request.POST["chunk_size"])
    add_data_from_files("{}{}".format(settings.MEDIA_ROOT,request.user.username),chunk_size,namespace,request)

    return redirect("get_answer")

@csrf_exempt 
def get_answer(request):
    if "POST" == request.method:
        question = request.POST["question"]
        history = request.POST["history"]
        namespace = request.POST["namespace"]
        print("namespace",namespace)
        response = get_chat_answer(question,history,namespace,request.user)
        return HttpResponse(response)
    else:
        return render(request, "user/chat.html")
    
@login_required
def get_namespaces(request):
    if "GET" == request.method:
        current_user = auth.get_user(request)
        return HttpResponse(get_user_namespaces(current_user))
    
def download_csv(df):
    # Create a CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="mydata.csv"'
    df.to_csv(path_or_buf=response, index=False)
    return response

def library_manager(request):
    value_list = json.loads(get_user_namespaces(request.user))

    if request.method == 'POST':
        selected_value = request.POST.get('value')
        # Process the selected value here, such as saving it to the database or performing any other action
        print(get_data_from_namespace(selected_value,request.user))
        return download_csv(get_data_from_namespace(selected_value,request.user))

    return render(request, 'user/library_manager.html', {'value_list': value_list})

def modify_data(request):
    if not request.user.is_authenticated:
        return redirect("login")
    data = {}
    if "GET" == request.method:
        value_list = json.loads(get_user_namespaces(request.user))
        return render(request, "user/upload_modified_csv.html", {'value_list': value_list})
    # if not GET, then proceed
    csv_file = request.FILES["csv_file"]
    csv_data = pd.read_csv(io.StringIO(csv_file.read().decode("latin-1")))
    namespace = request.POST.get('value')
    try:
        os.mkdir("{}{}".format(settings.MEDIA_ROOT,request.user.username))
    except Exception as e:
        print(e)
    file_path = "{}{}/data.csv".format(settings.MEDIA_ROOT,request.user.username)
    user = request.user
    csv_data.to_csv("{}{}/data.csv".format(settings.MEDIA_ROOT,request.user.username))
    update_data(namespace,user,file_path)
    if os.path.exists("{}{}/data.csv".format(settings.MEDIA_ROOT,request.user.username)):
        os.remove("{}{}/data.csv".format(settings.MEDIA_ROOT,request.user.username))
    return redirect("get_answer")

def get_chat_history(request):
    return JsonResponse(chat_history_global, safe=False)

@csrf_exempt
def reset_chat_history(request):
    print("reset_chat_history view has been accessed.")  # Debugging print statement
    # if not request.is_ajax():
    #    print("The request was not AJAX.")  # Debugging print statement
    #    return HttpResponseNotAllowed(['POST'])
    
    chat_history_global.clear()
    print("chat_history_global has been cleared.")  # Debugging print statement
    return JsonResponse({'status': 'success', 'message': 'Chat history reset successfully'})