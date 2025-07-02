import os
import pymupdf
import streamlit as st
from dotenv import load_dotenv
import sys

# Get the absolute path to the directory containing the script to import
# Replace 'path/to/your/other_folder' with the actual relative or absolute path
other_folder_path = os.path.abspath('./../../scripts') 

# Add the folder to sys.path
sys.path.insert(0, other_folder_path) 

from resume_llm import ask_llm, validate_json

load_dotenv("./../../.env")  

st.set_page_config(page_title="CV Parser", page_icon="📄")
st.title("CV Parser")
st.caption("Upload any CV or resume and extract the information in JSON format.")

uploaded_file = st.file_uploader("Choose a file")

if uploaded_file is not None:
  bytearray = uploaded_file.read()
  pdf = pymupdf.open(stream=bytearray, filetype="pdf")
  
  context = ""
  for page in pdf:
    context = context + "\n" + page.get_text()
    
  pdf.close()
  
if st.button("Extract"):
  question = """
You are tasked with parsing a job resume.
Your goal is to extract relevant information in a valid structured 'JSON' format. 
Do not write preambles or explanations.
"""

  with st.spinner("Parsing CV..."):
    response = ask_llm(context=context, question=question)
    
  with st.spinner("Validating JSON..."):
    response = validate_json(response)
    
  st.write("**Extracted Information:**")
  st.write(response)