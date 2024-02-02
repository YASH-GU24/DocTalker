from docx2pdf import convert
import docx, os
import pandas as pd
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
import PyPDF2, re
from bs4 import BeautifulSoup as bs

file_name_column = 'file_name'

def make_chunks(filename,chunk_size_chars):   
    print(f"Processing file: {filename}, extension: {filename.split('.')[-1]}")
    # if the file is a word document 
    if filename.endswith(".docx"):
        print("/nIdentified as a .docx document") # debug line - can remove later
        # split the text into chunks
        split_text = main_docx(filename, chunk_size_chars)
        # check if the text was split into chunks
        if split_text is False:
            print("Cannot create chunks for file...",filename)
        else: # if the text was split into chunks then save the output
            temp_store_list = []
            for item1 in split_text:
                temp_store_dict = {}
                temp_store_dict[file_name_column] = filename
                temp_store_dict["Text Segment"] = item1[0]
                temp_store_dict["Page"] = item1[1]
                temp_store_list.append(temp_store_dict)

            df = pd.DataFrame(temp_store_list)
            print(f"DataFrame shape after splitting docx file: {df.shape}")
            print(df.head())
            return df
        
    # if the file is a pdf document
    elif filename.endswith(".pdf"):
        print("/nIdentified as a .pdf document") # debug line - can remove later
        # split the text into chunks
        split_text = main_pdf(filename, chunk_size_chars)
        # check if the text was split into chunks and then save the output
        if split_text is False:
            print("Cannot create chunks for file...",filename)
        else: # if the text was split into chunks then save the output    
            temp_store_list = []
            for item1 in split_text:
                temp_store_dict = {}
                temp_store_dict[file_name_column] = filename
                item1[0] = ILLEGAL_CHARACTERS_RE.sub(r'', item1[0])
                temp_store_dict["Text Segment"] = item1[0]
                temp_store_dict["Page"] = item1[1]
                temp_store_list.append(temp_store_dict)

            df = pd.DataFrame(temp_store_list)
            print(f"DataFrame shape after splitting pdf file: {df.shape}")
            print(df.head())            
            return df

    # if the file is an html document
    elif filename.endswith(".html"):
        print("/nIdentified as a .html document") # debug line - can remove later
        # split the text into chunks
        split_text = split_text_by_characters_html(filename, chunk_size_chars)
        if split_text is False:
            print("Cannot create chunks for file...",filename)
        else: # if the text was split into chunks then save the output
            temp_store_list = []
            for item1 in split_text:
                temp_store_dict = {}
                temp_store_dict[file_name_column] = filename
                temp_store_dict["Text Segment"] = item1
                temp_store_dict["Page"] = "-"
                temp_store_list.append(temp_store_dict)

            df = pd.DataFrame(temp_store_list)
            print(f"DataFrame shape after splitting html file: {df.shape}")
            print(df.head())      
            return df

    else:
        print(f"File {filename} is not a docx or pdf file. Skipping...")
    print("-"*40)


# function for .docx documents - convert to pdf and split
def main_docx(filename, chunk_size_chars):
    # Debug output
    print("Before convert() call") # debug line - can remove later
    # convert the .docx to a pdf temporarily
    convert(filename, "temp.pdf")
    print(f"Converted {filename} to temp.pdf")
    print(f"Is temp.pdf file present: {os.path.isfile('temp.pdf')}") # debug line - can remove later
    # Debug output
    print("After convert() call") # debug line - can remove later
    # call the function to split the pdf
    split_text = find_pdf_page_numbers("temp.pdf", chunk_size_chars)
    return split_text


# function for .pdf documents - split
def main_pdf(filename, chunk_size_chars):
    print(f"Splitting PDF: {filename}")
    # call the function to split the pdf
    split_text = find_pdf_page_numbers(filename, chunk_size_chars)
    return split_text

# function to split the HTML document in to chunks
def split_text_by_characters_html(filename, chunk_size_chars):
    print(f"Splitting HTML: {filename}")
    # open the HTML file
    with open(filename, encoding="utf-8") as f:
        content = f.read()
    
    # parse the HTML file
    soup = bs(content, 'html.parser')

    # extract the text from the HTML file
    for element in soup(["style", "script"]):
        element.decompose()

    text = soup.text

    new_lines = []
    lines = text.split(".")
    # iterate over the lines and format them into a new list
    for line in range(len(lines)):
        if lines[line].replace("\n", "").strip() == "":
            continue
        if lines[line].strip().endswith("and"):
            new_lines.append(lines[line]+lines[line+1])
        else:
            new_lines.append(lines[line])

    split_text = []
    current_text = ""
    current_length = 0

    # iterate over the lines and split them into chunks until they are finished
    for line in new_lines:
        line = line.strip()
        
        # check if the current line is max than the max characters
        if current_length + len(line) + 1 > chunk_size_chars:
            split_text.append(current_text)
            current_text = ""
            current_length = 0
            
        current_text += line + ". "
        current_length += len(line) + 1

    split_text.append(current_text)

    print(f"\nSuccessfully split HTML document into chunks...")

    return split_text

def find_pdf_page_numbers(filename, chunk_size_chars):
        # load the pdf
        pdf_reader = PyPDF2.PdfReader(filename)
        page_text = ""

        split_text = []

        # extract the text from the pdf
        for page in range(len(pdf_reader.pages)):
             
             
             # check if the page number should be inserted or not
            # if self.insert_page.get():
            #    page_text += f"<START OF PAGE #{page+1}>\n" + f"[[Page Number#{page+1}]]" + pdf_reader.pages[page].extract_text() + f"[[Page Number#{page+1}]]\n"
            # else: 
                page_text += f"<START OF PAGE #{page+1}>\n" + f"[[Page Number#{page+1}]]" + pdf_reader.pages[page].extract_text() + f"[[Page Number#{page+1}]]\n"

        new_lines = []
        # split the text into lines
        lines = page_text.split(".")
        # iterate over the lines and format them into a new list
        for line in range(len(lines)):
            if lines[line].replace("\n", "").strip() == "":
                continue
            if lines[line].strip().endswith("and"):
                new_lines.append(lines[line]+lines[line+1])

            elif lines[line].strip().endswith("[[Page Number"):
                new_lines.append(lines[line]+lines[line+1])
            else:
                new_lines.append(lines[line])

        current_text = ""
        current_length = 0
        page_numbers = ""

        # iterate over the lines and split them into chunks until they are finished
        for new_line in new_lines:
            new_line = new_line.strip()
            # remove the empty lines
            lines = [line for line in new_line.split("\n") if line.strip()]
            line = "\n".join(lines)

            # check if the current line is max than the max characters
            if current_length + len(line) + 1 > chunk_size_chars:
                new_current_text = ""
                # iterate over the lines and find the page numbers, then remove the page numbers from the text
                for item in current_text.split("\n"):
                    if "[[Page Number#" in item:
                        # print(item)
                        # print(item.split("#")[1])
                        # print(item.split("#")[1].split("]]")[0])
                        # print("")
                        number = str(item.split("Number#")[1].split("]]")[0])
                        if number in page_numbers:
                            pass
                        else:
                            page_numbers +=  number + ", "
                        item = item.replace("[[Page Number#"+str(number)+"]]", "")
                    # add the new line to the text
                    new_current_text += item + "\n"

                # remove the last comma from the page numbers
                if page_numbers == "":
                    page_numbers = number + ", "

                # append the text and the page numbers to the list
                split_text.append([new_current_text, page_numbers[:-2]])
                current_text = ""
                current_length = 0
                page_numbers = ""
                
            current_text += line + ". "
            current_length += len(line) + 1

        new_current_text = ""
        
        # iterate over the remaning lines and find the page numbers, then remove the page numbers from the text
        for item in current_text.split("\n"):
            if "[[Page Number#" in item:
                number = str(item.split("Number#")[1].split("]]")[0])
                if number in page_numbers:
                    pass
                else:
                    page_numbers +=  number + ", "
                item = item.replace("[[Page Number#"+str(number)+"]]", "")
            new_current_text += item + "\n"

        # check if the last line is empty or not
        if new_current_text.replace(".", "").strip() == "":
            pass
        else: # if not empty, then append the text and the page numbers to the list
            if page_numbers == "":
                page_numbers = number + ", "
            split_text.append([new_current_text, page_numbers[:-2]])

        print(f"\nSuccessfully split PDF into chunks...")

        return split_text

